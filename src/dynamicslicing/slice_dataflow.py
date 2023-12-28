from pathlib import Path
from typing import Any, List, Callable, Sequence, Dict, Set, Tuple, Optional

import libcst as cst
from dynapyt.analyses.BaseAnalysis import BaseAnalysis
from dynapyt.instrument.IIDs import IIDs
from dynapyt.utils.nodeLocator import get_node_by_location

from .dataflow_recorder import DataflowRecorderSimple
from .dependency_graph_query import get_dependency_nodes
from .dependency_graph_utils import statement_to_node
from .finders import find_slicing_criterion_line, find_definitions, Definition, find_slice_me_call
from .utils import remove_lines
from .variable_extractor import extract_variables_from_assign_targets, does_assignment_consider_previous_values, \
    extract_variables_from_expression, extract_variables_from_args, get_contained_variables
from .dependency_graph_definitions import create_graph_from_definitions
from .graph_visualizer import save_rdf_graph
from .dependency_graph_dataflow import create_graph_from_dataflow


class SliceDataflow(BaseAnalysis):
    def __init__(self, source_path):
        super().__init__()

        with open(source_path, "r") as file:
            self.source = file.read()
        iid_object = IIDs(source_path)
        self.source_path = source_path
        self.ast = cst.parse_module(self.source)
        self.definitions = find_definitions(self.ast)
        self.slicing_criterion = find_slicing_criterion_line(self.ast)
        self.slice_me_call = find_slice_me_call(self.ast)
        self.recorder = DataflowRecorderSimple()


    def record_alias(self, alias: str, variable_behind_alias: str, line: int):
        self.recorder.record_alias(alias, variable_behind_alias, line)

    def record_modification(self, variable: str, line: int):
        self.recorder.record_modification(variable, line)

    def record_modifications(self, variables: Sequence[str], line: int):
        for variable in variables:
            self.record_modification(variable, line)

    def record_assignment(self, variable: str, line: int,):
        self.recorder.record_assignment(variable, line)

    def record_assignments(self, variables: Sequence[str], line: int):
        for variable in variables:
            self.record_assignment(variable, line)

    def record_usage(self, variable: str, line: int):
        self.recorder.record_usage(variable, line)

    def record_usages(self, variables: Sequence[str], line: int):
        for variable in variables:
            self.record_usage(variable, line)

    def write(
            self, dyn_ast: str, iid: int, old_vals: List[Callable], new_val: Any
    ) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)

        if isinstance(node, cst.Assign):
            targets: Sequence[cst.AssignTarget] = node.targets
            value: cst.BaseExpression = node.value
            is_alias_for = None
            if isinstance(value, cst.Name):
                is_alias_for = value.value

            for target in targets:
                self.record_assign_to_target(target.target, location, is_alias_for, False)

        elif isinstance(node, cst.AugAssign):
            target_expression: cst.BaseAssignTargetExpression = node.target
            self.record_assign_to_target(target_expression, location, None, True)

        else:
            raise RuntimeError("Unexpected behavior: found write event that is not of type cst.Assign: " + str(node))

    def record_assign_to_target(self, target: cst.BaseAssignTargetExpression, location, is_alias_for: Optional[str],
                                is_aug_assign: bool):
        if isinstance(target, cst.Subscript):
            subscript = target
            prefix = extract_variables_from_expression(subscript.value)[0]  # todo: support more?
            path = prefix + "[?]"
            if is_aug_assign:
                self.record_modification(path, location.start_line)
            else:
                self.record_assignment(path, location.start_line)

            self.record_modification(prefix, location.start_line)

            if is_alias_for:
                self.record_alias(path, is_alias_for, location.start_line)

        elif isinstance(target, cst.Attribute):
            attribute = target
            prefix = extract_variables_from_expression(attribute.value)[0]  # todo: support more?
            attr = attribute.attr.value
            path = prefix + "." + attr
            if is_aug_assign:
                self.record_modification(path, location.start_line)
            else:
                self.record_assignment(path, location.start_line)

            self.record_modification(prefix, location.start_line)

            if is_alias_for:
                self.record_alias(path, is_alias_for, location.start_line)

        elif isinstance(target, cst.Name):
            name = target
            if is_aug_assign:
                self.record_modification(name.value, location.start_line)
            else:
                self.record_assignment(name.value, location.start_line)

            if is_alias_for:
                self.record_alias(name.value, is_alias_for, location.start_line)

        else:
            raise RuntimeError("Unknown assign target: " + str(target))

    def read(self, dyn_ast: str, iid: int, val: Any) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        value_variables = extract_variables_from_expression(node)
        value_variables_extensive = get_contained_variables(value_variables)
        self.record_usages(value_variables_extensive, location.start_line)

    def pre_call(
            self, dyn_ast: str, iid: int, function: Callable, pos_args: Tuple, kw_args: Dict
    ):
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        if isinstance(node, cst.Call):
            args = node.args
            func = node.func
            if isinstance(func, cst.Attribute):
                func_attr = func.attr
                func_value = func.value
                if isinstance(func_attr, cst.Name) and isinstance(func_value, cst.Name):
                    target_variables = extract_variables_from_args(args)
                    target_variables_extensive = get_contained_variables(target_variables)
                    self.record_usages(target_variables_extensive, location.start_line)
                    self.record_modification(func_value.value, location.start_line)

    def begin_execution(self) -> None:
        """Hook for the start of execution."""
        pass

    def end_execution(self) -> None:
        """Hook for the end of execution."""
        result_slice = self.compute_slice()
        self.save_slice(result_slice)

    def compute_slice(self) -> Set[int]:
        graph_definitions = create_graph_from_definitions(self.definitions)
        graph_dataflow = create_graph_from_dataflow(self.recorder, self.slicing_criterion, self.definitions)
        graph = graph_definitions + graph_dataflow
        save_rdf_graph(graph, Path(self.source_path).parent)

        target_node = statement_to_node(self.slicing_criterion)
        dependency_nodes = get_dependency_nodes(graph, target_node)

        # todo: prettier conversion from nodes to lines
        corresponding_lines = [int(str(node).replace("g:statement_", "")) for node in dependency_nodes]
        corresponding_lines.append(self.slice_me_call)
        return set(corresponding_lines)

    def save_slice(self, slice_to_save: Set[int]):
        original_file_path = Path(self.source_path)
        folder_path = original_file_path.parent
        slice_file_path = folder_path.joinpath("sliced.py")
        file_content = remove_lines(self.source, list(slice_to_save))
        with open(slice_file_path, "w") as file:
            file.write(file_content)


# todo: function to create dataflow dependency table, code structure dependency table and later control flow dependency table. And function to merge those tables.