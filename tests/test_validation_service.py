import pytest
from unittest.mock import Mock, MagicMock, patch
from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDFS, RDF, Namespace, SH
from src.kgverifypy.validation_service import (
    FocusNodeSummary, 
    ShaclValidationResult, 
    ShaclValidationService, 
    find_focus_nodes, 
    summarize_validation_results,
)

PATCH_LOCATION = "src.kgverifypy.validation_service"

# Unit tests ShaclValidationService.prepare_data_for_validation
@pytest.mark.parametrize(
        "rdfs_graph, datatypes, context_dict",
        [
            pytest.param(None, False, None, id="Nothing to expand, no datatypes"),
            pytest.param(None, True, {"@context": "http://example.com/context"}, id="No RDFS graph, but add datatypes, custom context"),
            pytest.param(None, True, None, id="No RDFS graph, but add datatypes"),
            pytest.param(Graph(), False, None, id="RDFS graph, no datatypes"),
            pytest.param(Graph(), True, {"@context": "http://example.com/context"}, id="RDFS graph, add datatypes, custom context"),
            pytest.param(Graph(), True, None, id="RDFS graph, add datatypes"),
            pytest.param(None, True, {}, id="Empty custom context"),
        ]
)
@patch(f"{PATCH_LOCATION}.add_datatypes_from_context")
def test_prepare_data_for_validation_various(mock_add_datatypes: MagicMock, rdfs_graph: Graph|None, datatypes: bool, context_dict: dict|None, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    service = ShaclValidationService()
    service._expand_with_rdfs = Mock()
    data_graph = Graph()

    service.prepare_data_for_validation(data_graph, rdfs_graph=rdfs_graph, add_datatypes=datatypes, context_data=context_dict)
    if rdfs_graph is not None:
        service._expand_with_rdfs.assert_called_once_with(data_graph, rdfs_graph)
        assert "Expanding data graph with RDFS semantics from provided ontology." in caplog.text
    else:
        service._expand_with_rdfs.assert_not_called()

    if datatypes:
        mock_add_datatypes.assert_called_once_with(data_graph, context_dict)
        context_info = "custom context" if context_dict else "default context"
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
    service.prepare_data_for_validation(None, rdfs_graph=None, add_datatypes=True, context_data=None) # type: ignore

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
def test_expand_with_rdfs_namespaceconflicts(initial_binding: tuple, rdfs_binding: tuple, expected_binding: list[tuple]) -> None:
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
def test_expand_with_rdfs_emptygraphs(mock_expand: MagicMock, data_graph: Graph, rdfs_graph: Graph) -> None:
    service = ShaclValidationService()
    service._expand_with_rdfs(data_graph, rdfs_graph)

    mock_expand.assert_not_called()

# Unit tests ShaclValidationService.summarize_focus_nodes
@pytest.mark.parametrize(
    "data_graph, shacl_graph",
    [
        pytest.param(None, None, id="No data graph, no SHACL graph"),
        pytest.param(Graph(), None, id="Empty data graph, no SHACL graph"),
        pytest.param(None, Graph(), id="No data graph, empty SHACL graph"),
    ]
)
def test_summarize_focus_nodes_nographs(data_graph: Graph, shacl_graph: Graph) -> None:
    service = ShaclValidationService()

    result = service.summarize_focus_nodes(data_graph, shacl_graph)

    assert result is None

def test_summarize_focus_nodes_noexplicitfocusnodes() -> None:
    data = Graph()
    shapes = Graph()

    EX = Namespace("http://example.org/")
    shape = EX.Shape1
    shapes.add((shape, RDF.type, SH.NodeShape))
    shapes.add((shape, SH.targetClass, EX.Person))

    service = ShaclValidationService()
    result = service.summarize_focus_nodes(data, shapes)

    assert isinstance(result, FocusNodeSummary)
    assert result.total_shapes == 1
    assert result.shapes_with_focus_nodes == 0

def test_summarize_focus_nodes_withfocusnodes() -> None:
    data = Graph()
    shapes = Graph()

    EX = Namespace("http://example.org/")
    shape1 = EX.Shape1
    shapes.add((shape1, RDF.type, SH.NodeShape))
    shapes.add((shape1, SH.targetClass, EX.Person))

    shape2 = EX.Shape2
    shapes.add((shape2, RDF.type, SH.NodeShape))
    shapes.add((shape2, SH.targetNode, EX.special))

    data.add((EX.a, RDF.type, EX.Person))
    data.add((EX.special, RDF.type, EX.Thing))

    service = ShaclValidationService()
    result = service.summarize_focus_nodes(data, shapes)

    assert isinstance(result, FocusNodeSummary)
    assert result.total_shapes == 2
    assert result.shapes_with_focus_nodes == 2

@pytest.mark.parametrize(
    "mock_return, expected_result",
    [
        pytest.param([], (0, 0), id="No shapes, no focus nodes"),
        pytest.param([("shape1", set())], (1, 0), id="One shape, no focus nodes"),
        pytest.param([("shape1", {"node1"})], (1, 1), id="One shape, one focus node"),
        pytest.param([("shape1", {"node1", "node2"})], (1, 1), id="One shape, multiple focus nodes"),
        pytest.param([("shape1", set()), ("shape2", {"node2"})], (2, 1), id="Multiple shapes, one with focus nodes"),
    ]
)
@patch(f"{PATCH_LOCATION}.find_focus_nodes")
def test_summarize_focus_nodes_focusnodesoddreturns(mock_find_focus_nodes: MagicMock, mock_return: list, expected_result: tuple) -> None:
    mock_find_focus_nodes.return_value = mock_return
    service = ShaclValidationService()

    result = service.summarize_focus_nodes(Graph(), Graph())

    assert isinstance(result, FocusNodeSummary)
    assert (result.total_shapes, result.shapes_with_focus_nodes) == expected_result

def test_summarize_focus_nodes_circularshacl() -> None:
    # Documents what happends if there are circular references between shapes in the SHACL file. 
    data = Graph()
    shapes = Graph()

    EX = Namespace("http://example.org/")
    shape1 = EX.Shape1
    shape2 = EX.Shape2
    shapes.add((shape2, RDF.type, SH.NodeShape))
    shapes.add((shape1, RDF.type, SH.NodeShape))

    shapes.add((shape1, SH.node, shape2))
    shapes.add((shape2, SH.node, shape1))  # Circular reference to shape1

    data.add((EX.a, RDF.type, EX.Person))

    service = ShaclValidationService()
    result = service.summarize_focus_nodes(data, shapes)

    assert isinstance(result, FocusNodeSummary)
    assert result.total_shapes == 2
    assert result.shapes_with_focus_nodes == 0


# Unit tests ShaclValidationService.validate_graphs
@pytest.mark.parametrize(
    "data_graph, shacl_graph",
    [        
        pytest.param(None, None, id="No data graph, no SHACL graph"),
        pytest.param(Graph(), None, id="Empty data graph, no SHACL graph"),
        pytest.param(None, Graph(), id="No data graph, empty SHACL graph"),
    ]
)
@patch(f"{PATCH_LOCATION}.validate")
def test_validate_graphs_nographs(mock_validate: MagicMock, data_graph: Graph | None, shacl_graph: Graph | None) -> None:
    service = ShaclValidationService()

    result = service.validate_graphs(data_graph, shacl_graph, None)

    assert result is None
    mock_validate.assert_not_called()

@pytest.mark.parametrize(
    "rdfs_graph",
    [
        pytest.param(None, id="No RDFS graph"),
        pytest.param(Graph(), id="Empty RDFS graph"),
    ]
)
@patch(f"{PATCH_LOCATION}.summarize_validation_results")
@patch(f"{PATCH_LOCATION}.validate")
def test_validate_graphs_rdfsgraphs(mock_validate: MagicMock, mock_summarize: MagicMock, rdfs_graph: Graph) -> None:
    mock_graph = Graph()
    mock_validate.return_value = (True, mock_graph, None)  # Mocking a successful validation with an empty results graph
    mock_summarize.return_value = [("ConstraintA", 2), ("ConstraintB", 1)]  # Mocking summary results
    EX = Namespace("http://example.org/")
    data_graph = Graph()
    data_graph.bind("ex", EX)
    data_graph.add((EX.a, RDF.type, EX.Person))
    shacl_graph = Graph()
    shacl_graph.bind("ex", EX)
    shacl_graph.add((EX.Shape1, RDF.type, SH.NodeShape))

    service = ShaclValidationService()
    result = service.validate_graphs(data_graph, shacl_graph, rdfs_graph)

    assert isinstance(result, ShaclValidationResult)
    assert result.conforms is True
    assert result.results_graph is mock_graph
    assert result.summary_validation_results == [("ConstraintA", 2), ("ConstraintB", 1)]

    mock_summarize.assert_called_once_with(mock_graph)
    if rdfs_graph is None:
        mock_validate.assert_called_once_with(
            data_graph,
            shacl_graph=shacl_graph,
            ont_graph=None,
            inference="none",
            debug=False,
        )
    else:
        mock_validate.assert_called_once_with(
            data_graph,
            shacl_graph=shacl_graph,
            ont_graph=rdfs_graph,
            inference="rdfs",
            debug=False,
        )


@pytest.mark.parametrize(
    "return_value",
    [
        pytest.param((True, Graph(), None), id="Expected return types"),
        pytest.param(("false", Graph(), None), id="Unexpected conforms type"),
        pytest.param((True, "not a graph", None), id="Unexpected results graph type"),
        pytest.param((True, Graph(), "whatever"), id="Last tuple value is irrelevant"),
    ]
)
@patch(f"{PATCH_LOCATION}.summarize_validation_results")
@patch(f"{PATCH_LOCATION}.validate")
def test_validate_graphs_oddreturns(mock_validate: MagicMock, mock_summarize: MagicMock, return_value: tuple) -> None:
    mock_validate.return_value = return_value
    mock_summarize.return_value = [("ConstraintA", 2), ("ConstraintB", 1)]

    EX = Namespace("http://example.org/")
    data_graph = Graph()
    data_graph.bind("ex", EX)
    data_graph.add((EX.a, RDF.type, EX.Person))
    shacl_graph = Graph()
    shacl_graph.bind("ex", EX)
    shacl_graph.add((EX.Shape1, RDF.type, SH.NodeShape))

    service = ShaclValidationService()
    result = service.validate_graphs(data_graph, shacl_graph, None)

    assert isinstance(result, ShaclValidationResult)
    assert result.conforms == (return_value[0] if isinstance(return_value[0], bool) else False)
    assert result.results_graph == (return_value[1] if isinstance(return_value[1], Graph) else None)
    assert result.summary_validation_results == (mock_summarize.return_value if isinstance(return_value[1], Graph) else None)

# Unit tests ShaclValidationService.serialize_results
def test_serialize_results_nonegraph() -> None:
    service = ShaclValidationService()
    result = service.serialize_results(None, "output.ttl", "turtle")

    assert result is False

def test_serialize_results_validgraph() -> None:
    service = ShaclValidationService()
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.a, RDF.type, EX.Person))
    graph.serialize = Mock()

    output_file = "output.ttl"
    result = service.serialize_results(graph, output_file, "ttl")

    assert result is True
    graph.serialize.assert_called_once_with(destination=output_file, format="ttl")
    
