import math

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


def save_rdf_graph(graph: rdflib.Graph, folder: Path, source: str):
    source_lines = source.splitlines()

    nx_edges = []
    nx_edge_labels = {}
    nx_edge_colors = []

    for s, p, o in graph.triples((None, None, None)):
        s_label = node_to_label(s, source_lines)
        p_label = node_to_label(s, source_lines)
        o_label = node_to_label(o, source_lines)
        nx_edges.append([s_label, o_label])
        nx_edge_labels[s_label, o_label] = p_label

        if p in (RELATIONSHIP_DEFINITION_HAS_DEPENDENT, RELATIONSHIP_INIT_IS_MANDATORY_FOR):
            nx_edge_colors.append("brown")
        elif p in (RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY):
            nx_edge_colors.append("green")

    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from(nx_edges)
    pos = nx.spring_layout(nx_graph, scale=4, k=5/math.sqrt(nx_graph.order()))
    plt.figure()
    nx.draw(
        nx_graph, pos, edge_color=nx_edge_colors, width=1, linewidths=1,
        node_size=200, node_color='pink', alpha=0.6,
        labels={node: node for node in nx_graph.nodes()}
    )
    if DRAW_EDGE_LABELS:
        nx.draw_networkx_edge_labels(
            nx_graph, pos,
            nx_edge_labels,
            font_color='black',
            alpha=0.7
        )
    plt.axis('off')
    plt.show()

    plt.savefig(str(folder.joinpath("dependency_graph.png")))

    # Save it to turtle file also
    graph.serialize(destination=str(folder.joinpath("dependency_graph.ttl")), format='turtle')
