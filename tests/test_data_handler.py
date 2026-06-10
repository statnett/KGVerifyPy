import pytest
from unittest.mock import patch, MagicMock, call
from src.kgverifypy.data_handler import DataHandler

PATCH_LOCATION = "src.kgverifypy.data_handler"

# Unit tests for DataHandler._load_multiple_graph_files

@pytest.mark.parametrize(
        "files, format",
        [
            pytest.param(["data1.trig", "data2.trig"], "trig", id="trig"),
            pytest.param(["data1.trig", ""], "trig", id="trig, one with empty string"),
            pytest.param(["data1.xml", ""], "cimxml", id="xml, one with empty string"),
            pytest.param(["data1.xml", "data2.xml"], "cimxml", id="xml files"),
            pytest.param([], "trig", id="trig, empty list"),
            pytest.param([], "cimxml", id="cimxml, empty list"),
        ]
)
@patch(f"{PATCH_LOCATION}.make_graphs_from")
@patch(f"{PATCH_LOCATION}.merge_trig_graphs")
def test_load_multiple_graph_files(mock_merge: MagicMock, mock_make: MagicMock, files: list[str], format: str) -> None:
    mock_merge.return_value = "mocked_trig_graph"
    mock_make.return_value = "mocked_other_graph"
    handler = DataHandler()
    result = handler._load_multiple_graph_files(files, format)
    if not files:
        mock_merge.assert_not_called()
        mock_make.assert_not_called()
        assert result is None
    elif format == "trig":
        mock_merge.assert_called_once_with(files)
        mock_make.assert_not_called()
        assert result == "mocked_trig_graph"
    else:
        mock_make.assert_called_once_with(files, format=format)
        mock_merge.assert_not_called()
        assert result == "mocked_other_graph"


# Unit tests for DataHandler._load_file_with_loader
@pytest.mark.parametrize(
        "file, expected",
        [
            pytest.param("file.txt", "loaded file.txt with {'option': 'value'}", id="valid file"),
            pytest.param("", None, id="empty string, treated as no file"),
            pytest.param(" ", None, id="whitespace string, treated as no file"),
            pytest.param(None, None, id="none value")
        ]
)
def test_load_file_with_loader(file: str, expected: str) -> None:
    def mock_loader(file: str, **kwargs) -> str:
        return f"loaded {file} with {kwargs}"
    
    handler = DataHandler()
    result = handler._load_file_with_loader(file, mock_loader, option="value")
    assert result == expected

# Unit tests DataHandler.load_files
@patch(f"{PATCH_LOCATION}.make_graphs_from")
@patch(f"{PATCH_LOCATION}.load_json")
def test_load_files_nofiles(mock_load_json: MagicMock, mock_make: MagicMock) -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=[None, None])
    handler._load_file_with_loader = MagicMock(side_effect=[None, None])
    handler.load_files()

    # Calls are made even when no files are provided, but they return None
    graph_calls = [call([], "cimxml"),
                   call([], "xml")]
    handler._load_multiple_graph_files.assert_has_calls(graph_calls)
    loader_calls = [call("", mock_make, format="ttl"),
                    call("", mock_load_json)]
    handler._load_file_with_loader.assert_has_calls(loader_calls, any_order=True)
    assert handler.data_graph is None
    assert handler.rdfs_graph is None
    assert handler.shacl_graph is None
    assert handler.datatypes is None

def test_load_files_nofiles_nomock() -> None:
    handler = DataHandler()
    handler.load_files()

    # Calls are made even when no files are provided, but they return None
    assert handler.data_graph is None
    assert handler.rdfs_graph is None
    assert handler.shacl_graph is None
    assert handler.datatypes is None

def test_load_files_datafiles() -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=["mocked_data_graph", None])
    handler._load_file_with_loader = MagicMock(side_effect=[None, None])
    handler.data_files = ["data1.trig", "data2.trig"]
    handler.data_format = "trig"
    handler.load_files()

    handler._load_multiple_graph_files.assert_any_call(["data1.trig", "data2.trig"], "trig")
    assert handler._load_multiple_graph_files.call_count == 2  # for data_files and rdfs_files
    assert handler._load_file_with_loader.call_count == 2  # for shacl_file and datatype_file
    assert handler.data_graph == "mocked_data_graph"
    assert handler.rdfs_graph is None
    assert handler.shacl_graph is None
    assert handler.datatypes is None


