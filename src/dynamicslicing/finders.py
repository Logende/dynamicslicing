"""This file contains helper functions to extract information from an AST using static analysis methods."""

from typing import Optional

import libcst as cst
from libcst._position import CodeRange
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


def find_slicing_criterion_line(ast: cst.Module) -> int:
    criterion_finder = SlicingCriterionFinder("# slicing criterion")
    wrapper = cst.metadata.MetadataWrapper(ast)
    wrapper.visit(criterion_finder)
    if len(criterion_finder.results) == 0:
        raise RuntimeError("Unable to find slicing criterion in given ast.")
    elif len(criterion_finder.results) > 1:
        raise RuntimeError("Found multiple slicing criteria in given ast: " + str(criterion_finder.results))
    else:
        return criterion_finder.results[0]


class CallFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (
        PositionProvider,
    )

    def __init__(self, function_name: str):
        super().__init__()
        self.function_name = function_name
        self.results = []

    def on_visit(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        if isinstance(node, cst.Call):
            func = node.func
            if isinstance(func, cst.Name):
                if func.value == self.function_name:
                    self.results.append(location.start.line)
        return True


def find_slice_me_call(ast: cst.Module) -> int:
    call_finder = CallFinder("slice_me")
    wrapper = cst.metadata.MetadataWrapper(ast)
    wrapper.visit(call_finder)
    if len(call_finder.results) == 0:
        raise RuntimeError("Unable to find slice_me call in given ast.")
    elif len(call_finder.results) > 1:
        raise RuntimeError("Found multiple slice_me calls in given ast: " + str(call_finder.results))
    else:
        return call_finder.results[0]


class Definition:
    def __init__(self, name: str, node: cst.FunctionDef | cst.ClassDef, location: CodeRange, parent: Optional):
        self.name = name
        self.node = node
        self.location = location
        self.children: dict[str, Definition] = {}
        self.parent: Optional[Definition] = parent


class DefinitionFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (
        PositionProvider,
    )

    def __init__(self):
        super().__init__()
        self.results: dict[str, Definition] = {}
        self.current_definition: Optional[Definition] = None

    def on_visit(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        if isinstance(node, cst.ClassDef) | isinstance(node, cst.FunctionDef):
            name = node.name.value

            structure_to_add_new_definition = self.results if not self.current_definition \
                else self.current_definition.children

            if name in structure_to_add_new_definition:
                raise Exception("Error: this code can not deal with multiple definitions using the same name")
            self.current_definition = Definition(name, node, location, self.current_definition)
            structure_to_add_new_definition[name] = self.current_definition
        return True

    def on_leave(self, original_node: cst.CSTNode) -> None:
        if isinstance(original_node, cst.ClassDef) | isinstance(original_node, cst.FunctionDef):
            self.current_definition = self.current_definition.parent


def find_definitions(ast: cst.Module) -> dict[str, Definition]:
    def_finder = DefinitionFinder()
    wrapper = cst.metadata.MetadataWrapper(ast)
    wrapper.visit(def_finder)
    return def_finder.results


class CFElement:
    def __init__(self, node: cst.CSTNode, location: CodeRange, parent: Optional):
        self.node = node
        self.location = location
        self.children: list[CFElement] = []
        self.parent: Optional[CFElement] = parent
        self.main_line = location.start.line
        self.body_start = location.start.line + 1
        self.body_end = location.end.line


class CFElementConditional(CFElement):
    def __init__(self, node: cst.If | cst.While, location: CodeRange, parent: Optional):
        super().__init__(node, location, parent)


class ControlFlowFinder(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (
        PositionProvider,
    )

    def __init__(self, function_definition: Definition):
        super().__init__()
        self.current_element: Optional[CFElement] = CFElement(function_definition.node, function_definition.location, None)

    def on_visit(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        if isinstance(node, (cst.If, cst.Else, cst.While, cst.With, cst.Finally, cst.Try)):
            body = node.body

            if isinstance(node, (cst.If, cst.While)):
                new_element = CFElementConditional(node, location, self.current_element)
            else:
                new_element = CFElement(node, location, self.current_element)

            self.current_element.children.append(new_element)
            self.current_element = new_element

        return True

    def on_leave(self, original_node: cst.CSTNode) -> None:
        if isinstance(original_node, (cst.If, cst.Else, cst.While, cst.With, cst.Finally, cst.Try)):
            self.current_element = self.current_element.parent


def find_control_flow_elements(function_def: Definition, ast: cst.Module) -> CFElement:
    cf_finder = ControlFlowFinder(function_def)
    wrapper = cst.metadata.MetadataWrapper(ast)
    # note that the visitor will start from top of the ast, not from top of the function def node.
    # this still works because the module contains only one function with control flow elements
    wrapper.visit(cf_finder)
    return cf_finder.current_element
