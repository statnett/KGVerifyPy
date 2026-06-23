import pytest
from unittest.mock import patch, MagicMock, call
from rdflib import Graph, Literal, URIRef
from rdflib.plugin import PluginException
from pathlib import Path
from src.kgverifypy.file_handling import make_graphs_from, merge_trig_graphs

# Unit tests make_graph_from
@pytest.mark.parametrize(
    "files, format",
    [
        pytest.param(["file1.owl", "file2.owl"], "xml", id="Multiple files with default format"),
        pytest.param("file1.ttl", "ttl", id="Single file with specified format"),
        pytest.param([], "xml", id="Empty file list"),
        pytest.param(["", "file2.owl"], "xml", id="One file is empty string"),
    ]
)
@patch.object(Graph, "parse")
def test_make_graph_from(mock_parse: MagicMock, files: list|str, format: str) -> None:
    g = make_graphs_from(files, format=format)

    assert isinstance(g, Graph)
    if isinstance(files, str):
        files = [files]
    
    calls = []
    for file in files:
        calls.append(call(file, format=format))
    
    mock_parse.assert_has_calls(calls, any_order=True)


def test_make_graph_from_parsingerror() -> None:
    files = ["file1.owl", "file2.owl"]
    with pytest.raises(FileNotFoundError) as exc_info:
        g = make_graphs_from(files)
        assert isinstance(g, Graph)
    assert 'No such file or directory' in str(exc_info.value)


def test_make_graph_from_formaterror(tmp_path: Path) -> None:
    file = tmp_path / "file1.owl"
    file.write_text(f"""
        @prefix ex: <http://example.org/ns1#> .
        ex:s1 ex:p1 "o1" .
    """)
    with pytest.raises(PluginException) as exc_info:
        g = make_graphs_from([file], format="invalidformat")
        assert isinstance(g, Graph)
    assert "No plugin registered for (invalidformat, <class 'rdflib.parser.Parser'>)" in str(exc_info.value)


@pytest.mark.parametrize(
        "namespace1, namespace2",
        [
            pytest.param("http://example.org/ns1#", "http://example.org/ns1#", id="Same namespace"),
            pytest.param("http://example.org/ns1#", "http://example.com/ns2#", id="Different namespaces"),
        ]
)
def test_make_graph_from_graphcontent(tmp_path: Path, namespace1: str, namespace2: str) -> None:
    file1 = tmp_path / "file1.ttl" 
    file1.write_text(f"""
        @prefix ex: <{namespace1}> .
        ex:s1 ex:p1 "o1" .
    """)
    file2 = tmp_path / "file2.ttl"
    file2.write_text(f"""
        @prefix ex: <{namespace2}> .
        ex:s2 ex:p2 "o2" .
    """)

    g = make_graphs_from([file1, file2], format="ttl")

    ex = URIRef(namespace1)
    ex1 = URIRef(namespace2)
    assert (ex + "s1", ex + "p1", Literal("o1")) in g
    assert (ex1 + "s2", ex1 + "p2", Literal("o2")) in g
    assert g.namespace_manager.store.namespace("ex") == ex
    if namespace1 != namespace2:    # When namespaces are different, the second file's namespace is automatically given a new prefix
        assert g.namespace_manager.store.namespace("ex1") == ex1


# Unit tests merge_trig_graphs
# The deprecation warnings are due to rdflib's internal use of deprecated features, and are therefore silenced for the tests for this function.
@pytest.mark.filterwarnings("ignore:.*default_context.*:DeprecationWarning")
@pytest.mark.filterwarnings("ignore:.*ConjunctiveGraph.*:DeprecationWarning")
def test_merge_trig_graphs_emptylist() -> None:
    g = merge_trig_graphs([])
    assert isinstance(g, Graph)
    assert len(g) == 0

