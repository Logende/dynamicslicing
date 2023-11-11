# Implement a DynaPyt analysis to trace all writes by printing them to stdout.

import logging
from typing import Any, Callable, List
from dynapyt.analyses.BaseAnalysis import BaseAnalysis


class TraceWrites(BaseAnalysis):
    """
    .. include:: ../../../docs/hooks.md
    """

    def __init__(self) -> None:
        super().__init__()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = logging.FileHandler("output.log", "w", "utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)

    def log(self, iid: int, *args, **kwargs):
        res = ""
        # for arg in args:
        #     if 'danger_of_recursion' in kwargs:
        #         res += ' ' + str(hex(id(arg)))
        #     else:
        #         res += ' ' + str(arg)
        logging.info(str(iid) + ": " + res[:80])

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
        self.log(iid, "    Writing ", new_val)
