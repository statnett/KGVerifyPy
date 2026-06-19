import pytest
from unittest.mock import Mock, MagicMock, patch, call, ANY
import tkinter as tk
from pathlib import Path

from src.kgverifypy.gui import (
    FILE_CONFIG_PATH,
    CIMShaclGUI,
    _save_config_info,
    _load_dir_from_config,
    DATASET_SELECTORS
)

PATCH_LOCATION = "src.kgverifypy.gui"


# Unit tests CIMShaclGUI
# ._restore_format_from_file_config
@pytest.mark.parametrize(
        "file_config, data_fm, shacl_fm",
        [
            pytest.param({}, "cimxml", "ttl", id="empty config"),
            pytest.param(
                {"data": {"format": "xml"}, "shacl": {"format": "rdf"}},
                "xml",
                "rdf",
                id="custom formats"
            ),
            pytest.param(
                {"data": {}, "shacl": {}},
                "cimxml",
                "ttl",
                id="missing format keys"
            ),
            pytest.param(
                {"data": {"format": "json"}},
                "json",
                "ttl",
                id="missing shacl config"
            ),
            pytest.param(
                {"shacl": {"format": "rdf"}},
                "cimxml",
                "rdf",
                id="missing data config"
            ),
            pytest.param(None, "cimxml", "ttl", id="None config"),
            pytest.param({"data": None, "shacl": None}, "cimxml", "ttl", id="None data and shacl config"),
            pytest.param({"data": {"format": None}, "shacl": {"format": None}}, None, None, id="None format values"),
            pytest.param(
                {"data": {"format": "txt"}, "shacl": {"format": "json"}},
                "txt",
                "json",
                id="Unsupported formats"    # This method does not check if the formats are supported.
            ),

        ]
)
def test_restore_format_from_file_config(file_config: dict, data_fm: str, shacl_fm: str) -> None:
    gui = CIMShaclGUI().__new__(CIMShaclGUI)  # Avoid __init__ since it calls _restore_format_from_file_config
    gui.data_format = tk.StringVar(value="cimxml")
    gui.shacl_format = tk.StringVar(value="ttl")
    gui.datahandler = Mock()
    gui.datahandler.data_format = "cimxml"
    gui.datahandler.shacl_format = "ttl"
    gui.file_config = file_config

    gui._restore_format_from_file_config()
    print(gui.data_format.get(), gui.shacl_format.get())
    assert gui.data_format.get() == data_fm if data_fm is not None else "None"  # tk.StringVar will convert None to "None"
    assert gui.shacl_format.get() == shacl_fm if shacl_fm is not None else "None"
    assert gui.datahandler.data_format == data_fm
    assert gui.datahandler.shacl_format == shacl_fm

# ._build_gui
@patch(f"{PATCH_LOCATION}.ttk.Frame")
def test_build_gui_callssectionsinorder(frame_mock: MagicMock) -> None:
    gui = CIMShaclGUI()
    gui.root = Mock()
    mock_frame = frame_mock.return_value
    gui._file_selection_section = Mock(side_effect=[1, 2])  # First call for data file section, second for shacl file section
    gui._add_collapsible_section = Mock(side_effect=[3, 4])
    gui._validation_output_section = Mock(return_value=5)

    gui._build_gui()

    gui._file_selection_section.assert_has_calls([
        call(mock_frame, 0, "Data", gui.data_format, gui.data_var, [("CIMXML", "cimxml"), ("RDF/XML", "xml"), ("JSON-LD", "json-ld"), ("TRIG", "trig"), ("TTL", "ttl")], gui._select_data_files),
        call(mock_frame, 1, "SHACL", gui.shacl_format, gui.shacl_var, [("TTL", "ttl"), ("RDF/XML", "xml")], gui._select_shacl_file)
    ])
    gui._add_collapsible_section.assert_has_calls([
        call(mock_frame, 2, "Add RDFS files", gui._rdfs_section),
        call(mock_frame, 3, "Datatype enrichment options", gui._datatype_section)
    ])
    gui._validation_output_section.assert_called_once_with(mock_frame, 5)

