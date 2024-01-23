"""This file provides a function to generate an RDF knowledge graph based on static analysis of controlflow nodes
of an AST. The resulting graph contains an edge from each line of a controlflow element body to the head of the
controlflow element."""


from rdflib import Graph, URIRef, Namespace
import libcst as cst

from dynamicslicing.dependency_graph_utils import statement_to_node
from dynamicslicing.finders import CFElement

RELATIONSHIP_CONTROL_FLOW_HAS_DEPENDENT = URIRef("g:cf_has_dependent")


def create_graph_from_control_flow(element: CFElement) -> Graph:
    g = Graph()
    g.bind("g", Namespace("g"))

    if not isinstance(element.node, cst.FunctionDef):
        for body_line in range(element.body_start, element.body_end + 1):
            g.add((
                statement_to_node(element.main_line),
                RELATIONSHIP_CONTROL_FLOW_HAS_DEPENDENT,
                statement_to_node(body_line),
            ))

    for child in element.children:
        sub_graph = create_graph_from_control_flow(child)
        g += sub_graph
    return g
