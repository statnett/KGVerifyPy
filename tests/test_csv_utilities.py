import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from rdflib import Graph, URIRef, Literal, Node, BNode
from rdflib.namespace import RDF, SH, XSD
from src.kgverifypy.csv_utilities import (
    PREDICATE_MAP,
    ConstraintViolation, 
    extract_violations_from_graph, 
    collect_violations, 
    write_shacl_violations_to_csv
)

PATCH_LOCATION = "src.kgverifypy.csv_utilities"

# Test to ensure that all fields in ConstraintViolation are present in the PREDICATE_MAP
def test_all_fields_present() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")

    violation = extract_violations_from_graph(g, subject)

    assert set(vars(violation).keys()) == set(PREDICATE_MAP.keys())


# Unit tests extract_violations_from_graph
def test_extract_violations_from_graph_emptygraph() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    violation = extract_violations_from_graph(g, subject)

    assert isinstance(violation, ConstraintViolation)
    assert violation.subject_uuid == "N/A"
    assert violation.predicate == "N/A"
    assert violation.object == "N/A"
    assert violation.constraint_component == "N/A"
    assert violation.shape == "N/A"
    assert violation.severity == "N/A"
    assert violation.message == "N/A"

def test_extract_violations_from_graph_withsomevalues() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject") 
    g.add((subject, RDF.type, SH.ValidationResult)) # Noise
    g.add((subject, SH.focusNode, URIRef("http://example.org/focusNode")))
    g.add((subject, SH.resultPath, URIRef("http://example.org/predicate")))
    g.add((subject, SH.value, URIRef("http://example.org/object1")))
    g.add((subject, SH.value, URIRef("http://example.org/object2")))
    violation = extract_violations_from_graph(g, subject)

    assert violation.subject_uuid == "http://example.org/focusNode"
    assert violation.predicate == "http://example.org/predicate"
    assert violation.object == "http://example.org/object1, http://example.org/object2"
    assert violation.constraint_component == "N/A"
    assert violation.shape == "N/A"
    assert violation.severity == "N/A"
    assert violation.message == "N/A"


def test_extract_violations_from_graph_allvalues() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    g.add((subject, SH.focusNode, URIRef("http://example.org/focusNode")))
    g.add((subject, SH.resultPath, URIRef("http://example.org/predicate")))
    g.add((subject, SH.value, URIRef("http://example.org/object1")))
    g.add((subject, SH.sourceConstraintComponent, URIRef("http://example.org/constraintComponent")))
    g.add((subject, SH.sourceShape, URIRef("http://example.org/shape")))
    g.add((subject, SH.resultSeverity, URIRef("http://example.org/severity")))
    g.add((subject, SH.resultMessage, Literal("Violation message")))
    violation = extract_violations_from_graph(g, subject)

    assert isinstance(violation, ConstraintViolation)
    assert violation.subject_uuid == "http://example.org/focusNode"
    assert violation.predicate == "http://example.org/predicate"
    assert violation.object == "http://example.org/object1"
    assert violation.constraint_component == "http://example.org/constraintComponent"
    assert violation.shape == "http://example.org/shape"
    assert violation.severity == "http://example.org/severity"
    assert violation.message == "Violation message"


B = BNode()  # Create a single BNode instance for testing
@pytest.mark.parametrize(
        "object",
        [
            pytest.param(Literal("Literal value"), id="Literal string value"),
            pytest.param(Literal(""), id="Literal empty string value"),
            pytest.param(Literal(42), id="Literal integer value"),
            pytest.param(Literal(42, datatype=XSD.integer), id="Literal integer value with datatype"),
            pytest.param(B, id="BNode value")
        ]
)
def test_extract_violations_from_graph_edgecases(object: Node) -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    g.add((subject, SH.focusNode, object))

    violation = extract_violations_from_graph(g, subject)

    if isinstance(object, Literal) and object.datatype is not None:
        assert violation.subject_uuid == str(object.value)
    else:
        assert violation.subject_uuid == str(object)


def test_extract_violations_from_graph_mixedvaluetypes() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")

    g.add((subject, SH.value, Literal("text")))
    g.add((subject, SH.value, BNode()))

    violation = extract_violations_from_graph(g, subject)

    parts = violation.object.split(", ")
    assert len(parts) == 2