@patch(f"{PATCH_LOCATION}.ttk.Button")
@patch(f"{PATCH_LOCATION}.ttk.Frame")
def test_build_gui_buttons(frame_mock: MagicMock, button_mock: MagicMock):
    gui = CIMShaclGUI()
    gui.root = Mock()

    gui._build_gui()

    calls = button_mock.call_args_list

    assert any(call.kwargs["text"] == "Check namespaces" for call in calls)
    assert any(call.kwargs["command"] == gui.show_namespace_report for call in calls)

    assert any(call.kwargs["text"] == "Run SHACL validation" for call in calls)
    assert any(call.kwargs["command"] == gui.start_validation for call in calls)

# ._file_selection_section
def test_file_selection_section() -> None:
    gui = CIMShaclGUI()
    gui._make_radio_group = Mock(return_value=2)
    gui._add_file_picker_row = Mock(return_value=3)
    parent = Mock()
    format_var = Mock()
    file_var = Mock()
    select_command = Mock()

    with patch(f"{PATCH_LOCATION}.ttk.Label") as label_mock:
        result = gui._file_selection_section(parent, 0, "Title", format_var, file_var, [("CIMXML", "cimxml")], select_command)

        label_mock.assert_called_once_with(parent, text="Title files:")
        label_mock.return_value.grid.assert_called_once()

    gui._make_radio_group.assert_called_once_with(parent, 1, format_var, [("CIMXML", "cimxml")])
    gui._add_file_picker_row.assert_called_once_with(parent, 2, file_var, select_command)
    assert result == 4


# ._rdfs_section
def test_rdfs_section() -> None:
    gui = CIMShaclGUI()
    gui._add_file_picker_row = Mock(return_value=1)
    parent = Mock()

    result = gui._rdfs_section(parent, 0)

    gui._add_file_picker_row.assert_called_once_with(parent, 0, gui.rdfs_var, gui._select_rdfs_files)
    assert result == 2

# ._datatype_section
def test_datatype_section() -> None:
    gui = CIMShaclGUI()
    gui._add_file_picker_row = Mock(return_value=2)
    parent = Mock()

    with patch(f"{PATCH_LOCATION}.ttk.Label") as label_mock, \
         patch(f"{PATCH_LOCATION}.ttk.Checkbutton") as mock_check:
        result = gui._datatype_section(parent, 0)
        label_mock.assert_called_once_with(parent, text="Custom context file:")
        label_mock.return_value.grid.assert_called_once()
        mock_check.assert_called_once_with(parent, text="Add datatypes", variable=gui.add_datatypes_var)
        mock_check.return_value.grid.assert_called_once()

    gui._add_file_picker_row.assert_called_once_with(parent, 1, gui.datatype_var, gui._select_datatype_file)
    assert result == 3


# ._validation_output_section
def test_validation_output_section() -> None:
    gui = CIMShaclGUI()
    gui._make_radio_group = Mock(return_value=1)
    parent = Mock()

    with patch(f"{PATCH_LOCATION}.ttk.Label") as label_mock, \
            patch(f"{PATCH_LOCATION}.ttk.Entry") as entry_mock, \
                 patch(f"{PATCH_LOCATION}.ttk.Checkbutton") as button_mock:
                    result = gui._validation_output_section(parent, 0)
        
                    label_mock.assert_called_once_with(parent, text="Validation output file path:")
                    label_mock.return_value.grid.assert_called_once()
                    entry_mock.assert_called_once_with(parent, textvariable=gui.validation_output_path)
                    entry_mock.return_value.grid.assert_called_once()
                    button_mock.assert_called_once_with(parent, text="CSV report", variable=gui.csv_report_var)
                    button_mock.return_value.grid.assert_called_once()

    gui._make_radio_group.assert_called_once_with(parent, 2, gui.validation_output_format, [("JSON-LD", "json-ld"), ("TTL", "ttl"), ("RDF/XML", "xml")])
    assert result == 6

