from enum import Enum
from typing import Any, List, Callable, Union, Sequence
import logging

import libcst as cst
import libcst.matchers as m
from dynapyt.analyses.BaseAnalysis import BaseAnalysis
from dynapyt.instrument.IIDs import IIDs
from dynapyt.instrument.instrument import instrument_code, get_hooks_from_analysis
from dynapyt.utils.nodeLocator import get_node_by_location, get_parent_by_type
from libcst import CSTNodeT, RemovalSentinel, FlattenSentinel
from libcst.metadata import PositionProvider, ParentNodeProvider


class DataflowEventType(Enum):
    USE = 0,
    ASSIGN = 1


class DataflowEvent:
    def __init__(self, var: str, line: int, event_id: int, event_type: DataflowEventType):
        self.var = var
        self.line = line
        self.event_id = event_id
        self.event_type = event_type


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
        # todo: differentiate between variable name and class name (e.g. when creating new instance)
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


class SliceDataflow(BaseAnalysis):
    def __init__(self, source_path):
        super().__init__()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = logging.FileHandler("output.log", "w", "utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)

        with open(source_path, "r") as file:
            source = file.read()
        iid_object = IIDs(source_path)
        self.syntax_tree = cst.parse_module(source)

        self.next_event_id = 0
        self.events: List[DataflowEvent] = []

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
            value: cst.BaseExpression = node.value

            target_variables = extract_variables_from_assign_targets(targets)
            value_variables = extract_variables_from_expression(value)

            # first the variables are used
            for value_variable in value_variables:
                self.events.append(DataflowEvent(
                    value_variable,
                    location.start_line,
                    self.next_event_id,
                    DataflowEventType.USE
                ))
                self.next_event_id += 1

            # second te values are assigned to the target variables
            for target_variable in target_variables:
                self.events.append(DataflowEvent(
                    target_variable,
                    location.start_line,
                    self.next_event_id,
                    DataflowEventType.ASSIGN
                ))
                self.next_event_id += 1

        else:
            raise RuntimeError("Unexpected behavior: found write event that is not of type cst.Assign: " + str(node))

    def begin_execution(self) -> None:
        """Hook for the start of execution."""
        pass

    def end_execution(self) -> None:
        """Hook for the end of execution."""
        # Traverse use and assign events in backwards order
        for i in reversed(a):