from typing import Sequence, Dict, Set, Optional

from .finders import Definition
import libcst as cst


def compute_dataflow_dependents(dependency_table: Dict[int, Set[int]], slicing_criterion: int) -> Set[int]:
    created_new_knowledge = True
    relevant_nodes = {slicing_criterion}

    while created_new_knowledge:
        created_new_knowledge = False

        for relevant_node in relevant_nodes.copy():
            for assignment, usages in dependency_table.items():
                if relevant_node in usages and assignment not in relevant_nodes:
                    relevant_nodes.add(assignment)
                    created_new_knowledge = True
    return relevant_nodes


def update_dependency_table_with_definitions(dependency_table: Dict[int, Set[int]], definitions: dict[str, Definition]):
    for name, definition in definitions.items():
        # make every line inside the definition dependent on the first line of the definition
        definition_start = definition.location.start.line
        if definition_start not in dependency_table:
            dependency_table[definition_start] = set()
        for line in range(definition.location.start.line + 1, definition.location.end.line + 1):
            dependency_table[definition_start].add(line)

        if definition.name == "__init__" and isinstance(definition.node, cst.FunctionDef):
            # always make classes dependent on complete init
            # todo: optimize to only use needed part of init
            class_def_line = definition.parent.location.start.line
            for init_line in range(definition.location.start.line, definition.location.end.line + 1):
                if init_line not in dependency_table:
                    dependency_table[init_line] = set()
                dependency_table[init_line].add(class_def_line)

        update_dependency_table_with_definitions(dependency_table, definition.children)


class DataflowRecorderSimple:
    def __init__(self, definitions: dict[str, Definition]):
        self.definitions = definitions

        self.assignments: Dict[int, Set[str]] = {}
        self.usages: Dict[int, Set[str]] = {}

        self.latest_assignments: Dict[str, int] = {}
        self.latest_aliases: Dict[str, str] = {}

        self.dependency_table: Dict[int, Set[int]] = {}  # variable assignment line mapped to places where it is used
        update_dependency_table_with_definitions(self.dependency_table, self.definitions)

        self.other_dependents: Set[int] = set()

    def record_assignment(self, variables: Sequence[str], line: int, variables_are_alias_for: Optional[str] = None):
        if line not in self.assignments.keys():
            self.assignments[line] = set()
        for variable in variables:
            self.assignments[line].add(variable)

            self.latest_assignments[variable] = line
            self.latest_aliases[variable] = variables_are_alias_for

    def record_alias(self, alias: str, variable: str):
        self.latest_aliases[alias] = variable

    def record_usage(self, variables: Sequence[str], line: int):
        if line not in self.usages.keys():
            self.usages[line] = set()
        for variable in variables:
            self.usages[line].add(variable)

            definition_lines = self.get_definition_lines_from_variable(variable)
            for definition_line in definition_lines:
                self.record_definition_use_pair(definition_line, line)

    def record_definition_use_pair(self, definition_line: int, use_line: int):
        if definition_line not in self.dependency_table.keys():
            self.dependency_table[definition_line] = set()
        self.dependency_table[definition_line].add(use_line)

    def get_definition_lines_from_variable(self, variable: str) -> Sequence[int]:
        latest_assignment = self.latest_assignments.get(variable, -1)
        if latest_assignment == -1:
            if variable in self.definitions:
                latest_assignment = self.definitions[variable].location.start.line

        result_lines = [latest_assignment, ]

        if variable in self.latest_aliases:
            variable_behind_alias = self.latest_aliases[variable]
            if variable_behind_alias:
                result_lines.extend(self.get_definition_lines_from_variable(variable_behind_alias))

        return result_lines

    def record_other_dependent(self, line: int):
        self.other_dependents.add(line)