# ._make_radio_group
def test_make_radio_group() -> None:
    gui = CIMShaclGUI()
    parent = Mock()
    var = Mock()
    options = [("Option 1", "opt1"), ("Option 2", "opt2")]

    with patch(f"{PATCH_LOCATION}.ttk.Frame") as mock_frame, \
         patch(f"{PATCH_LOCATION}.ttk.Radiobutton") as radio_mock:
            result = gui._make_radio_group(parent, 0, var, options)

            assert radio_mock.call_count == len(options)
            for text, value in options:
                radio_mock.assert_any_call(mock_frame.return_value, text=text, variable=var, value=value)
                radio_mock.return_value.pack.assert_any_call(side="left", padx=(0, 12))

    assert result == 1

    mock_frame.assert_called_once_with(parent)
    mock_frame.return_value.grid.assert_called_once()

# ._add_collapsible_section
def test_add_collapsible_section() -> None:
    gui = CIMShaclGUI()
    parent = Mock()
    builder_fn = Mock(return_value=1)

    with patch(f"{PATCH_LOCATION}.CollapsibleSection") as section_mock:
        result = gui._add_collapsible_section(parent, 0, "Section Title", builder_fn)

        section_mock.assert_called_once_with(parent, title="Section Title")
        section_mock.return_value.grid.assert_called_once_with(row=0, column=0, sticky="ew", pady=(10, 10))
        builder_fn.assert_called_once_with(section_mock.return_value.content, 0)
        assert result == 1

# ._add_file_picker_row
def test_add_file_picker_row() -> None:
    gui = CIMShaclGUI()
    parent = Mock()
    value_var = Mock()
    command = Mock()

    with patch(f"{PATCH_LOCATION}.ttk.Entry") as entry_mock, \
         patch(f"{PATCH_LOCATION}.ttk.Button") as button_mock:
            result = gui._add_file_picker_row(parent, 0, value_var, command)

            entry_mock.assert_called_once_with(parent, textvariable=value_var, state="readonly")
            entry_mock.return_value.grid.assert_called_once()
            button_mock.assert_called_once_with(parent, text="Browse", command=command)
            button_mock.return_value.grid.assert_called_once()

    assert result == 1

# .safe_execute
@pytest.mark.parametrize("exception", [None, Exception("Test error")])
@patch(f"{PATCH_LOCATION}.messagebox.showerror")
def test_safe_execute_success(mock_showerror: MagicMock, exception: None | Exception, caplog: pytest.LogCaptureFixture) -> None:
    gui = CIMShaclGUI()
    func = Mock(side_effect=exception)
    gui.root = Mock()
    gui.root.after = Mock(side_effect=lambda delay, func: func())

    gui._safe_execute(func, title="Error")

    func.assert_called_once()
    if exception is None:
        mock_showerror.assert_not_called()
        assert "Unhandled exception" not in caplog.text
    else:
        assert "Unhandled exception" in caplog.text
        mock_showerror.assert_called_once_with("Error", str(exception))


