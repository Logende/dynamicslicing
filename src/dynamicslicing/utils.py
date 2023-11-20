from typing import List, Union
import libcst as cst
from libcst._nodes.statement import BaseStatement, If
from libcst import CSTNodeT, RemovalSentinel, FlattenSentinel
from libcst.metadata import (
    ParentNodeProvider,
    PositionProvider,
)
import libcst.matchers as m


class OddIfNegation(m.MatcherDecoratableTransformer):
    """
    Negate the test of every if statement on an odd line.
    """
    METADATA_DEPENDENCIES = (
        ParentNodeProvider,
        PositionProvider,
    )

    def leave_If(self, original_node: If, updated_node: If) -> BaseStatement | FlattenSentinel[BaseStatement] | RemovalSentinel:
        location = self.get_metadata(PositionProvider, original_node)
        if location.start.line % 2 == 0:
            return updated_node
        negated_test = cst.UnaryOperation(
            operator=cst.Not(),
            expression=updated_node.test,
        )
        return updated_node.with_changes(
            test=negated_test,
        )


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
        location = self.get_metadata(PositionProvider, node)
        # visit children only when node should be kept, otherwise would lead to errors (e.g. removing name of function)
        return location.start.line in self.lines_to_keep

    def on_leave(self, original_node: CSTNodeT, updated_node: CSTNodeT) -> Union[CSTNodeT, RemovalSentinel, FlattenSentinel[CSTNodeT]]:
        location = self.get_metadata(PositionProvider, original_node)
        if location.start.line in self.lines_to_keep:
            return updated_node

        return cst.RemoveFromParent()


def negate_odd_ifs(code: str) -> str:
    syntax_tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(syntax_tree)
    code_modifier = OddIfNegation()
    new_syntax_tree = wrapper.visit(code_modifier)
    return new_syntax_tree.code


def remove_lines(code: str, lines_to_keep: List[int]) -> str:
    syntax_tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(syntax_tree)
    code_modifier = LineRemover(lines_to_keep)
    new_syntax_tree = wrapper.visit(code_modifier)
    return new_syntax_tree.code
