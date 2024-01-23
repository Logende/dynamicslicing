"""Implement a DynaPyt analysis to trace all writes by printing them to stdout."""

import logging
from typing import Any, Callable, List
from dynapyt.analyses.BaseAnalysis import BaseAnalysis


class TraceWrites(BaseAnalysis):

    def __init__(self) -> None:
        super().__init__()
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = logging.FileHandler("output.log", "w", "utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)

    def log(self, iid: int, *args, **kwargs):
        res = ""
        for arg in args:
            if 'danger_of_recursion' in kwargs:
                res += ' ' + str(hex(id(arg)))
            else:
                res += ' ' + str(arg)
        logging.info(res)
        print(res)

    def write(
            self, dyn_ast: str, iid: int, old_vals: List[Callable], new_val: Any
    ) -> Any:
        self.log(iid, new_val)
