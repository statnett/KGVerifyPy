import pytest
from unittest.mock import Mock, MagicMock, patch
import tkinter as tk
from tkinter import ttk
import time

from src.kgverifypy.gui import (
    CollapsibleSection,
    LoadingDialog, 
    all_namespaces_match, 
    format_namespace_matrix
)

# Unit tests CollapsibleSection
def test_collapsiblesection_initialization() -> None:
    root = tk.Tk()
    frame = ttk.Frame(root)
    section = CollapsibleSection(frame, "Test Section")
    assert section.title == "Test Section"
    assert section.open is False
    assert section.header_btn.cget("text") == "[+] Test Section"


@pytest.mark.parametrize("open", [True, False])
def test_collapsiblesection_toggle(open: bool) -> None:
    root = tk.Tk()
    frame = ttk.Frame(root)
    section = CollapsibleSection(frame, "Test Section")
    if open:
        section.toggle()
    assert section.open == open
    expected_text = "[-] Test Section" if open else "[+] Test Section"
    assert section.header_btn.cget("text") == expected_text


# Unit tests LoadingDialog
@patch.object(LoadingDialog, "_update_timer")
def test_loadingdialog_initialization(mock_update_timer: Mock) -> None:
    root = tk.Tk()
    dialog = LoadingDialog(root)
    assert dialog.top.winfo_exists() == 1
    assert dialog.top.title() == "Loading files..."
    assert dialog.progress.winfo_exists() == 1
    assert isinstance(dialog.start_time, float)
    mock_update_timer.assert_called_once()


@pytest.mark.parametrize(
    "elapsed, expected_text",
    [
        pytest.param(5, "Elapsed: 5.0 s", id="< 60 seconds"),
        pytest.param(75, "Elapsed: 1 min 15 s", id="< 3600 seconds"),
        pytest.param(3665, "Elapsed: 1 h 1 min", id=">= 3600 seconds"),
    ],
)
@patch("time.time")
def test_loadingdialog_update_timer(mock_time: MagicMock, elapsed: int, expected_text: str) -> None:
    dialog = LoadingDialog.__new__(LoadingDialog)  # avoid __init__

    dialog.start_time = 1000
    dialog.time_label = MagicMock()
    dialog.top = MagicMock()
    dialog.top.after.return_value = "job_id"

    mock_time.return_value = 1000 + elapsed

    dialog._update_timer()

    dialog.time_label.config.assert_called_with(text=expected_text)

    dialog.top.after.assert_called_once_with(100, dialog._update_timer)

@pytest.mark.parametrize("with_job", [True, False])
def test_loadingdialog_close(with_job: bool) -> None:
    dialog = LoadingDialog.__new__(LoadingDialog)
    dialog.progress = MagicMock()
    dialog.top = MagicMock()

    if with_job:
        dialog._job = "job_id"

    dialog.close()

    dialog.progress.stop.assert_called_once()
    dialog.top.destroy.assert_called_once()

    if with_job:
        dialog.top.after_cancel.assert_called_once_with("job_id")
    else:
        dialog.top.after_cancel.assert_not_called()

# Unit tests all_namespaces_match
def test_all_namespaces_match() -> None:
    report = []
    assert all_namespaces_match(report) is True

    report = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": []}
    ]
    assert all_namespaces_match(report) is True

    report_with_missing = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": ["graph1"]}
    ]
    assert all_namespaces_match(report_with_missing) is False

# Unit tests format_namespace_matrix
def test_format_namespace_matrix_basic():
    report = [
        {
            "uri": "ns1",
            "missing": True,
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": True,
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     \n"
        "ns2 |     ✘      |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_notmissing():
    report = [
        {
            "uri": "ns1",
            "missing": ["g2"],
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": [],
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_emptyreport():
    assert format_namespace_matrix([], ["g1"]) == "Namespace |     G1    \n----------------------"

def test_format_namespace_matrix_nomissingrows():
    report = [{"uri": "ns", "missing": False, "presence": {}}]
    result = format_namespace_matrix(report, ["g1"])
    assert "ns" not in result


if __name__ == "__main__":
    pytest.main()