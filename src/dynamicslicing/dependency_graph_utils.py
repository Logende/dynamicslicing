from rdflib import URIRef


def statement_to_node(line: int) -> URIRef:
    return URIRef("g:statement_" + str(line))
