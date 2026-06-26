import pytest
from unittest.mock import patch, MagicMock
from rdflib import Graph
from rdflib.namespace import NamespaceManager
from src.kgverifypy.data_handler import DataHandler, _get_ns_map

PATCH_LOCATION = "src.kgverifypy.data_handler"


# Unit tests for DataHandler
# ._load_data_files
@patch(f"{PATCH_LOCATION}._get_ns_map")
@patch(f"{PATCH_LOCATION}.make_graphs_from")
@patch(f"{PATCH_LOCATION}.merge_trig_graphs")
def test_load_data_files_nofiles(mock_merge: MagicMock, mock_make: MagicMock, mock_ns_map: MagicMock) -> None:
    handler = DataHandler()
    handler.data_files = []
    handler.data_format = "trig"
    handler.load_data_files()
    mock_merge.assert_not_called()
    mock_make.assert_not_called()
    assert handler.data_graph is None
    mock_ns_map.assert_not_called()
    assert handler.namespace_handler.data_ns_map is None


@pytest.mark.parametrize("format", ["trig", "cimxml"])
@patch(f"{PATCH_LOCATION}._get_ns_map")
@patch(f"{PATCH_LOCATION}.make_graphs_from")
@patch(f"{PATCH_LOCATION}.merge_trig_graphs")
def test_load_data_files_formats(mock_merge: MagicMock, mock_make: MagicMock, mock_ns_map: MagicMock, format: str) -> None:
    mock_merge.return_value = "mocked_trig_graph"
    mock_make.return_value = "mocked_other_graph"
    mock_ns_map.return_value = {"http://example.org/ns#": "ex"}
    handler = DataHandler()
    handler.data_files = ["file1", "file2"]
    handler.data_format = format

    handler.load_data_files()

    if format == "trig":
        mock_merge.assert_called_once_with(["file1", "file2"])
        mock_make.assert_not_called()
        assert handler.data_graph == "mocked_trig_graph"
    else:
        mock_merge.assert_not_called()
        mock_make.assert_called_once_with(["file1", "file2"], format=format)
        assert handler.data_graph == "mocked_other_graph"

    mock_ns_map.assert_called_once_with(handler.data_graph)
    assert handler.namespace_handler.data_ns_map == {"http://example.org/ns#": "ex"}

# .load_shacl_file
@pytest.mark.parametrize("shacl_file", ["shacl.ttl", ""])
@patch(f"{PATCH_LOCATION}._get_ns_map")
@patch(f"{PATCH_LOCATION}.make_graphs_from")
def test_load_shacl_file(mock_make: MagicMock, mock_ns_map: MagicMock, shacl_file: str) -> None:
    handler = DataHandler()
    handler.shacl_file = shacl_file
    handler.shacl_format = "ttl"
    mock_make.return_value = "mocked_shacl_graph"
    mock_ns_map.return_value = {"http://example.org/ns#": "ex"}

    handler.load_shacl_file()

    if shacl_file:
        mock_make.assert_called_once_with(shacl_file, format="ttl")
        assert handler.shacl_graph == "mocked_shacl_graph"
        mock_ns_map.assert_called_once_with(handler.shacl_graph)
        assert handler.namespace_handler.shacl_ns_map == {"http://example.org/ns#": "ex"}
    else:
        mock_make.assert_not_called()
        assert handler.shacl_graph is None
        mock_ns_map.assert_not_called()
        assert handler.namespace_handler.shacl_ns_map is None


# .load_rdfs_files
@pytest.mark.parametrize("rdfs_files", [["rdfs1.xml", "rdfs2.xml"], []])
@patch(f"{PATCH_LOCATION}._get_ns_map")
@patch(f"{PATCH_LOCATION}.make_graphs_from")
def test_load_rdfs_files(mock_make: MagicMock, mock_ns_map: MagicMock, rdfs_files: list[str]) -> None:
    handler = DataHandler()
    handler.rdfs_files = rdfs_files
    mock_make.return_value = "mocked_rdfs_graph"
    mock_ns_map.return_value = {"http://example.org/ns#": "ex"}

    handler.load_rdfs_files()

    if rdfs_files:
        mock_make.assert_called_once_with(rdfs_files, format="xml")
        assert handler.rdfs_graph == "mocked_rdfs_graph"
        mock_ns_map.assert_called_once_with(handler.rdfs_graph)
        assert handler.namespace_handler.rdfs_ns_map == {"http://example.org/ns#": "ex"}
    else:
        mock_make.assert_not_called()
        assert handler.rdfs_graph is None
        mock_ns_map.assert_not_called()
        assert handler.namespace_handler.rdfs_ns_map is None


# .load_datatypes
@pytest.mark.parametrize("datatype_file", ["datatypes.json", ""])
@patch(f"{PATCH_LOCATION}.load_json")
def test_load_datatypes(mock_load_json: MagicMock, datatype_file: str) -> None:
    handler = DataHandler()
    handler.datatype_file = datatype_file
    mock_load_json.return_value = "mocked_datatypes"

    handler.load_datatypes()

    if datatype_file:
        mock_load_json.assert_called_once_with(datatype_file)
        assert handler.datatypes == "mocked_datatypes"
    else:
        mock_load_json.assert_not_called()
        assert handler.datatypes is None

# Unit test _get_ns_map
def test_get_ns_map_empty() -> None:
    g = Graph()
    namespaces = NamespaceManager(g, bind_namespaces="none")
    g.namespace_manager = namespaces    # To remove all default namespaces
    result = _get_ns_map(g)

    assert isinstance(result, dict)
    assert len(result) == 0

def test_get_ns_map_multiple() -> None:
    g = Graph()
    g.bind("ex", "http://example.org/")
    g.bind("foaf", "http://xmlns.com/foaf/0.1/")

    result = _get_ns_map(g)

    assert result["http://example.org/"] == "ex"
    assert result["http://xmlns.com/foaf/0.1/"] == "foaf"

if __name__ == "__main__":
    pytest.main()