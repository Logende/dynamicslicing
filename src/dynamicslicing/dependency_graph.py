import rdflib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDFS
import libcst as cst

from dynamicslicing.dataflow_recorder import DataflowRecorderSimple
from dynamicslicing.finders import Definition


def create_graph_from_dataflow_recorder(recorder: DataflowRecorderSimple, slicing_criterion_line: int) -> Graph:
    return None


def statement_to_node(line: int) -> URIRef:
    return URIRef("statement_" + str(line))


def create_graph_from_definitions(definitions: dict[str, Definition]) -> Graph:
    g = Graph()

    for name, definition in definitions.items():
        # make every line inside the definition dependent on the first line of the definition
        definition_start = definition.location.start.line

        for line in range(definition.location.start.line + 1, definition.location.end.line + 1):
            g.add((
                statement_to_node(definition_start),
                URIRef("definition_is_used_by"),
                statement_to_node(line),
            ))

        if definition.name == "__init__" and isinstance(definition.node, cst.FunctionDef):
            # always make classes dependent on complete init
            # todo: optimize to only use needed part of init
            class_def_line = definition.parent.location.start.line
            for init_line in range(definition.location.start.line, definition.location.end.line + 1):
                g.add((
                    statement_to_node(init_line),
                    URIRef("init_is_mandatory_for"),
                    statement_to_node(class_def_line),
                ))

        sub_graph = create_graph_from_definitions(definition.children)
        g += sub_graph
    return g