# Unit tests find_focus_nodes
EX = Namespace("http://example.org/")

@pytest.mark.parametrize(
    "shape_type, shape_triples, data_triples, expected",
    [
        pytest.param(
            EX.Shape_targetClass,
            [(SH.targetClass, EX.Person)],
            [(EX.a, RDF.type, EX.Person)],
            {EX.a},
            id="targetClass"
        ),
        pytest.param(
            EX.Shape_targetNode,
            [(SH.targetNode, EX.b)],
            [],  # data graph irrelevant
            {EX.b},
            id="targetNode"
        ),
        pytest.param(
            EX.Shape_targetSubjectsOf,
            [(SH.targetSubjectsOf, EX.knows)],
            [(EX.s, EX.knows, EX.o)],
            {EX.s},
            id="targetSubjectsOf"
        ),
        pytest.param(
            EX.Shape_targetObjectsOf,
            [(SH.targetObjectsOf, EX.likes)],
            [(EX.s, EX.likes, EX.o)],
            {EX.o},
            id="targetObjectsOf"
        ),
        pytest.param(
            EX.Shape_targetClass,
            [(SH.targetClass, EX.Person)],
            [(EX.a, RDF.type, EX.Person), (EX.b, RDF.type, EX.Person)],
            {EX.a, EX.b},
            id="targetClass with multiple matches"
        ),
        pytest.param(
            EX.Shape_noFocus,
            [(RDF.type, EX.NoFocus)],  # No targeting triples
            [],  # No data triples
            set(),
            id="No focus nodes"
        ),
        pytest.param(
            EX.ShapeMissing,
            [(RDF.type, SH.NodeShape), (SH.targetClass, EX.doesNotExist), (SH.targetSubjectsOf, EX.nonexistentProp)],
            [],
            set(),
            id="Shape with missing targets"
        )
    ]
)
def test_find_focus_nodes_shapetypes(shape_type: URIRef, shape_triples: list[tuple], data_triples: list[tuple], expected: set) -> None:
    data = Graph()
    shapes = Graph()

    # Add data triples
    data.add((URIRef("http://example.org/noise"), RDF.type, URIRef("http://example.org/Noise")))  # Extra triple for noise
    for s, p, o in data_triples:
        data.add((s, p, o))

    # Create shape
    shapes.add((shape_type, RDF.type, SH.NodeShape))

    # Add shape triples
    for p, o in shape_triples:
        shapes.add((shape_type, p, o))

    results = dict(find_focus_nodes(data, shapes))

    assert shape_type in results
    assert results[shape_type] == expected