def test_load_files_rdfsfiles() -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=[None, "mocked_rdfs_graph"])
    handler._load_file_with_loader = MagicMock(side_effect=[None, None])
    handler.rdfs_files = ["model1.xml", "model2.xml"]
    handler.load_files()

    handler._load_multiple_graph_files.assert_any_call(["model1.xml", "model2.xml"], "xml")
    assert handler._load_multiple_graph_files.call_count == 2  # for data_files and rdfs_files
    assert handler._load_file_with_loader.call_count == 2  # for shacl_file and datatype_file
    assert handler.data_graph is None
    assert handler.rdfs_graph == "mocked_rdfs_graph"
    assert handler.shacl_graph is None
    assert handler.datatypes is None

@patch(f"{PATCH_LOCATION}.make_graphs_from")
def test_load_files_shaclfile(mock_make: MagicMock) -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=[None, None])
    handler._load_file_with_loader = MagicMock(side_effect=["mocked_shacl_graph", None])
    handler.shacl_file = "shacl.ttl"
    handler.shacl_format = "ttl"
    handler.load_files()

    handler._load_file_with_loader.assert_any_call("shacl.ttl", mock_make, format="ttl")
    assert handler._load_multiple_graph_files.call_count == 2  # for data_files and rdfs_files
    assert handler._load_file_with_loader.call_count == 2  # for shacl_file and datatype_file
    assert handler.data_graph is None
    assert handler.rdfs_graph is None
    assert handler.shacl_graph == "mocked_shacl_graph"
    assert handler.datatypes is None

@patch(f"{PATCH_LOCATION}.load_json")
def test_load_files_datatypefile(mock_load_json: MagicMock) -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=[None, None])
    handler._load_file_with_loader = MagicMock(side_effect=[None, "mocked_datatypes"])
    handler.datatype_file = "datatypes.json"
    handler.load_files()
    
    handler._load_file_with_loader.assert_any_call("datatypes.json", mock_load_json)
    assert handler._load_multiple_graph_files.call_count == 2  # for data_files and rdfs_files
    assert handler._load_file_with_loader.call_count == 2  # for shacl_file and datatype_file
    assert handler.data_graph is None
    assert handler.rdfs_graph is None
    assert handler.shacl_graph is None
    assert handler.datatypes == "mocked_datatypes"

@patch(f"{PATCH_LOCATION}.make_graphs_from")
@patch(f"{PATCH_LOCATION}.load_json")
def test_load_files_allfiles(mock_load_json: MagicMock, mock_make: MagicMock) -> None:
    handler = DataHandler()
    handler._load_multiple_graph_files = MagicMock(side_effect=["mocked_data_graph", "mocked_rdfs_graph"])
    handler._load_file_with_loader = MagicMock(side_effect=["mocked_shacl_graph", "mocked_datatypes"])
    handler.data_files = ["data1.trig", "data2.trig"]
    handler.data_format = "trig"
    handler.rdfs_files = ["model1.xml", "model2.xml"]
    handler.shacl_file = "shacl.ttl"
    handler.shacl_format = "ttl"
    handler.datatype_file = "datatypes.json"
    handler.load_files()
    
    graph_calls = [call(["data1.trig", "data2.trig"], "trig"),
                   call(["model1.xml", "model2.xml"], "xml")]
    handler._load_multiple_graph_files.assert_has_calls(graph_calls, any_order=True)
    loader_calls = [call("shacl.ttl", mock_make, format="ttl"),
                    call("datatypes.json", mock_load_json)]
    handler._load_file_with_loader.assert_has_calls(loader_calls, any_order=True)
    assert handler.data_graph == "mocked_data_graph"
    assert handler.rdfs_graph == "mocked_rdfs_graph"
    assert handler.shacl_graph == "mocked_shacl_graph"
    assert handler.datatypes == "mocked_datatypes"


if __name__ == "__main__":
    pytest.main()