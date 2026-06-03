import pytest
from unittest.mock import Mock, MagicMock, patch
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, RDF, Namespace
from src.kgverifypy.validation_service import ShaclValidationService


PATCH_LOCATION = "src.kgverifypy.validation_service"

# Unit tests ShaclValidationService.prepare_data_for_validation
@pytest.mark.parametrize(
        "rdfs_graph, datatypes, context_url",
        [
            pytest.param(None, False, None, id="Nothing to expand, no datatypes"),
            pytest.param(None, True, "http://example.com/context", id="No RDFS graph, but add datatypes, custom context"),
            pytest.param(None, True, None, id="No RDFS graph, but add datatypes"),
            pytest.param(Graph(), False, None, id="RDFS graph, no datatypes"),
            pytest.param(Graph(), True, "http://example.com/context", id="RDFS graph, add datatypes, custom context"),
            pytest.param(Graph(), True, None, id="RDFS graph, add datatypes"),
            pytest.param(None, True, "", id="Empty custom context"),
        ]
)
@patch(f"{PATCH_LOCATION}.add_datatypes_from_context")
def test_prepare_data_for_validation_various(mock_add_datatypes: MagicMock, rdfs_graph: Graph|None, datatypes: bool, context_url: str|None, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    service = ShaclValidationService()
    service._expand_with_rdfs = Mock()
    data_graph = Graph()

    service.prepare_data_for_validation(data_graph, rdfs_graph=rdfs_graph, add_datatypes=datatypes, context_url=context_url)
    if rdfs_graph is not None:
        service._expand_with_rdfs.assert_called_once_with(data_graph, rdfs_graph)
        assert "Expanding data graph with RDFS semantics from provided ontology." in caplog.text
    else:
        service._expand_with_rdfs.assert_not_called()

    if datatypes:
        mock_add_datatypes.assert_called_once_with(data_graph, context_url)
        context_info = context_url if context_url else "default context"
        assert f"Adding datatypes from context: {context_info}" in caplog.text
    else:
        mock_add_datatypes.assert_not_called()

    if rdfs_graph and datatypes:    # The expansion of data graph must be done before adding datatypes to ensure full enrichment
        assert service._expand_with_rdfs.call_args_list[0] < mock_add_datatypes.call_args_list[0]
    
@patch(f"{PATCH_LOCATION}.add_datatypes_from_context")
def test_prepare_data_for_validation_nodata(mock_add_datatypes: MagicMock) -> None:
    service = ShaclValidationService()
    service._expand_with_rdfs = Mock()

    # Pylance ignored for testing wrong input type
    service.prepare_data_for_validation(None, rdfs_graph=None, add_datatypes=True, context_url=None) # type: ignore

    mock_add_datatypes.assert_not_called()


# Unit tests ShaclValidationService._expand_with_rdfs

def test_expand_with_rdfs_fullcall() -> None:
    ex = Namespace("http://example.org/")

    data = Graph()
    data.bind("ex", ex)
    data.add((ex.john, RDF.type, ex.Person))

    rdfs = Graph()
    rdfs.add((ex.Person, RDFS.subClassOf, ex.Agent))
    rdfs.namespace_manager.bind("ex", ex)

    service = ShaclValidationService()
    service._expand_with_rdfs(data, rdfs)

    assert "ex" in dict(data.namespace_manager.namespaces())
    assert (ex.Person, RDFS.subClassOf, ex.Agent) in data
    assert (ex.john, RDF.type, ex.Agent) in data


EX = URIRef("http://example.org/")
EX2 = URIRef("http://other.example.org/")

@pytest.mark.parametrize(
    "initial_binding, rdfs_binding, expected_binding",
    [
        pytest.param(
            ("ex", EX),
            ("ex", EX),
            [("ex", EX)],
            id = "Prefix already bound to the same namespace → unchanged"
        ),
        pytest.param(
            ("ex", EX2),
            ("ex", EX),
            [("ex", EX2), ("ex1", EX)],
            id = "Prefix already bound to a different namespace, namespace added with new prefix"
        ),
        pytest.param(
            None,
            ("ex", EX),
            [("ex", EX)],
            id = "Prefix not bound at all → new binding added"
        ),
        pytest.param(
            ("ex", EX),
            ("ex1", EX),
            [("ex", EX)],
            id = "Different prefix already bound to the same namespace → unchanged"
        ),
    ],
)
def test_expand_with_rdfs_namespaceconflicts(initial_binding, rdfs_binding, expected_binding):
    data = Graph()
    rdfs = Graph()

    if initial_binding:
        prefix, ns = initial_binding
        data.namespace_manager.bind(prefix, ns)

    prefix, ns = rdfs_binding
    rdfs.namespace_manager.bind(prefix, ns)

    service = ShaclValidationService()
    service._expand_with_rdfs(data, rdfs)

    for prefix, ns in expected_binding:
        assert data.namespace_manager.store.namespace(prefix) == ns

@pytest.mark.parametrize(
    "data_graph, rdfs_graph",
    [
        pytest.param(None, None, id="No data graph, no RDFS graph"),
        pytest.param(Graph(), None, id="Empty data graph, no RDFS graph"),
        pytest.param(None, Graph(), id="No data graph, empty RDFS graph"),
    ]
)
@patch(f"{PATCH_LOCATION}.DeductiveClosure.expand")
def test_expand_with_rdfs_emptygraphs(mock_expand, data_graph, rdfs_graph):
    service = ShaclValidationService()
    service._expand_with_rdfs(data_graph, rdfs_graph)

    mock_expand.assert_not_called()

if __name__ == "__main__":
    pytest.main()