@pytest.mark.parametrize(
    "shape_defs,data_triples,expected_map",
    [
        pytest.param(
            {
                EX.Shape1: [(SH.targetClass, EX.Person)],
                EX.Shape2: [(SH.targetSubjectsOf, EX.knows)],
            },
            [
                (EX.a, RDF.type, EX.Person),
                (EX.x, EX.knows, EX.y),
            ],
            {
                EX.Shape1: {EX.a},
                EX.Shape2: {EX.x},
            },
            id="targetClass and targetSubjectsOf"
        ),
        pytest.param(
            {
                EX.ShapeA: [(SH.targetNode, EX.special)],
                EX.ShapeB: [(SH.targetObjectsOf, EX.likes)],
            },
            [
                (EX.s, EX.likes, EX.o),
            ],
            {
                EX.ShapeA: {EX.special},
                EX.ShapeB: {EX.o},
            },
            id="targetNode and targetObjectsOf"
        ),
        pytest.param(
            {
                EX.ShapeMulti: [(SH.targetClass, EX.Person), (SH.targetSubjectsOf, EX.knows), (SH.targetNode, EX.special)],
            },
            [
                (EX.a, RDF.type, EX.Person),
                (EX.x, EX.knows, EX.y),
            ],
            {
                EX.ShapeMulti: {EX.a, EX.x, EX.special},
            },
            id="Shape with multiple target types"
        )
    ],
)
def test_find_focus_nodes_multipleshapes(shape_defs: dict, data_triples: list[tuple], expected_map: dict) -> None:
    data = Graph()
    shapes = Graph()

    # Add data
    for s, p, o in data_triples:
        data.add((s, p, o))

    # Add shapes
    for shape, triples in shape_defs.items():
        shapes.add((shape, RDF.type, SH.NodeShape))
        for p, o in triples:
            shapes.add((shape, p, o))

    results = dict(find_focus_nodes(data, shapes))

    assert results == expected_map

