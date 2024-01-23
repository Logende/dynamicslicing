"""This file defines the event recorder classes for dataflow events. To be filled with data during
execution of instructed code. Can then be used to perform dataflow analysis based on the recorded events."""

import copy
from typing import List
from pathlib import Path
from json import dumps


class Event:
    def __init__(self, line: int):
        self.line = line
        self.aliases: set[EventAlias] = set()


class EventAssign(Event):
    def __init__(self, line: int, variable: str):
        super().__init__(line)
        self.variable = variable


class EventUse(Event):
    def __init__(self, line: int, variable: str):
        super().__init__(line)
        self.variable = variable


class EventModify(Event):
    def __init__(self, line: int, variable: str):
        super().__init__(line)
        self.variable = variable


class EventAlias(Event):
    def __init__(self, line: int, alias: str, variable_behind_alias: str):
        super().__init__(line)
        self.alias = alias
        self.variable_behind_alias = variable_behind_alias


class DataflowRecorderSimple:
    def __init__(self):
        self.event_stack: List[Event] = []

    def record_assignment(self, variable: str, line: int):
        self.event_stack.append(EventAssign(line, variable))

    def record_alias(self, alias: str, variable: str, line: int):
        self.event_stack.append(EventAlias(line, alias, variable))

    def record_modification(self, variable: str, line: int):
        self.event_stack.append(EventModify(line, variable))

    def record_usage(self, variable: str, line: int):
        self.event_stack.append(EventUse(line, variable))


def convert_recorder_to_dict(recorder: DataflowRecorderSimple) -> dict:
    events = []

    for event in recorder.event_stack:
        event_copy = copy.deepcopy(event)
        # turn set into list because sets are not JSON serializable
        event_copy.aliases = list(event_copy.aliases)
        event_copy.type = event_copy.__class__.__name__
        events.append(event_copy.__dict__)

    return {"events": events}


def save_recorder_to_file(recorder: DataflowRecorderSimple, path: Path):
    json_string = dumps(convert_recorder_to_dict(recorder), indent=4)
    with open(path, 'w') as file:
        file.write(json_string)
