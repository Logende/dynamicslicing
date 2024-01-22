from typing import Dict

from rdflib import Graph, URIRef, Namespace

from dynamicslicing.dataflow_recorder import DataflowRecorderSimple
from dynamicslicing.dependency_graph_utils import statement_to_node
from dynamicslicing.finders import Definition
from dynamicslicing.dataflow_recorder import EventUse, EventModify, EventAssign, EventAlias

RELATIONSHIP_DEFINITION_IS_USED_BY = URIRef("g:def_used_by")
RELATIONSHIP_DEFINITION_IS_MODIFIED_BY = URIRef("g:def_modified_by")


def create_graph_from_dataflow(recorder: DataflowRecorderSimple, slicing_criterion_line: int,
                               definitions: dict[str, Definition]) -> Graph:
    return DependencyGraphDataflowForward(recorder, slicing_criterion_line, definitions).g


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
