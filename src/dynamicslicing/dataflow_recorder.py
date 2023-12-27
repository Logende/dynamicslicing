from typing import Sequence, Dict, Set, Optional

from .finders import Definition
import libcst as cst


class StatementEvents:
    def __init__(self):
        self.assignments: Set[str] = set()
        self.usages: Set[str] = set()
        self.modifications: Set[str] = set()
        self.aliases: Dict[str, str] = {}


class DataflowRecorderSimple:
    def __init__(self):
        self.statements: Dict[int, StatementEvents] = {}

    def get_statement_events(self, line) -> StatementEvents:
        if line not in self.statements:
            self.statements[line] = StatementEvents()
        events = self.statements[line]
        return events

    def record_assignment(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.assignments.add(variable)

    def record_alias(self, alias: str, variable: str, line: int):
        events = self.get_statement_events(line)
        events.aliases[alias] = variable

    def record_modification(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.modifications.add(variable)

    def record_usage(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.usages.add(variable)