# ._select_files_by
@pytest.mark.parametrize("dataset_name", ["data", "shacl", "rdfs", "datatypes", "unknown"])
@patch(f"{PATCH_LOCATION}.filedialog.askopenfilename")
@patch(f"{PATCH_LOCATION}.filedialog.askopenfilenames")
@patch(f"{PATCH_LOCATION}._load_dir_from_config", return_value="last_dir")
def test_select_files_by(mock_load_dir: MagicMock, mock_askopenfilenames: MagicMock, mock_askopenfilename: MagicMock, dataset_name: str) -> None:
    gui = CIMShaclGUI()
    gui.file_config = Mock(return_value="last_dir")
    gui._run_threaded = Mock()
    gui._safe_execute = Mock()
    mock_files = "files"
    mock_askopenfilename.return_value = mock_files
    mock_askopenfilenames.return_value = mock_files

    gui._select_files_by(dataset_name)

    if dataset_name not in DATASET_SELECTORS:
        mock_load_dir.assert_not_called()
        mock_askopenfilename.assert_not_called()
        mock_askopenfilenames.assert_not_called()
        gui._run_threaded.assert_not_called()
        gui._safe_execute.assert_not_called()
        return
    
    dataset = DATASET_SELECTORS[dataset_name]
    mock_load_dir.assert_called_once_with(gui.file_config, dataset_name)
    if dataset_name in ["rdfs", "data"]:
        mock_askopenfilenames.assert_called_once_with(initialdir="last_dir", title=dataset.title)
        mock_askopenfilename.assert_not_called()
    elif dataset_name in ["shacl", "datatypes"]:
        mock_askopenfilename.assert_called_once_with(initialdir="last_dir", title=dataset.title)
        mock_askopenfilenames.assert_not_called()
    
    if dataset_name == "data":
        gui._run_threaded.assert_called_once_with("data", mock_files, dataset)
        gui._safe_execute.assert_not_called()
        args, _ = gui._run_threaded.call_args
        assert args[2] is dataset
    elif dataset_name in ["shacl", "datatypes", "rdfs"]:
        gui._safe_execute.assert_called_once_with(ANY, title=f"Error loading {dataset_name} files")
        gui._run_threaded.assert_not_called()
        

@patch(f"{PATCH_LOCATION}.filedialog.askopenfilenames", return_value=())
@patch(f"{PATCH_LOCATION}._load_dir_from_config")
def test_select_files_by_nofilesretrieved(mock_load_dir: MagicMock, mock_askopenfilenames: MagicMock) -> None:
    gui = CIMShaclGUI()
    gui.file_config = Mock(return_value="last_dir")
    gui._run_threaded = Mock()
    gui._safe_execute = Mock()

    gui._select_files_by("data")
    mock_load_dir.assert_called_once_with(gui.file_config, "data")
    mock_askopenfilenames.assert_called_once()
    gui._run_threaded.assert_not_called()
    gui._safe_execute.assert_not_called()


@patch(f"{PATCH_LOCATION}.filedialog.askopenfilenames", return_value=("a", "b"))
@patch(f"{PATCH_LOCATION}._load_dir_from_config")
def test_select_files_by_filesretrievedcorrectly(mock_load_dir: MagicMock, mock_askopenfilenames: MagicMock) -> None:
    gui = CIMShaclGUI()
    gui.file_config = Mock(return_value="last_dir")
    gui._run_threaded = Mock()
    gui._safe_execute = Mock()

    gui._select_files_by("data")
    mock_load_dir.assert_called_once_with(gui.file_config, "data")
    mock_askopenfilenames.assert_called_once()
    args, _ = gui._run_threaded.call_args
    assert isinstance(args[1], list)
    assert args[1] == ["a", "b"]
    gui._run_threaded.assert_called_once()
    gui._safe_execute.assert_not_called()


# ._execute_selection
@patch(f"{PATCH_LOCATION}._save_config_info")
def test_execute_selection_calls_load_method(mock_save_config: MagicMock) -> None:
    dataset_config = DATASET_SELECTORS["data"]
    gui = CIMShaclGUI()
    gui.datahandler = Mock()
    setattr(gui.datahandler, dataset_config.load_method, Mock())
    setattr(gui.datahandler, dataset_config.set_method, Mock())

    # mock attributes used via getattr
    var_mock = Mock()
    setattr(gui, dataset_config.var_attr, var_mock)

    if dataset_config.format_attr:
        format_var_mock = Mock()
        setattr(gui, dataset_config.format_attr, format_var_mock)
        format_var_mock.get.return_value = "cimxml"

    gui.file_config = {}

    files = "file1.txt"

    gui._execute_selection(files, dataset_config)

    # Assert
    setter = getattr(gui.datahandler, dataset_config.set_method)
    setter.assert_called_once_with(files, "cimxml")
    getattr(gui.datahandler, dataset_config.load_method).assert_called_once()
    var_mock.set.assert_called_once_with(files)
    mock_save_config.assert_called_once_with(gui.file_config, "file1.txt", dataset_config.config_key, "cimxml")


