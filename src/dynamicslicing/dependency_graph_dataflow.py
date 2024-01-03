from typing import Dict

from rdflib import Graph, URIRef, Namespace

from dynamicslicing.dataflow_recorder import DataflowRecorderSimple
from dynamicslicing.dependency_graph_utils import statement_to_node
from dynamicslicing.finders import Definition
from dynamicslicing.dataflow_recorder import EventUse, EventModify, EventAssign, EventAlias
from settings import FORWARD_SLICE

RELATIONSHIP_DEFINITION_IS_USED_BY = URIRef("g:def_used_by")
RELATIONSHIP_DEFINITION_IS_MODIFIED_BY = URIRef("g:def_modified_by")


def create_graph_from_dataflow(recorder: DataflowRecorderSimple, slicing_criterion_line: int,
                               definitions: dict[str, Definition]) -> Graph:
    if FORWARD_SLICE:
        return DependencyGraphDataflowForward(recorder, slicing_criterion_line, definitions).g
    else:
        return DependencyGraphDataflowBackward(recorder, slicing_criterion_line, definitions).g


class DependencyGraphDataflowForward:

    def __init__(self, recorder: DataflowRecorderSimple, slicing_criterion_line: int,
                 definitions: dict[str, Definition]):
        self.g = Graph()
        self.g.bind("g", Namespace("g"))
        self.slicing_criterion_line = slicing_criterion_line
        self.definitions = definitions
        self.latest_assignments: Dict[str, int] = {}
        self.latest_aliases: Dict[str, str] = {}

        for event in recorder.event_stack:

            if isinstance(event, EventAssign):
                self.latest_assignments[event.variable] = event.line
                # remove alias linkage on assignment.
                # note that this requires alias event to be triggered after assign event
                if event.variable in self.latest_aliases:
                    del self.latest_aliases[event.variable]

            elif isinstance(event, EventUse):
                variable_definitions = self.get_definitions_for_variable(event.variable)
                for definition_line in variable_definitions.values():
                    self.add_definition_use_tuple(definition_line, event.line, RELATIONSHIP_DEFINITION_IS_USED_BY)

            elif isinstance(event, EventModify):
                variable_definitions = self.get_definitions_for_variable(event.variable)
                for variable, definition_line in variable_definitions.items():
                    self.add_definition_use_tuple(definition_line, event.line, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY)
                    self.latest_assignments[variable] = event.line

            elif isinstance(event, EventAlias):
                self.latest_aliases[event.alias] = event.variable_behind_alias

    def add_definition_use_tuple(self, definition_line: int, use_line: int, relationship: URIRef):
        self.g.add((
            statement_to_node(definition_line),
            relationship,
            statement_to_node(use_line),
        ))

    def get_definitions_for_variable(self, variable: str) -> Dict[str, int]:
        latest_assignment = self.latest_assignments.get(variable, -1)

        if latest_assignment == -1:
            if variable in self.definitions:
                latest_assignment = self.definitions[variable].location.start.line
        result_lines = {
            variable: latest_assignment
        }

        if variable in self.latest_aliases:
            variable_behind_alias = self.latest_aliases[variable]
            if variable_behind_alias:
                result_lines.update(self.get_definitions_for_variable(variable_behind_alias))

        return result_lines


class DependencyGraphDataflowBackward:

    def __init__(self, recorder: DataflowRecorderSimple, slicing_criterion_line: int,
                 definitions: dict[str, Definition]):
        self.g = Graph()
        self.g.bind("g", Namespace("g"))
        self.slicing_criterion_line = slicing_criterion_line
        self.definitions = definitions
        self.open_uses: dict[str, set[int]] = {}

        for event in reversed(recorder.event_stack):

            if isinstance(event, EventAssign):
                if event.variable in self.open_uses:
                    definition_line = event.line
                    for usage_line in self.open_uses[event.variable]:
                        self.add_definition_use_tuple(definition_line, usage_line, RELATIONSHIP_DEFINITION_IS_USED_BY)
                    del self.open_uses[event.variable]

            elif isinstance(event, EventUse):
                if event.variable in self.definitions:
                    definition_line = self.definitions[event.variable].location.start.line
                    self.add_definition_use_tuple(definition_line, event.line, RELATIONSHIP_DEFINITION_IS_USED_BY)
                else:
                    self.add_open_usage(event.variable, event.line)

            elif isinstance(event, EventModify):
                if event.variable in self.open_uses:
                    definition_line = event.line
                    for usage_line in self.open_uses[event.variable]:
                        self.add_definition_use_tuple(definition_line, usage_line, RELATIONSHIP_DEFINITION_IS_USED_BY)

            elif isinstance(event, EventAlias):
                if event.alias in self.open_uses:
                    definition_line = event.line
                    for usage_line in self.open_uses[event.alias]:
                        self.add_definition_use_tuple(definition_line, usage_line, RELATIONSHIP_DEFINITION_IS_USED_BY)
                    del self.open_uses[event.alias]

    def add_open_usage(self, variable: str, line: int):
        if variable not in self.open_uses:
            self.open_uses[variable] = set()
        self.open_uses[variable].add(line)

    def add_definition_use_tuple(self, definition_line: int, use_line: int, relationship: URIRef):
        self.g.add((
            statement_to_node(definition_line),
            relationship,
            statement_to_node(use_line),
        ))
