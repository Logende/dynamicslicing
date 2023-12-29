from typing import Sequence, Dict, Set, Optional, List

from .finders import Definition
import libcst as cst


class ControlFlowRecorder:
    def __init__(self):
        self.statements: Dict[int, StatementEvents] = {}
        self.event_stack: List[Event] = []

    def get_statement_events(self, line) -> StatementEvents:
        if line not in self.statements:
            self.statements[line] = StatementEvents()
        events = self.statements[line]
        return events

    def record_assignment(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.assignments.add(variable)
        self.event_stack.append(EventAssign(line, variable))

    def record_alias(self, alias: str, variable: str, line: int):
        events = self.get_statement_events(line)
        events.aliases[alias] = variable
        self.event_stack.append(EventAlias(line, alias, variable))

    def record_modification(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.modifications.add(variable)
        self.event_stack.append(EventModify(line, variable))

    def record_usage(self, variable: str, line: int):
        events = self.get_statement_events(line)
        events.usages.add(variable)
        self.event_stack.append(EventUse(line, variable))
