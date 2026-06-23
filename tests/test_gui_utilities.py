import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import tkinter as tk
from tkinter import ttk
from src.kgverifypy.gui_utilites import CollapsibleSection, ProgressTimerDialog

PATCH_LOCATION = "src.kgverifypy.gui_utilites"

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


# Unit tests ProgressTimerDialog
# ._format_elapsed
@pytest.mark.parametrize("elapsed, expected", [
    (30, "Elapsed: 30.0 s"),
    (90, "Elapsed: 1 min 30 s"),
    (3600, "Elapsed: 1 h 0 min"),
    (3665, "Elapsed: 1 h 1 min"),
])
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_format_elapsed(mock_toplevel: MagicMock, elapsed: int, expected: str) -> None:
    start_time = 0
    def fake_time():
        return start_time + elapsed

    root = Mock()
    dialog = ProgressTimerDialog(root, time_fn=fake_time)
    dialog.start_time = start_time
    assert dialog._format_elapsed() == expected
    mock_toplevel.assert_called_once_with(root)

# ._tick
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_tick_updateslabel(mock_toplevel: MagicMock) -> None:
    dlg = ProgressTimerDialog(parent=Mock())
    dlg._format_elapsed = MagicMock(return_value="Elapsed: 42 s")
    dlg.time_label = MagicMock()
    dlg.top = MagicMock()

    dlg._tick()

    dlg.time_label.config.assert_called_once_with(text="Elapsed: 42 s")
    dlg.top.after.assert_called_once_with(100, dlg._tick)
    mock_toplevel.assert_called_once()


# .start
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_start_callsprogressandtick(mock_toplevel: MagicMock) -> None:
    dlg = ProgressTimerDialog(parent=Mock())
    dlg.progress = MagicMock()
    dlg._tick = MagicMock()

    dlg.start()

    dlg.progress.start.assert_called_with(10)
    dlg._tick.assert_called()

# .stop
@pytest.mark.parametrize("job_exists", [True, False])
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_stop_cancelstimer(mock_toplevel: MagicMock, job_exists: bool) -> None:
    dlg = ProgressTimerDialog(parent=Mock())
    dlg.progress = MagicMock()
    dlg.top = MagicMock()
    dlg.time_label = MagicMock()
    dlg._format_elapsed = MagicMock(return_value="Elapsed: 5.0 s")

    dlg._job = "job_id" if job_exists else None
    dlg.start_time = time.time() - 5

    dlg.stop()

    dlg.progress.stop.assert_called_once()
    if job_exists:
        dlg.top.after_cancel.assert_called_once_with("job_id")
    else:
        dlg.top.after_cancel.assert_not_called()

    dlg.time_label.config.assert_called_once_with(text="Elapsed: 5.0 s")
    assert dlg._job is None
    mock_toplevel.assert_called_once()

# .close
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_close_destroyswindow(mock_toplevel: MagicMock) -> None:
    dlg = ProgressTimerDialog(parent=Mock())
    dlg.stop = MagicMock()
    dlg.top = MagicMock()

    dlg.close()

    dlg.stop.assert_called_once()
    dlg.top.destroy.assert_called_once()
    mock_toplevel.assert_called_once()

# .get_elapsed_text
@pytest.mark.parametrize("start_time_exists", [False, True])
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_get_elapsed_text(mock_toplevel: MagicMock, start_time_exists) -> None:
    dlg = ProgressTimerDialog(parent=Mock())
    dlg.start_time = time.time() - 5 if start_time_exists else 0

    text = dlg.get_elapsed_text()
    if not dlg.start_time:
        assert text == "Elapsed: 0.0 s"
    else:
        assert text == "Elapsed: 5.0 s"
    mock_toplevel.assert_called_once()

if __name__ == "__main__":
    pytest.main()