@pytest.mark.parametrize(
    "key, files, expected_var_value",
    [
        pytest.param("data", "file1.txt", "file1.txt", id="data single file with format",),
        pytest.param("shacl", "file1.txt", "file1.txt", id="shacl single file with format",),
        pytest.param("rdfs", ["file1.txt", "file2.txt"], "2 files selected", id="rdfs multiple files no format",),
        pytest.param("datatypes", "file1.txt", "file1.txt", id="datatypes single file no format",),
        # Additional edge cases
        pytest.param("data", ["file1.txt", "file2.txt"], "2 files selected", id="data multiple files with format",),
        pytest.param("rdfs", ["file1.txt"], "file1.txt", id="one item in list",),
    ],
)
@patch(f"{PATCH_LOCATION}._save_config_info")
def test_execute_selection(mock_save_config: MagicMock, key: str, files: list[str]|str, expected_var_value: str) -> None:
    dataset_config = DATASET_SELECTORS[key]

    gui = CIMShaclGUI()
    gui.datahandler = Mock()
    setter_mock = Mock()
    loader_mock = Mock()
    setattr(gui.datahandler, dataset_config.set_method, setter_mock)
    setattr(gui.datahandler, dataset_config.load_method, loader_mock)
    var_mock = Mock()
    setattr(gui, dataset_config.var_attr, var_mock)

    fmt_value = None
    if dataset_config.format_attr:
        format_var_mock = Mock()
        fmt_value = "cimxml"
        format_var_mock.get.return_value = fmt_value
        setattr(gui, dataset_config.format_attr, format_var_mock)

    gui.file_config = {}

    gui._execute_selection(files, dataset_config)

    if fmt_value is not None:
        setter_mock.assert_called_once_with(files, fmt_value)
    else:
        setter_mock.assert_called_once_with(files)

    loader_mock.assert_called_once()
    var_mock.set.assert_called_once_with(expected_var_value)
    first = files[0] if isinstance(files, list) else files
    mock_save_config.assert_called_once_with(gui.file_config, first, dataset_config.config_key, fmt_value)

@patch(f"{PATCH_LOCATION}._save_config_info")
def test_execute_selection_nofiles(mock_save_config: MagicMock) -> None:
    dataset_config = DATASET_SELECTORS["data"]
    gui = CIMShaclGUI()
    gui.datahandler = Mock()
    setattr(gui.datahandler, dataset_config.load_method, Mock())
    setattr(gui.datahandler, dataset_config.set_method, Mock())
    var_mock = Mock()
    setattr(gui, dataset_config.var_attr, var_mock)

    if dataset_config.format_attr:
        format_var_mock = Mock()
        setattr(gui, dataset_config.format_attr, format_var_mock)

    gui.file_config = {}

    files = []

    with pytest.raises(IndexError, match="list index out of range"):
        gui._execute_selection(files, dataset_config)

    getattr(gui.datahandler, dataset_config.load_method).assert_not_called()
    var_mock.set.assert_not_called()
    mock_save_config.assert_not_called()

