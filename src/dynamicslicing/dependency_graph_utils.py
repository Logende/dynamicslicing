from rdflib import URIRef


def statement_to_node(line: int) -> URIRef:
    return URIRef("g:statement_" + str(line))


def node_to_statement(node: URIRef) -> int:
    return int(str(node).replace("g:statement_", ""))
