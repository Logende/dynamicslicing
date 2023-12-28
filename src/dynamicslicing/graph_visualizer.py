import math
from typing import Sequence

import rdflib
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from .dependency_graph_dataflow import RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY
from .dependency_graph_definitions import RELATIONSHIP_INIT_IS_MANDATORY_FOR, RELATIONSHIP_DEFINITION_HAS_DEPENDENT
from .dependency_graph_utils import node_to_statement
from .settings import DRAW_EDGE_LABELS


def node_to_label(node: rdflib.term.Node, source_lines: list[str]) -> str:
    if isinstance(node, rdflib.URIRef):
        try:
            statement = node_to_statement(node)
            if statement == -1:
                return "-1"
            else:
                return str(statement) + ": '" + source_lines[statement - 1].strip() + "'"
        except ValueError:
            pass

    else:
        return str(node)


def get_node_color(node, result_statements: Sequence[int]) -> str:
    corresponding_statement = int(str(node).split(":")[0].strip())
    if corresponding_statement in result_statements:
        return "green"
    else:
        return "red"


def save_rdf_graph(graph: rdflib.Graph, folder: Path, source: str, result_statements: Sequence[int]):
    source_lines = source.splitlines()

    nx_edges = []
    nx_edge_labels = {}
    # todo: fix edge colors. Somehow mixed up in few cases
    nx_edge_colors = []

    for s, p, o in graph.triples((None, None, None)):
        s_label = node_to_label(s, source_lines)
        o_label = node_to_label(o, source_lines)
        pair = [s_label, o_label]
        if pair not in nx_edges:
            nx_edges.append(pair)
            nx_edge_labels[tuple(pair)] = str(p)

            if p in (RELATIONSHIP_DEFINITION_HAS_DEPENDENT, RELATIONSHIP_INIT_IS_MANDATORY_FOR):
                nx_edge_colors.append("brown")
            elif p in (RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY):
                nx_edge_colors.append("green")
            else:
                raise RuntimeError("Unknown type of predicate: " + str(p))

    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from(nx_edges)

    pos = nx.spring_layout(nx_graph, scale=2, k=5/math.sqrt(nx_graph.order()))
    plt.figure(figsize=(10, 10))
    nx.draw(
        nx_graph, pos, edge_color=nx_edge_colors, width=1, linewidths=1,
        node_size=200, alpha=0.6,
        labels={node: node for node in nx_graph.nodes()},
        node_color=[get_node_color(node, result_statements) for node in nx_graph.nodes()]
    )
    if DRAW_EDGE_LABELS:
        nx.draw_networkx_edge_labels(
            nx_graph, pos,
            nx_edge_labels,
            font_color='black',
            alpha=0.7
        )

    plt.savefig(str(folder.joinpath("dependency_graph.png")))
    plt.show()

    # Save it to turtle file also
    graph.serialize(destination=str(folder.joinpath("dependency_graph.ttl")), format='turtle')