# ._run_threaded
@patch(f"{PATCH_LOCATION}.ProgressTimerDialog")
@patch(f"{PATCH_LOCATION}.threading.Thread")
def test_run_threaded(mock_thread: MagicMock, mock_progress: MagicMock) -> None:
    gui = CIMShaclGUI()
    gui.root = Mock()
    gui._safe_execute = Mock()
    gui._execute_selection = Mock()
    dataset_config = DATASET_SELECTORS["data"]
    files = "file1.txt"

    gui._run_threaded("data", files, dataset_config)

    mock_thread.assert_called_once_with(target=ANY, daemon=True)
    mock_thread.return_value.start.assert_called_once()
    task_func = mock_thread.call_args.kwargs["target"]
    task_func()
    gui._safe_execute.assert_called_once_with(ANY, title=f"Error loading data files")
    args, kwargs = gui._safe_execute.call_args
    assert "Error loading data files" == kwargs["title"]
    callable_passed = args[0]
    callable_passed()
    gui._execute_selection.assert_called_once_with(files, dataset_config)

    mock_progress.assert_called_once_with(gui.root, title=dataset_config.loading_title, message=dataset_config.loading_message)
    gui.root.after.assert_called_once_with(100, ANY)

# ._check_thread
@pytest.mark.parametrize("thread_alive", [True, False])
def test_check_thread(thread_alive: bool) -> None:
    gui = CIMShaclGUI()
    gui.loading_window = Mock()
    gui.root = Mock()
    thread_mock = Mock()
    thread_mock.is_alive.return_value = thread_alive
    
    gui._check_thread(thread_mock)

    if thread_alive:
        gui.root.after.assert_called_once_with(100, ANY)
        gui.loading_window.stop.assert_not_called()
    else:
        gui.loading_window.close.assert_called_once()
        gui.root.after.assert_not_called()


# ._prepare_data_graph
@pytest.mark.parametrize(
        "graph, add_datatypes, datatype_file",
        [
            pytest.param(None, False, None, id="No data"),
            pytest.param("graph", False, None, id="Data with no datatypes"),
            pytest.param(None, True, "datatypes.json", id="No data with datatypes, returns early"), # Nothing is done with the datatypes.
            pytest.param("graph", True, None, id="Data with datatypes but no custom context file"),
            pytest.param("graph", True, "datatypes.json", id="Data with datatypes and custom file"),
            pytest.param("graph", False, "datatypes.json", id="Data without datatypes but has custom file"),    # Custom datatypes is sent but never used when add_datatypes is False.
        ]
)
def test_prepare_data_graph(graph, add_datatypes, datatype_file) -> None:
    gui = CIMShaclGUI()
    gui.datahandler = Mock()
    gui.add_datatypes_var = Mock()
    gui.add_datatypes_var.get.return_value = add_datatypes
    gui.validation_service = Mock()
    gui.datahandler.data_graph = graph
    gui.datahandler.rdfs_graph = "rdfs_graph"
    gui.datahandler.datatype_file = datatype_file
    context_data = "datatypes" if datatype_file else None
    gui.datahandler.datatypes = context_data

    gui._prepare_data_graph()

    if graph is None:
        gui.validation_service.prepare_data_for_validation.assert_not_called()
        return
    
    if add_datatypes:
        if datatype_file is None:
            gui.validation_service.prepare_data_for_validation.assert_called_once_with(graph, "rdfs_graph", add_datatypes=True, context_data=None)
        else:
            gui.validation_service.prepare_data_for_validation.assert_called_once_with(graph, "rdfs_graph", add_datatypes=True, context_data="datatypes")
    else:
        gui.validation_service.prepare_data_for_validation.assert_called_once_with(graph, "rdfs_graph", add_datatypes=False, context_data=context_data)