def test_extract_violations_from_graph_nomatchingsubject() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    other = URIRef("http://example.org/other")

    g.add((other, SH.value, Literal("foo")))

    violation = extract_violations_from_graph(g, subject)

    assert violation.object == "N/A"


# Unit tests collect_violations
@pytest.mark.parametrize(
    "triples",
    [
        pytest.param([], id="Empty graph"),
        pytest.param([(URIRef("http://example.org/subject"), RDF.type, SH.ValidationReport)], id="Graph without ValidationResult type"),
    ]
)
def test_collect_violations_emptyresult(triples: list[tuple[Node, URIRef, Node]]) -> None:
    g = Graph()
    for triple in triples:
        g.add(triple)
    
    violations = collect_violations(g)
    assert violations == []


@patch(f"{PATCH_LOCATION}.extract_violations_from_graph")
def test_collect_violations_extractcalls(mock_extract: MagicMock) -> None:
    mock_extract.side_effect = ["v1", "v2"]
    g = Graph()
    subject1 = URIRef("http://example.org/subject1")
    subject2 = URIRef("http://example.org/subject2")
    g.add((subject1, RDF.type, SH.ValidationResult))
    g.add((subject2, RDF.type, SH.ValidationResult))

    result = collect_violations(g)

    assert mock_extract.call_count == 2
    mock_extract.assert_any_call(g, subject1)
    mock_extract.assert_any_call(g, subject2)

    assert result == ["v1", "v2"]


# Unit tests write_shacl_violations_to_csv
@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_emptylist(mock_file: MagicMock) -> None:
    write_shacl_violations_to_csv([], "output.csv")

    mock_file.assert_not_called()


@pytest.mark.parametrize(
    "filepath",
    [
        pytest.param("output.csv", id="String file path"),
        pytest.param(Path("output.csv"), id="Path object file path")
    ]
)
@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_writing(mock_file: MagicMock, filepath: str | Path) -> None:
    violations = [
        ConstraintViolation(
            subject_uuid="s",
            predicate="p",
            object="o",
            constraint_component="c",
            shape="sh",
            severity="sev",
            message="msg"
        )
    ]

    write_shacl_violations_to_csv(violations, filepath)

    mock_file.assert_called_once_with(filepath, 'w', newline='', encoding='utf-8')
    handle = mock_file()
    handle.write.assert_called()

    written = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "subject_uuid;predicate;object;constraint_component;shape;severity;message" in written
    assert "s;p;o;c;sh;sev;msg" in written


@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_multiplerows(mock_file: MagicMock) -> None:
    v1 = ConstraintViolation(
        subject_uuid="s1",
        predicate="p1",
        object="o1",
        constraint_component="c1",
        shape="sh1",
        severity="sev1",
        message="msg1"
    )
    v2 = ConstraintViolation(
        subject_uuid="s2",
        predicate="p2",
        object="o2",
        constraint_component="c2",
        shape="sh2",
        severity="sev2",
        message="msg2"
    )
    violations = [v1, v2]

    write_shacl_violations_to_csv(violations, "output.csv")

    handle = mock_file()
    assert handle.write.call_count == 3  # header + 2 rows


@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_specialcharacters(mock_file: MagicMock) -> None:
    violations = [
        ConstraintViolation(
            subject_uuid="s;1",
            predicate="p\nline",
            object='o"quote',
            constraint_component="cc",
            shape="sh",
            severity="sev",
            message="msg",
        )
    ]

    write_shacl_violations_to_csv(violations, "output.csv")

    handle = mock_file()

    assert '"s;1";"p\nline";"o""quote";cc;sh;sev;msg\r\n' in handle.write.call_args_list[1][0][0]  # Check the first data row for proper escaping

@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_invalidtype(mock_file: MagicMock) -> None:
    with pytest.raises(TypeError):
        # Pylance silenced to test invalid input type handling
        write_shacl_violations_to_csv([{"not": "dataclass"}], "output.csv") # type: ignore

    mock_file.assert_called_once() 

if __name__ == "__main__":
    pytest.main()