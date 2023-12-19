from enum import Enum
from pathlib import Path
from typing import Any, List, Callable, Sequence, Dict, Set, Tuple

import dynapyt.instrument.IIDs
import libcst
import libcst as cst
from dynapyt.analyses.BaseAnalysis import BaseAnalysis
from dynapyt.instrument.IIDs import IIDs
from dynapyt.utils.nodeLocator import get_node_by_location, get_parent_by_type
from libcst.metadata import PositionProvider, ParentNodeProvider

from .utils import remove_lines


class SlicingCriterionFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (
        PositionProvider,
    )

    def __init__(self, criterion_text: str):
        super().__init__()
        self.criterion_text = criterion_text
        self.results = []

    def on_visit(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        if isinstance(node, cst.Comment):
            if node.value == self.criterion_text:
                self.results.append(location.start.line)
        return True



def determine_slicing_criterion_line(ast: libcst.Module) -> int:
    criterion_finder = SlicingCriterionFinder("# slicing criterion")
    wrapper = cst.metadata.MetadataWrapper(ast)
    wrapper.visit(criterion_finder)
    if len(criterion_finder.results) == 0:
        raise RuntimeError("Unable to find slicing criterion in given ast.")
    elif len(criterion_finder.results) > 1:
        raise RuntimeError("Found multiple slicing criteria in given ast: " + str(criterion_finder.results))
    else:
        return criterion_finder.results[0]


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


def extract_variables_from_args(args: Sequence[cst.Arg]) -> Sequence[str]:
    result = []

    for arg in args:
        result.extend(extract_variables_from_expression(arg.value))

    return result


def extract_variables_from_formatted_string_content(expression: cst.BaseFormattedStringContent) -> Sequence[str]:
    result = []

    if isinstance(expression, cst.FormattedStringText):
        pass

    elif isinstance(expression, cst.FormattedStringExpression):
        result.extend(extract_variables_from_expression(expression.expression))

    else:
        raise RuntimeError("Unknown expression type for variable extraction: " + str(expression))

    return result


def extract_variables_from_expression(expression: cst.BaseExpression) -> Sequence[str]:
    result = []

    if isinstance(expression, cst.List):
        for element in expression.elements:
            result.extend(extract_variables_from_element(element))

    elif isinstance(expression, cst.FormattedString):
        for part in expression.parts:
            result.extend(extract_variables_from_formatted_string_content(part))

    elif isinstance(expression, cst.Subscript):
        value: cst.BaseExpression = expression.value
        result.extend(extract_variables_from_expression(value))

        subscript_elements: Sequence[cst.SubscriptElement] = expression.slice
        # todo: support extracting variable from subscirpt elements

    elif isinstance(expression, cst.Name):
        # todo: differentiate between variable name and class name (e.g. when creating new instance) or function call
        result.append(expression.value)

    elif isinstance(expression, cst.BinaryOperation):
        left = expression.left
        right = expression.right
        result.extend(extract_variables_from_expression(left))
        result.extend(extract_variables_from_expression(right))

    elif isinstance(expression, cst.Comparison):
        left = expression.left
        result.extend(extract_variables_from_expression(left))
        for comparison_target in expression.comparisons:
            target_comparator = comparison_target.comparator
            result.extend(extract_variables_from_expression(target_comparator))

    elif isinstance(expression, cst.Call):
        func: cst.BaseExpression = expression.func
        result.extend(extract_variables_from_expression(func))
        args: Sequence[cst.Arg] = expression.args
        # todo: consider whether args or scope are relevant? what if args shadow a outer scope variable?

    elif isinstance(expression, cst.Attribute):
        # todo
        return []

    elif isinstance(expression, (cst.Integer, cst.Float, cst.SimpleString)):
        pass

    else:
        raise RuntimeError("Unknown expression type for variable extraction: " + str(expression))

    return result


def extract_variables_from_element(element: cst.BaseElement) -> Sequence[str]:
    result = []
    value = element.value

    if isinstance(value, (cst.SimpleString, cst.Float, cst.Integer, cst.Newline)):
        pass

    else:
        raise RuntimeError("Unknown element value type for variable extraction: " + str(value))
    return result


def extract_variables_from_assign_targets(assign_targets: Sequence[cst.AssignTarget]) -> Sequence[str]:
    result = []
    for assign_target in assign_targets:
        result.extend(extract_variables_from_expression(assign_target.target))
    return result


def does_assignment_consider_previous_values(assign_targets: Sequence[cst.AssignTarget]) -> bool:
    for target in assign_targets:
        if isinstance(target.target, cst.Subscript):
            return True

    return False


class DataflowRecorderSimple:
    def __init__(self):
        self.assignments: Dict[int, Set[str]] = {}
        self.usages: Dict[int, Set[str]] = {}

        self.latest_assignments: Dict[str, int] = {}
        self.dependency_table: Dict[int, Set[int]] = {}  # variable assignment line mapped to places where it is used

        self.other_dependents: Set[int] = set()

    def record_assignment(self, variables: Sequence[str], line: int):
        if line not in self.assignments.keys():
            self.assignments[line] = set()
        for variable in variables:
            self.assignments[line].add(variable)

            self.latest_assignments[variable] = line

    def record_usage(self, variables: Sequence[str], line: int):
        if line not in self.usages.keys():
            self.usages[line] = set()
        for variable in variables:
            self.usages[line].add(variable)

            latest_assignment = self.latest_assignments.get(variable, -1)
            if latest_assignment not in self.dependency_table.keys():
                self.dependency_table[latest_assignment] = set()
            self.dependency_table[latest_assignment].add(line)

    def record_other_dependent(self, line: int):
        self.other_dependents.add(line)


class SliceDataflow(BaseAnalysis):
    def __init__(self, source_path):
        super().__init__()

        with open(source_path, "r") as file:
            self.source = file.read()
        iid_object = IIDs(source_path)
        self.source_path = source_path
        self.ast = cst.parse_module(self.source)
        self.recorder = DataflowRecorderSimple()
        self.slicing_criterion = determine_slicing_criterion_line(self.ast)

    def record_assignment(self, variables: Sequence[str], line: int):
        self.recorder.record_assignment(variables, line)

    def record_usage(self, variables: Sequence[str], line: int):
        self.recorder.record_usage(variables, line)

    def record_other_dependent(self, line: int):
        self.recorder.record_other_dependent(line)

    def get_parent_dependents(self, ast: cst.CSTNodeT, location: dynapyt.instrument.IIDs.Location, node: cst.CSTNode):
        parent_function_def = get_parent_by_type(ast, location, cst.FunctionDef)
        print("todo")

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