# Unit tests _save_config_info
@pytest.mark.parametrize(
          "format", [None, "cimxml", "json"]
)
@patch(f"{PATCH_LOCATION}.save_json")
def test_save_config_info(mock_save_json: MagicMock, format: str) -> None:
    file_config = {
        "data": {"last_directory": "/old/data/dir", "format": "cimxml"},
        "shacl": {"last_directory": "/old/shacl/dir", "format": "ttl"}
    }
    test_filestr = "somewhere/testfile.ttl"
    original_format = file_config["shacl"]["format"]
    
    _save_config_info(file_config, test_filestr, "shacl", format)

    assert file_config["data"]["last_directory"] == "/old/data/dir"  # Data config should not be modified
    assert file_config["data"]["format"] == "cimxml"  # Data format should not be modified
    assert file_config["shacl"]["last_directory"] == "somewhere"
    assert file_config["shacl"]["format"] == (format if format else original_format)
    mock_save_json.assert_called_once_with(file_config, FILE_CONFIG_PATH)

@patch(f"{PATCH_LOCATION}.save_json")
def test_save_config_info_nodirpath(mock_save_json: MagicMock) -> None:
    file_config = {
        "data": {"last_directory": "/old/data/dir", "format": "cimxml"},
        "shacl": {"last_directory": "/old/shacl/dir", "format": "ttl"}
    }
    test_filestr = "testfile.ttl"
    original_format = file_config["shacl"]["format"]
    
    _save_config_info(file_config, test_filestr, "shacl")

    assert file_config["shacl"]["last_directory"] == "."
    assert file_config["shacl"]["format"] == original_format
    mock_save_json.assert_called_once_with(file_config, FILE_CONFIG_PATH)

@pytest.mark.parametrize(
        "file_config",
        [
            pytest.param({}, id="empty config"),
            pytest.param({"shacl": {}}, id="missing shacl config"),
            pytest.param({"shacl": {"format": "xml"}}, id="missing last_directory key"),
            pytest.param({"shacl": {"last_directory": "/old/dir"}}, id="missing format key"),
        ]
)
@patch(f"{PATCH_LOCATION}.save_json")
def test_save_config_info_emptyconfig(mock_save_json: MagicMock, file_config: dict[str, dict[str, str]]) -> None:
    test_filestr = "somewhere/testfile.ttl"
    
    _save_config_info(file_config, test_filestr, "shacl", "ttl")

    assert file_config["shacl"]["last_directory"] == "somewhere"
    assert file_config["shacl"]["format"] == "ttl"
    mock_save_json.assert_called_once_with(file_config, FILE_CONFIG_PATH)

@patch(f"{PATCH_LOCATION}.save_json")
def test_save_config_info_noneconfig(mock_save_json: MagicMock) -> None:
    test_filestr = "somewhere/testfile.ttl"
    
    # Pylance silenced to test wrong input
    _save_config_info(None, test_filestr, "shacl", "ttl") # type: ignore

    mock_save_json.assert_called_once_with({"shacl": {"last_directory": "somewhere", "format": "ttl"}}, FILE_CONFIG_PATH)

# Unit tests _load_dir_from_config
@pytest.mark.parametrize(
    "file_config, dataset, expected",
    [
        pytest.param({"data": {"last_directory": "/data/dir"}}, "data", "/data/dir", id="data dir"),
        pytest.param({"shacl": {"last_directory": "/shacl/dir"}}, "shacl", "/shacl/dir", id="shacl dir"),
        pytest.param({}, "rdfs", str(Path.home()), id="empty config"),
        pytest.param({"rdfs": {}}, "rdfs", str(Path.home()), id="missing rdfs config"),
        pytest.param({"rdfs": {"format": "rdf"}}, "rdfs", str(Path.home()), id="missing last_directory key"),
        pytest.param({"rdfs": {"last_directory": ""}}, "rdfs", "", id="empty last_directory"),
        pytest.param(None, "rdfs", str(Path.home()), id="none config"),
        pytest.param({"rdfs": {"last_directory": 123}}, "rdfs", 123, id="invalid last_directory")
    ],
)
def test_load_dir_from_config(file_config: dict[str, dict[str, str]] | None, dataset: str, expected: str | int) -> None:
    # Pylance silenced to test wrong input
    assert _load_dir_from_config(file_config, dataset) == expected  # type: ignore

if __name__ == "__main__":
    pytest.main()