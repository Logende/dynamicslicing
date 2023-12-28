from rdflib import Graph, URIRef, Namespace
import libcst as cst

from dynamicslicing.dependency_graph_utils import statement_to_node
from dynamicslicing.finders import Definition

RELATIONSHIP_DEFINITION_HAS_DEPENDENT = URIRef("g:definition_has_dependent")
RELATIONSHIP_INIT_IS_MANDATORY_FOR = URIRef("g:init_is_mandatory_for")


def create_graph_from_definitions(definitions: dict[str, Definition]) -> Graph:
    g = Graph()
    g.bind("g", Namespace("g"))

    for name, definition in definitions.items():
        # make every line inside the definition dependent on the first line of the definition
        definition_start = definition.location.start.line

        for line in range(definition.location.start.line + 1, definition.location.end.line + 1):
            g.add((
                statement_to_node(definition_start),
                RELATIONSHIP_DEFINITION_HAS_DEPENDENT,
                statement_to_node(line),
            ))

        if definition.name == "__init__" and isinstance(definition.node, cst.FunctionDef):
            # always make classes dependent on complete init
            # todo: optimize to only use needed part of init
            class_def_line = definition.parent.location.start.line
            for init_line in range(definition.location.start.line, definition.location.end.line + 1):
                g.add((
                    statement_to_node(init_line),
                    RELATIONSHIP_INIT_IS_MANDATORY_FOR,
                    statement_to_node(class_def_line),
                ))

        sub_graph = create_graph_from_definitions(definition.children)
        g += sub_graph
    return g
