from enum import Enum
from typing import Any, List, Callable, Sequence, Dict, Set

import libcst
import libcst as cst
from dynapyt.analyses.BaseAnalysis import BaseAnalysis
from dynapyt.instrument.IIDs import IIDs
from dynapyt.utils.nodeLocator import get_node_by_location
from libcst.metadata import PositionProvider


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
    criterion_finder = SlicingCriterionFinder(" slicing criterion")
    ast.visit(criterion_finder)
    if len(criterion_finder.results) == 0:
        raise RuntimeError("Unable to find slicing criterion in given ast.")
    elif len(criterion_finder.results) > 1:
        raise RuntimeError("Found multiple slicing criteria in given ast: " + str(criterion_finder.results))
    else:
        return criterion_finder.results[0]


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


class DataflowRecorderSimple:
    def __init__(self):
        self.assignments: Dict[int, Set[str]] = {}
        self.usages: Dict[int, Set[str]] = {}

    def record_assignment(self, variables: Sequence[str], line: int):
        if line not in self.assignments.keys():
            self.assignments[line] = set()
        for variable in variables:
            self.assignments[line].add(variable)

    def record_usage(self, variables: Sequence[str], line: int):
        if line not in self.usages.keys():
            self.usages[line] = set()
        for variable in variables:
            self.usages[line].add(variable)


class DataflowGraph:
    def __int__(self, assignments: Dict[int, Set[str]], usages: Dict[int, Set[str]], slicing_criterion: int):
        relevant_variables = usages.get(slicing_criterion, set()).copy()

        for line in range(slicing_criterion-1, 0, -1):
            line_assignments = assignments.get(line, set())
            line_usages = usages.get(line, set())




class SliceDataflow(BaseAnalysis):
    def __init__(self, source_path):
        super().__init__()

        with open(source_path, "r") as file:
            source = file.read()
        iid_object = IIDs(source_path)
        self.ast = cst.parse_module(source)
        self.recorder = DataflowRecorderSimple()
        self.slicing_criterion = determine_slicing_criterion_line(self.ast)

    def record_assignment(self, variables: Sequence[str], line: int):
        self.recorder.record_assignment(variables, line)

    def record_usage(self, variables: Sequence[str], line: int):
        self.recorder.record_usage(variables, line)

    # todo: add support for more hooks to track other ways of variable use
    # it might be that I will remove the expression extraction code if I already get all uses via hooks directly
    # e.g. for assignment hook only fire assignment event, and to get uses just listen to variable read event
    def write(
            self, dyn_ast: str, iid: int, old_vals: List[Callable], new_val: Any
    ) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)

        if isinstance(node, cst.Assign):
            targets: Sequence[cst.AssignTarget] = node.targets
            target_variables = extract_variables_from_assign_targets(targets)
            self.record_assignment(target_variables, location.start_line)

            # no need to extract usages here: use read hook for usages instead
            # value: cst.BaseExpression = node.value
            # value_variables = extract_variables_from_expression(value)
            # self.record_usage(value_variables, location.start_line)

            print("asd")

        else:
            raise RuntimeError("Unexpected behavior: found write event that is not of type cst.Assign: " + str(node))

    def read(self, dyn_ast: str, iid: int, val: Any) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        value_variables = extract_variables_from_expression(node)
        self.record_usage(value_variables, location.start_line)
        print("asd")

    def read(self, dyn_ast: str, iid: int, val: Any) -> Any:
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)
        node = get_node_by_location(ast[0], location)
        value_variables = extract_variables_from_expression(node)
        self.record_usage(value_variables, location.start_line)
        print("asd")
#
    #def begin_execution(self) -> None:
    #    """Hook for the start of execution."""
    #    pass
#
    #def end_execution(self) -> None:
    #    """Hook for the end of execution."""
    #    # Traverse use and assign events in backwards order
    #    relevant_variables = []
    #    for event in reversed(self.events):
    #        if event.event_type == DataflowEventType.USE:
    #            pass
