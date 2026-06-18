import pytest
from unittest.mock import Mock, MagicMock, patch, call
import tkinter as tk

from src.kgverifypy.gui import (
    CIMShaclGUI,
    all_namespaces_match, 
    format_namespace_matrix
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
        call(mock_frame, 0, "Data", gui.data_format, gui.data_var, [("CIMXML", "cimxml"), ("RDF/XML", "xml"), ("JSON-LD", "json-ld"), ("TRIG", "trig"), ("TTL", "ttl")], gui.select_data_files),
        call(mock_frame, 1, "SHACL", gui.shacl_format, gui.shacl_var, [("TTL", "ttl"), ("RDF/XML", "xml")], gui.select_shacl_file)
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

    gui._add_file_picker_row.assert_called_once_with(parent, 0, gui.rdfs_var, gui.select_rdfs_files)
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

    gui._add_file_picker_row.assert_called_once_with(parent, 1, gui.datatype_var, gui.select_datatype_file)
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



if __name__ == "__main__":
    pytest.main()