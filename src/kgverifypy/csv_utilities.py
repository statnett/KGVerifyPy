from rdflib import Graph, URIRef, RDF, Node
from pathlib import Path
from dataclasses import dataclass, asdict
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
    subject_uuid: str
    predicate: str
    object: str
    constraint_component: str
    shape: str
    severity: str
    message: str

def extract_violations_from_graph(graph: Graph, subject: Node) -> ConstraintViolation:
    """Extracts violation details from a SHACL result RDF graph and subject node.

    Parameters:
        graph (Graph): The RDF graph containing the SHACL validation results.
        subject (Node): The subject node for which to extract violation details.
    
    Returns:
        ConstraintViolation: A dataclass instance containing the extracted violation details.
    """
    data = {}
    for key, value in PREDICATE_MAP.items():
        temp_list = list(graph.objects(subject, URIRef(value)))
        if len(temp_list) == 1:
            data[key] = str(temp_list[0])
        elif len(temp_list) == 0:
            data[key] = "N/A"
        else:
            data[key] = ", ".join(str(item) for item in temp_list)

    return ConstraintViolation(**data)

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
    datafile = Path.cwd().parent / "validation_results.json"
    g = Graph()
    g.parse(datafile, format="json-ld")
    violations = collect_violations(g)
    print(f"Collected {len(violations)} violations.")
    output_csv = Path.cwd() / "violations_output.csv"
    write_shacl_violations_to_csv(violations, output_csv)