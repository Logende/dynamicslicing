from typing import Set

from rdflib import URIRef
from rdflib import Graph


def get_dependency_nodes(graph: Graph, target_node: URIRef) -> Set[URIRef]:
    nodes: set[URIRef] = set()
    nodes.add(target_node)

    had_change = True

    while had_change:
        had_change = False

        new_nodes: set[URIRef] = set()

        for node in nodes:
            # todo: maybe it is possible to have a single query that returns all nodes connected
            # via any path, instead of going just one step and then repeating it
            sparql_query = f"""
            SELECT DISTINCT ?sourceNode
            WHERE {{
                ?sourceNode ?predicate ?targetNode.
            }}
            """
            query_result = graph.query(sparql_query, initBindings={'targetNode': node})
            for row in query_result:
                found_node = row.sourceNode
                if found_node not in nodes:
                    new_nodes.add(found_node)
                    had_change = True

        nodes.update(new_nodes)

    return nodes
