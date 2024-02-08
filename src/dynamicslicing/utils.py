"""This file implements a utility function to extract only the provided set of lines of code from an AST."""

from typing import List, Union
import libcst as cst
from libcst import CSTNodeT, RemovalSentinel, FlattenSentinel
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
)
import libcst.matchers as m


class LineRemover(m.MatcherDecoratableTransformer):
    """
    Remove the given code lines.
    """
    METADATA_DEPENDENCIES = (
        ParentNodeProvider,
        PositionProvider,
    )

    def __init__(self, lines_to_keep: List[int]):
        super().__init__()
        self.lines_to_keep = lines_to_keep

    def on_visit(self, node: cst.CSTNode):
        return self.is_keep_node(node)

    def on_leave(self, original_node: CSTNodeT, updated_node: CSTNodeT) -> Union[CSTNodeT, RemovalSentinel,
                                                                                 FlattenSentinel[CSTNodeT]]:
        if self.is_keep_node(original_node):
            return updated_node

        return cst.RemoveFromParent()

    def is_keep_node(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        return location.start.line in self.lines_to_keep or isinstance(node, cst.IndentedBlock)


def remove_lines(code: str, lines_to_keep: List[int]) -> str:
    syntax_tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(syntax_tree)
    code_modifier = LineRemover(lines_to_keep)
    new_syntax_tree = wrapper.visit(code_modifier)
    return new_syntax_tree.code


def is_of_primitive_type(value: any) -> bool:
    return isinstance(value, (bool, str, int, float, type(None)))
