"""Utilities for reorganising the SHACL validation results into table format for CSV output."""

from rdflib import Graph, URIRef, RDF, Node, BNode, Literal
from rdflib.namespace import RDF
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import csv

PREDICATE_MAP = {
    "subject_uuid": "http://www.w3.org/ns/shacl#focusNode",
    "predicate": "http://www.w3.org/ns/shacl#resultPath",
    "object": "http://www.w3.org/ns/shacl#value",
    "constraint_component": "http://www.w3.org/ns/shacl#sourceConstraintComponent",
    "shape": "http://www.w3.org/ns/shacl#sourceShape",
    "severity": "http://www.w3.org/ns/shacl#resultSeverity",
    "message": "http://www.w3.org/ns/shacl#resultMessage",
}


@dataclass
class ConstraintViolation:
    """Dataclass to hold details of a single SHACL constraint violation."""
    
    subject_uuid: str
    predicate: str
    object: str
    constraint_component: str   # The type of contstraint that was violated (e.g., sh:MinCountConstraintComponent)
    shape: str  # The SHACL shape that was violated (e.g., sh:MinCountConstraintComponent)
    severity: str   # The severity of the violation (e.g., sh:Violation, sh:Warning, sh:Info)
    message: str


def extract_violations_from_graph(graph: Graph, subject: Node) -> ConstraintViolation:
    """Extracts violation details from a SHACL result RDF graph and subject node.

    Parameters:
        graph (Graph): The RDF graph containing the SHACL validation results.
        subject (Node): The subject node for which to extract violation details.
    
    Returns:
        ConstraintViolation: A dataclass instance containing the extracted violation details.
    """
    data: dict[str, str] = {}
    for key, value in PREDICATE_MAP.items():
        raw_objects = list(graph.objects(subject, URIRef(value)))

        resolved_values = []
        for obj in raw_objects:
            resolved_values.extend(resolve_node(graph, obj))

        if len(resolved_values) == 1:
            data[key] = resolved_values[0]
        elif len(resolved_values) == 0:
            data[key] = "N/A"
        else:
            data[key] = ", ".join(resolved_values)

    return ConstraintViolation(**data)


def resolve_node(graph: Graph, node: Node, seen: set[Node]|None=None) -> list[str]:
    """Recursively resolve a node to its string representation, handling RDF lists and blank nodes.
    
    Parameters:
        graph (Graph): The RDF graph containing the node.
        node (Node): The RDF node to resolve.
        seen (set[Node], optional): A set of already seen nodes to avoid infinite recursion. Defaults to None.
    """
    if seen is None:
        seen = set()

    if node in seen:
        return []

    seen.add(node)

    if isinstance(node, (Literal, URIRef)):
        return [str(node)]

    if isinstance(node, BNode):
        if is_rdf_list(graph, node):
            items = resolve_rdf_list(graph, node)
            return [" / ".join(items)] if items else []
        
        grouped = defaultdict(list)

        for pred, obj in graph.predicate_objects(node):
            grouped[pred].extend(resolve_node(graph, obj, seen))

        return [
            f"{pred}: {', '.join(values)}"
            for pred, values in grouped.items()
        ]

    return [str(node)]            


def is_rdf_list(graph: Graph, node) -> bool:
    """Check if a node is the head of an RDF list.
    
    Parameters:
        graph (Graph): The RDF graph containing the node.
        node (Node): The RDF node to check.
    
    Returns:
        bool: True if the node is the head of an RDF list, False otherwise.
    """
    return (isinstance(node, BNode) and (node, RDF.first, None) in graph)


def resolve_rdf_list(graph: Graph, node) -> list[str]:
    """Traverse RDF list and return ordered values.
    
    An RDF list is represented as a linked list using the RDF.first and RDF.rest predicates. 

    Parameters:
        graph (Graph): The RDF graph containing the list.
        node (Node): The head node of the RDF list.

    Returns:
        list[str]: A list of string representations of the items in the RDF list.
    """
    items = []
    visited = set()

    while node and node != RDF.nil and node not in visited:
        visited.add(node)

        first = graph.value(node, RDF.first)
        if first is not None:
            items.extend(resolve_node(graph, first))

        node = graph.value(node, RDF.rest)

    return items


def collect_violations(graph: Graph) -> list[ConstraintViolation]:
    """Collect all violations from a SHACL result RDF graph.

    Parameters:
        graph (Graph): The RDF graph containing the SHACL validation results.
    
    Returns:
        list[ConstraintViolation]: A list of dataclass instances containing the extracted violation details.
    """
    subjects = list(graph.subjects(RDF.type, URIRef("http://www.w3.org/ns/shacl#ValidationResult")))
    return [extract_violations_from_graph(graph, subject) for subject in subjects]


def write_shacl_violations_to_csv(violations: list[ConstraintViolation], output_file: Path | str) -> None:
    """Write a list of ConstraintViolation instances to a CSV file.

    Using semicolon as the delimiter and UTF-8 encoding. 

    Parameters:
        violations (list[ConstraintViolation]): The list of violations to write.
        output_file (Path | str): The path to the output CSV file.    
    """
    if not violations:
        return
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=asdict(violations[0]).keys(), delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for violation in violations:
            writer.writerow(asdict(violation))


if __name__ == "__main__":
    print("Utilities for outputting constraint violations to CSV.")
