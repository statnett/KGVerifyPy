import pytest
from unittest.mock import patch, MagicMock
from src.kgverifypy.file_handling import make_graph_from
from rdflib import Graph, URIRef

# Unit tests make_graph_from
@patch.object(Graph, "parse")
def test_make_graph_from(mock_parse: MagicMock) -> None:
    files = ["file1.owl", "file2.owl"]
    g = make_graph_from(files)
    assert isinstance(g, Graph)
    assert mock_parse.call_count == len(files)
    mock_parse.assert_any_call("file1.owl", format="xml")
    mock_parse.assert_any_call("file2.owl", format="xml")


@patch.object(Graph, "parse")
def test_make_graph_from_error(mock_parse: MagicMock) -> None:
    mock_parse.side_effect = [Graph(), Exception("File not found")]
    files = ["file1.owl", "file2.owl"]
    with pytest.raises(Exception, match="File not found"):
        g = make_graph_from(files)
        assert isinstance(g, Graph)

    assert mock_parse.call_count == len(files)


@patch.object(Graph, "parse")
def test_make_graph_from_singlefile(mock_parse: MagicMock) -> None:
    files = ["file1.ttl"]
    g = make_graph_from(files, format="ttl")
    assert isinstance(g, Graph)
    assert mock_parse.call_count == len(files)
    mock_parse.assert_any_call("file1.ttl", format="ttl")


if __name__ == "__main__":
    pytest.main()