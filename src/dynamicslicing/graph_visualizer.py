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

    nx_definition_edges = []
    nx_dataflow_edges = []

    for s, p, o in graph.triples((None, None, None)):
        s_label = node_to_label(s, source_lines)
        o_label = node_to_label(o, source_lines)
        pair = [s_label, o_label]
        if pair not in nx_edges:
            nx_edges.append(pair)
            nx_edge_labels[tuple(pair)] = str(p)

            if p in (RELATIONSHIP_DEFINITION_HAS_DEPENDENT, RELATIONSHIP_INIT_IS_MANDATORY_FOR):
                nx_definition_edges.append(pair)
            elif p in (RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY):
                nx_dataflow_edges.append(pair)
            else:
                raise RuntimeError("Unknown type of predicate: " + str(p))

    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from(nx_edges)

    pos = nx.spring_layout(nx_graph, scale=2, k=5 / math.sqrt(nx_graph.order()))
    plt.figure(figsize=(10, 10))

    nx.draw_networkx_nodes(nx_graph, pos,
                           node_size=200, alpha=0.45,
                           node_color=[get_node_color(node, result_statements) for node in nx_graph.nodes()]
                           )
    nx.draw_networkx_labels(nx_graph, pos)

    nx.draw_networkx_edges(nx_graph, pos, edgelist=nx_definition_edges, edge_color='brown', arrows=True, width=1,
                           alpha=0.3)
    nx.draw_networkx_edges(nx_graph, pos, edgelist=nx_dataflow_edges, edge_color='blue', arrows=True, width=3)

    if DRAW_EDGE_LABELS:
        nx.draw_networkx_edge_labels(
            nx_graph, pos,
            nx_edge_labels,
            font_color='black',
            alpha=0.7
        )
    plt.margins(x=0.4)
    plt.savefig(str(folder.joinpath("dependency_graph.png")))
    plt.show()

    # Save it to turtle file also
    graph.serialize(destination=str(folder.joinpath("dependency_graph.ttl")), format='turtle')
