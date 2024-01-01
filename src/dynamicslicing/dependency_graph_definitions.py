from rdflib import Graph, URIRef, Namespace
import libcst as cst

from dynamicslicing.dependency_graph_utils import statement_to_node
from dynamicslicing.finders import Definition

RELATIONSHIP_DEFINITION_HAS_DEPENDENT = URIRef("g:def_has_dependent")
RELATIONSHIP_DEFINITION_OUTSIDE_OF_ANALYSIS = URIRef("g:def_not_analyzed")


def create_graph_from_definitions(definitions: dict[str, Definition]) -> Graph:
    g = Graph()
    g.bind("g", Namespace("g"))

    for name, definition in definitions.items():
        # make every line inside the definition dependent on the first line of the definition
        definition_start = definition.location.start.line

        for line in range(definition.location.start.line + 1, definition.location.end.line + 1):
            g.add((
                statement_to_node(definition_start),
                RELATIONSHIP_DEFINITION_HAS_DEPENDENT,
                statement_to_node(line),
            ))

        # as only slice_me is supposed to be analyzed, we fully include all functions inside other definitions
        if isinstance(definition.node, cst.FunctionDef) and definition.parent:
            class_def_line = definition.parent.location.start.line
            for init_line in range(definition.location.start.line, definition.location.end.line + 1):
                g.add((
                    statement_to_node(init_line),
                    RELATIONSHIP_DEFINITION_OUTSIDE_OF_ANALYSIS,
                    statement_to_node(class_def_line),
                ))

        sub_graph = create_graph_from_definitions(definition.children)
        g += sub_graph
    return g