def test_find_focus_nodes_noshapes() -> None:
    data = Graph()
    shapes = Graph()

    results = dict(find_focus_nodes(data, shapes))

    assert results == {}

@pytest.mark.parametrize(
    "data_graph, shapes_graph",
    [
        pytest.param(None, None, id="No data graph, no shapes graph"),
        pytest.param(Graph(), None, id="Empty data graph, no shapes graph"),
        pytest.param(None, Graph(), id="No data graph, empty shapes graph"),
    ]
)
def test_find_focus_nodes_graphnone(data_graph: Graph, shapes_graph: Graph) -> None:

    results = find_focus_nodes(data_graph, shapes_graph)

    assert results == []


def test_find_focus_nodes_nodeshape_propertyshape_ordering() -> None:
    data = Graph()
    shapes = Graph()

    # Data
    EX = Namespace("http://example.org/")
    data.add((EX.a, RDF.type, EX.Person))
    data.add((EX.s, EX.knows, EX.o))

    # NodeShape
    EX = Namespace("http://example.org/")
    shape1 = EX.NodeShape1
    shapes.add((shape1, RDF.type, SH.NodeShape))
    shapes.add((shape1, SH.targetClass, EX.Person))

    # PropertyShape
    shape2 = EX.PropShape2
    shapes.add((shape2, RDF.type, SH.PropertyShape))
    shapes.add((shape2, SH.targetSubjectsOf, EX.knows))

    results = find_focus_nodes(data, shapes)

    # Check order: NodeShape first, then PropertyShape
    assert results[0][0] == shape1
    assert results[1][0] == shape2

