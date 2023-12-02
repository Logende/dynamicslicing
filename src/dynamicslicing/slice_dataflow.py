from enum import Enum
from typing import Any, List, Callable, Union
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


# Todo: node does not need to be transformer
class AssignmentFinder(m.MatcherDecoratableTransformer):
    """
    Remove the given code lines.
    """
    METADATA_DEPENDENCIES = (
        ParentNodeProvider,
        PositionProvider,
    )

    def __init__(self, relevant_line: int):
        super().__init__()
        self.relevant_line = relevant_line

    def on_visit(self, node: cst.CSTNode):
        location = self.get_metadata(PositionProvider, node)
        # do not go into children when already having found relevant line
        return location.start.line != self.relevant_line

    def on_leave(self, original_node: CSTNodeT, updated_node: CSTNodeT) -> Union[CSTNodeT, RemovalSentinel, FlattenSentinel[CSTNodeT]]:
        location = self.get_metadata(PositionProvider, original_node)
        if location.start.line == self.relevant_line:
            print("found relevant line in tree")
            # found the node for the relevant line
            #if original_node.
            if original_node.

        return updated_node


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

        # Instrument the code
        #klass = self.__class__
        #module = klass.__module__
        #full_qualified_class_name = module + '.' + klass.__qualname__
        #selected_hooks = get_hooks_from_analysis([full_qualified_class_name])
        # instrumented_code = instrument_code(source, source_path, iid_object, selected_hooks)

        # Analyse the code

        print("init slicedataflow file")
        self.next_event_id = 0
        self.events: List[DataflowEvent] = []

    def write(
            self, dyn_ast: str, iid: int, old_vals: List[Callable], new_val: Any
    ) -> Any:
        """Hook for writes.


        Parameters
        ----------
        dyn_ast : str
            The path to the original code. Can be used to extract the syntax tree.

        iid : int
            Unique ID of the syntax tree node.

        old_vals : Any
            A list of old values before the write takes effect.
            It's a list to support multiple assignments.
            Each old value is wrapped into a lambda function, so that
            the analysis writer can decide if and when to evaluate it.

        new_val : Any
            The value after the write takes effect.


        Returns
        -------
        Any
            If provided, overwrites the returned value.

        """
        ast = self._get_ast(dyn_ast)
        location = self.iid_to_location(dyn_ast, iid)

        wrapper = cst.metadata.MetadataWrapper(self.syntax_tree)
        finder = AssignmentFinder(location.start_line)
        _ = wrapper.visit(finder)


        print("dyn ast: " + dyn_ast + " iid: " + str(iid) + " old_vals: " + str(old_vals) + " new_val: " + str(new_val))
