import rdflib
from rdflib import Literal
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path


def save_rdf_graph(graph: rdflib.Graph, folder: Path):
    networkx_graph = rdflib_to_networkx_multidigraph(graph)

    # Plot Networkx instance of RDF Graph
    # Adapted from https://stackoverflow.com/a/54095269/4743756
    pos = nx.spring_layout(networkx_graph, scale=2)
    edge_labels = nx.get_edge_attributes(networkx_graph, "r")
    nx.draw_networkx_edge_labels(networkx_graph, pos, edge_labels=edge_labels)
    nx.draw(networkx_graph, pos, with_labels=True)

    plt.show()
    plt.savefig(str(folder.joinpath("dependency_graph.png")))

    # Save it to turtle file also
    graph.serialize(destination=str(folder.joinpath("dependency_graph.turtle")), format='turtle')