def test_find_focus_nodes_blanknodeshape() -> None:
    data = Graph()
    shapes = Graph()

    # Data
    EX = Namespace("http://example.org/")
    data.add((EX.a, RDF.type, EX.Person))

    # Blank node shape
    shape = BNode()
    shapes.add((shape, RDF.type, SH.NodeShape))
    shapes.add((shape, SH.targetClass, EX.Person))

    results = dict(find_focus_nodes(data, shapes))

    assert results[shape] == {EX.a}


# Unit tests summarize_validation_results
@pytest.mark.parametrize(
    "graph",
    [
        pytest.param(None, id="No graph"),
        pytest.param(Graph(), id="Empty graph"),
    ]
)
def test_summarize_validation_results_nograph(graph: Graph | None) -> None:
    # Pylance ignored for testing wrong input type
    result = summarize_validation_results(graph) # type: ignore

    assert result == []


def test_summarize_validation_results_nomatching() -> None:
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.a, EX.b, EX.c))

    result = summarize_validation_results(graph)

    assert result == []


def test_summarize_validation_results_multiplehits() -> None:
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.violation1, EX.noise, EX.ConstraintC))
    graph.add((EX.violation1, SH.sourceConstraintComponent, EX.ConstraintA))
    graph.add((EX.violation2, SH.sourceConstraintComponent, EX.ConstraintA))
    graph.add((EX.violation3, SH.sourceConstraintComponent, EX.ConstraintB))

    result = summarize_validation_results(graph)

    assert result == [(EX.ConstraintA, 2), (EX.ConstraintB, 1)]

def test_summarize_validation_results_acceptssubclasses() -> None:
    class SubGraph(Graph):
        pass

    graph = SubGraph()  # Using a subclass of Graph to test isinstance check
    EX = Namespace("http://example.org/")
    graph.add((EX.violation1, SH.sourceConstraintComponent, EX.ConstraintA))

    result = summarize_validation_results(graph)

    assert result == [(EX.ConstraintA, 1)]


if __name__ == "__main__":
    pytest.main()