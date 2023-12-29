from typing import List, Union
import libcst as cst
from libcst._nodes.statement import BaseStatement, If
from libcst import CSTNodeT, RemovalSentinel, FlattenSentinel
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
)
import libcst.matchers as m


class ControlFlowTransformer(m.MatcherDecoratableTransformer):
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

    def on_leave(self, original_node: CSTNodeT, updated_node: CSTNodeT) -> Union[
        CSTNodeT, RemovalSentinel, FlattenSentinel[CSTNodeT]]:
        if self.is_keep_node(original_node):
            return updated_node

        return cst.RemoveFromParent()

    def is_keep_node(self, node: cst.CSTNode):
        if isinstance(node, cst.SimpleWhitespace):
            return True

        location = self.get_metadata(PositionProvider, node)
        location_range = range(location.start.line, location.end.line + 1)

        for line_to_keep in self.lines_to_keep:
            if line_to_keep in location_range:
                return True
        return False


def transform_control_flow(code: str, lines_to_keep: List[int]) -> str:
    syntax_tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(syntax_tree)
    code_modifier = ControlFlowTransformer(lines_to_keep)
    new_syntax_tree = wrapper.visit(code_modifier)
    return new_syntax_tree.code