@pytest.mark.filterwarnings("ignore:.*default_context.*:DeprecationWarning")
@pytest.mark.filterwarnings("ignore:.*ConjunctiveGraph.*:DeprecationWarning")
def test_merge_trig_graphs_singlefile(tmp_path: Path) -> None:
    file = tmp_path / "data.trig"
    file.write_text("""
        @prefix ex: <http://example.org/> .
        ex:g1 {
            ex:s1 ex:p1 "o1" .
        }
        ex:g2 {
            ex:s2 ex:p2 "o2" .
        }           
    """)

    g = merge_trig_graphs([file])

    ex = URIRef("http://example.org/")
    assert (ex + "s1", ex + "p1", Literal("o1")) in g
    assert (ex + "s2", ex + "p2", Literal("o2")) in g
    assert g.namespace_manager.store.namespace("ex") == ex

@pytest.mark.filterwarnings("ignore:.*default_context.*:DeprecationWarning")
@pytest.mark.filterwarnings("ignore:.*ConjunctiveGraph.*:DeprecationWarning")
def test_merge_trig_graphs_parsingerror() -> None:
    files = ["file1.trig", "file2.trig"]
    with pytest.raises(FileNotFoundError) as exc_info:
        g = merge_trig_graphs(files)
        assert isinstance(g, Graph)
    assert 'No such file or directory' in str(exc_info.value)

@pytest.mark.parametrize(
        "namespace1, namespace2",
        [
            pytest.param("http://example.org/ns1#", "http://example.org/ns1#", id="Same namespace"),
            pytest.param("http://example.org/ns1#", "http://example.com/ns2#", id="Different namespaces"),
        ]
)
@pytest.mark.filterwarnings("ignore:.*default_context.*:DeprecationWarning")
@pytest.mark.filterwarnings("ignore:.*ConjunctiveGraph.*:DeprecationWarning")
def test_merge_trig_graphs_multiplefiles(tmp_path: Path, namespace1: str, namespace2: str) -> None:
    file1 = tmp_path / "data1.trig"
    file1.write_text(f"""
        @prefix ex: <{namespace1}> .
        ex:g {{
            ex:s1 ex:p1 "o1" .
        }}
    """)
    file2 = tmp_path / "data2.trig"
    file2.write_text(f"""
        @prefix ex: <{namespace2}> .
        ex:g {{
            ex:s2 ex:p2 "o2" .
        }}
    """)

    g = merge_trig_graphs([file1, file2])
    print(list(g))

    ex = URIRef(namespace1)
    ex1 = URIRef(namespace2)
    assert (ex + "s1", ex + "p1", Literal("o1")) in g
    assert (ex1 + "s2", ex1 + "p2", Literal("o2")) in g
    assert g.namespace_manager.store.namespace("ex") == ex
    if namespace1 != namespace2:    # When namespaces are different, the second file's namespace is automatically given a new prefix
        assert g.namespace_manager.store.namespace("ex1") == ex1

@pytest.mark.filterwarnings("ignore:.*default_context.*:DeprecationWarning")
@pytest.mark.filterwarnings("ignore:.*ConjunctiveGraph.*:DeprecationWarning")
def test_merge_trig_graphs_multipleprefixes(tmp_path: Path) -> None:
    file1 = tmp_path / "data1.trig"
    file1.write_text(f"""
        @prefix ex: <http://www.bar.com/> .
        ex:g {{
            ex:s1 ex:p1 "o1" .
        }}
    """)
    file2 = tmp_path / "data2.trig"
    file2.write_text(f"""
        @prefix foo: <http://www.bar.com/> .
        foo:g {{
            foo:s2 foo:p2 "o2" .
        }}
    """)

    g = merge_trig_graphs([file1, file2])
    print(list(g))

    ex = URIRef("http://www.bar.com/")
    print(list(g))
    assert (ex + "s1", ex + "p1", Literal("o1")) in g
    assert (ex + "s2", ex + "p2", Literal("o2")) in g
    assert g.namespace_manager.store.namespace("foo") == ex # Last prefix wins when multiple prefixes point to the same namespace

if __name__ == "__main__":
    pytest.main()