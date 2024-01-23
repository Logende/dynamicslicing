"""Utility file used to make sure the different RDF graph functions use the same node naming conventions."""

from rdflib import URIRef


def statement_to_node(line: int) -> URIRef:
    return URIRef("g:statement_" + str(line))


def node_to_statement(node: URIRef) -> int:
    return int(str(node).replace("g:statement_", ""))
