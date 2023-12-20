from pathlib import Path
from typing import Any, List, Callable, Sequence, Dict, Set, Tuple

import libcst as cst
from dynapyt.analyses.BaseAnalysis import BaseAnalysis
from dynapyt.instrument.IIDs import IIDs
from dynapyt.utils.nodeLocator import get_node_by_location

from .dataflow_recorder import DataflowRecorderSimple, compute_dataflow_dependents
from .finders import find_slicing_criterion_line, find_definitions, Definition
from .utils import remove_lines
from .variable_extractor import extract_variables_from_assign_targets, does_assignment_consider_previous_values, \
    extract_variables_from_expression, extract_variables_from_args


class SliceDataflow(BaseAnalysis):
    def __init__(self, source_path):
        super().__init__()

        with open(source_path, "r") as file:
            self.source = file.read()
        iid_object = IIDs(source_path)
        self.source_path = source_path
        self.ast = cst.parse_module(self.source)
        definitions = find_definitions(self.ast)
        self.recorder = DataflowRecorderSimple(definitions)
        self.slicing_criterion = find_slicing_criterion_line(self.ast)

    def record_assignment(self, variables: Sequence[str], line: int):
        self.recorder.record_assignment(variables, line)

    def record_usage(self, variables: Sequence[str], line: int):
        self.recorder.record_usage(variables, line)

    def record_other_dependent(self, line: int):
        self.recorder.record_other_dependent(line)

    def write(
            self, dyn_ast: str, iid: int, old_vals: List[Callable], new_val: Any
    ) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)

        if isinstance(node, cst.Assign):
            targets: Sequence[cst.AssignTarget] = node.targets
            target_variables = extract_variables_from_assign_targets(targets)
            if does_assignment_consider_previous_values(targets):
                self.record_usage(target_variables, location.start_line)
            self.record_assignment(target_variables, location.start_line)

        elif isinstance(node, cst.AugAssign):
            target_expression: cst.BaseAssignTargetExpression = node.target
            target_variables = extract_variables_from_expression(target_expression)
            self.record_usage(target_variables, location.start_line)
            self.record_assignment(target_variables, location.start_line)

        else:
            raise RuntimeError("Unexpected behavior: found write event that is not of type cst.Assign: " + str(node))

    def read(self, dyn_ast: str, iid: int, val: Any) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        value_variables = extract_variables_from_expression(node)
        self.record_usage(value_variables, location.start_line)

    def function_enter(
            self, dyn_ast: str, iid: int, args: List[Any], name: str, is_lambda: bool
    ) -> None:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        if isinstance(node, cst.FunctionDef):
            if node.name.value == "slice_me":
                self.record_other_dependent(location.start_line)

    def pre_call(
            self, dyn_ast: str, iid: int, function: Callable, pos_args: Tuple, kw_args: Dict
    ):
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        if isinstance(node, cst.Call):
            args = node.args
            func = node.func
            if isinstance(func, cst.Name):
                if func.value == "slice_me":
                    self.record_other_dependent(location.start_line)
            if isinstance(func, cst.Attribute):
                func_attr = func.attr
                func_value = func.value
                if isinstance(func_attr, cst.Name) and isinstance(func_value, cst.Name):
                    target_variables = extract_variables_from_args(args)
                    self.record_usage(target_variables, location.start_line)
                    self.record_usage([func_value.value], location.start_line)
                    self.record_assignment([func_value.value], location.start_line)

    def begin_execution(self) -> None:
        """Hook for the start of execution."""
        pass

    def end_execution(self) -> None:
        """Hook for the end of execution."""
        result_slice = self.compute_slice()
        self.save_slice(result_slice)

    def compute_slice(self) -> Set[int]:
        return compute_dataflow_dependents(
            self.recorder.dependency_table,
            self.slicing_criterion).union(self.recorder.other_dependents)

    def save_slice(self, slice_to_save: Set[int]):
        original_file_path = Path(self.source_path)
        folder_path = original_file_path.parent
        slice_file_path = folder_path.joinpath("sliced.py")
        file_content = remove_lines(self.source, list(slice_to_save))
        with open(slice_file_path, "w") as file:
            file.write(file_content)
