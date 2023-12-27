from typing import Sequence
import libcst as cst


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
        prefix = extract_variables_from_expression(expression.value)
        attr = expression.attr.value
        path = prefix[0] + "." + attr
        result.append(path)
        # result.extend(prefix)

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
        if isinstance(target.target, cst.Attribute):
            return True

    return False


def get_contained_variables(variables: Sequence[str]) -> Sequence[str]:
    result = []

    for variable in variables:
        result.append(variable)
        if "." in variable:
            result.extend(get_contained_variables([variable[0: variable.rfind(".")]],))

    return result
