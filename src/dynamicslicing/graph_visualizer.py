"""This file provides a function to plot a RDF knowledge graph with dataflow, controlflow and structural dependencies.
"""

import math
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import networkx as nx
import rdflib
from matplotlib.lines import Line2D

from .dependency_graph_control_flow import RELATIONSHIP_CONTROL_FLOW_HAS_DEPENDENT
from .dependency_graph_dataflow import (RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY)
from .dependency_graph_definitions import RELATIONSHIP_DEFINITION_OUTSIDE_OF_ANALYSIS, \
    RELATIONSHIP_DEFINITION_HAS_DEPENDENT
from .dependency_graph_utils import node_to_statement
from .settings import DRAW_EDGE_LABELS, MAX_NODE_LABEL_LENGTH, PLOT_WIDTH, PLOT_HEIGHT


def node_to_label(node: rdflib.term.Node, source_lines: list[str]) -> str:
    result = str(node)

    if isinstance(node, rdflib.URIRef):
        try:
            statement = node_to_statement(node)
            if statement != -1:
                result = str(statement) + ": '" + source_lines[statement - 1].strip() + "'"
            else:
                result = "-1"
        except ValueError:
            pass

    return (result[:MAX_NODE_LABEL_LENGTH - 2] + '..') if len(result) > MAX_NODE_LABEL_LENGTH else result


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
    nx_control_flow_edges = []

    for s, p, o in graph.triples((None, None, None)):
        s_label = node_to_label(s, source_lines)
        o_label = node_to_label(o, source_lines)
        pair = [s_label, o_label]
        if pair not in nx_edges:
            nx_edges.append(pair)
            nx_edge_labels[tuple(pair)] = str(p)

            if p in (RELATIONSHIP_DEFINITION_HAS_DEPENDENT, RELATIONSHIP_DEFINITION_OUTSIDE_OF_ANALYSIS):
                nx_definition_edges.append(pair)
            elif p in (RELATIONSHIP_DEFINITION_IS_USED_BY, RELATIONSHIP_DEFINITION_IS_MODIFIED_BY):
                nx_dataflow_edges.append(pair)
            elif p in (RELATIONSHIP_CONTROL_FLOW_HAS_DEPENDENT,):
                nx_control_flow_edges.append(pair)
            else:
                raise RuntimeError("Unknown type of predicate: " + str(p))

    nx_graph = nx.DiGraph()
    nx_graph.add_edges_from(nx_edges)

    pos = nx.spring_layout(nx_graph, scale=2, k=5 / math.sqrt(nx_graph.order()))
    fig = plt.figure(figsize=(PLOT_WIDTH, PLOT_HEIGHT))
    ax = fig.add_subplot()
    ax.set_title(str(folder.parent.name) + "/" + str(folder.name))

    nx.draw_networkx_nodes(nx_graph, pos,
                           node_size=200, alpha=0.45,
                           node_color=[get_node_color(node, result_statements) for node in nx_graph.nodes()]
                           )
    nx.draw_networkx_labels(nx_graph, pos)

    nx.draw_networkx_edges(nx_graph, pos, edgelist=nx_control_flow_edges, edge_color='purple', arrows=True, width=2,
                           alpha=1)
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

    # add legend
    node_included = Line2D([0], [0], label='Statement in slice', marker='s', markersize=10,
                           markeredgecolor='green', markerfacecolor='green', linestyle='')
    node_excluded = Line2D([0], [0], label='Statement not in slice', marker='s', markersize=10,
                           markeredgecolor='red', markerfacecolor='red', linestyle='')
    edge_dataflow = Line2D([0], [0], label='Dataflow dependency', color='blue', linewidth=3)
    edge_control_flow = Line2D([0], [0], label='Control flow dependency', color='purple', linewidth=2)
    edge_structure = Line2D([0], [0], label='Structural dependency', color='brown', linewidth=1)
    handles = [node_included, node_excluded, edge_dataflow, edge_control_flow, edge_structure]
    plt.legend(handles=handles)

    # Save it as file and also show plot directly
    plt.savefig(str(folder.joinpath("dependency_graph.png")))
    plt.show()

    # Save it to turtle file also
    graph.serialize(destination=str(folder.joinpath("dependency_graph.ttl")), format='turtle')
