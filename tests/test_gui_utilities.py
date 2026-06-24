import pytest
from unittest.mock import Mock, patch, MagicMock, ANY, call
import time
import tkinter as tk
from tkinter import ttk
from src.kgverifypy.gui_utilites import CollapsibleSection, ProgressTimerDialog, ToolTip

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


# Unit tests ToolTip
# ._show_now
@patch(f"{PATCH_LOCATION}.tk.Label")
@patch(f"{PATCH_LOCATION}.tk.Toplevel")
def test_show_now(mock_toplevel: MagicMock, mock_label: MagicMock) -> None:
    tt = ToolTip()
    widget = MagicMock()
    tt._show_now(widget, 10, 20, "Test Tooltip")

    mock_toplevel.assert_called_once_with(widget)
    mock_label.assert_called_once_with(
        tt.tooltip,
        text="Test Tooltip",
        background="lightyellow",
        relief="solid",
        borderwidth=1,
        padx=3,
        pady=1
    )
    mock_label.return_value.pack.assert_called_once()

# .hide
@pytest.mark.parametrize(
        "after_id_exists, tooltip_exists, exception_raised",
        [
            pytest.param(True, True, False, id="after_id and tooltip exist, no exception"),
            pytest.param(True, False, False, id="after_id exists, tooltip does not exist, no exception"),
            pytest.param(False, True, False, id="after_id does not exist, tooltip exists, no exception"),
            pytest.param(False, False, False, id="after_id and tooltip do not exist, no exception"),
            pytest.param(True, True, True, id="Exception raised, has no effect on the outcome."),
        ]
)
def test_hide(after_id_exists, tooltip_exists, exception_raised) -> None:
    tt = ToolTip()
    tt.tooltip_widget = MagicMock()
    tt.after_id = "some_id" if after_id_exists else None
    tt.tooltip = MagicMock() if tooltip_exists else None
    tt.tooltip_widget.after_cancel = MagicMock(side_effect=ValueError("Test Exception") if exception_raised else None)

    tt.hide()

    if after_id_exists:
        tt.tooltip_widget.after_cancel.assert_called_once_with("some_id")
    else:
        tt.tooltip_widget.after_cancel.assert_not_called()

    assert tt.after_id is None
    assert tt.tooltip is None


# Show
def test_show() -> None:
    tt = ToolTip()
    widget = MagicMock()
    widget.after = MagicMock(return_value="after_id")
    tt._show_now = MagicMock()
    tt.hide = MagicMock()

    tt.show(widget, 10, 20, "Test Tooltip")

    tt.hide.assert_called_once()  # Should hide any existing tooltip
    assert tt.after_id == "after_id"
    assert tt.tooltip_widget == widget
    widget.after.assert_called_once_with(tt.delay, ANY)
    tt._show_now.assert_not_called()  # Should not be called immediately

    # After the delay, the _show_now method should be called with the correct parameters
    delayed = widget.after.call_args[0][1]
    delayed()
    tt._show_now.assert_called_once_with(widget, 10, 20, "Test Tooltip")

# .attach
def test_attach() -> None:
    tt = ToolTip()
    widget = MagicMock()
    widget.bind = MagicMock()
    tt.show = MagicMock()
    tt.hide = MagicMock()

    tt.attach(widget, "Test Tooltip")

    widget.bind.assert_any_call("<Enter>", ANY)
    widget.bind.assert_any_call("<Leave>", ANY)

    enter_event = MagicMock()
    enter_event.x_root = 10
    enter_event.y_root = 20
    enter_callback = widget.bind.call_args_list[0][0][1]
    enter_callback(enter_event)
    tt.show.assert_called_once_with(widget, 10, 20, "Test Tooltip")

    leave_callback = widget.bind.call_args_list[1][0][1]
    leave_callback(MagicMock())
    tt.hide.assert_called_once()


# .apply_to_text
def test_apply_to_text_multipletags() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    text_widget.tag_config = MagicMock()
    text_widget.tag_bind = MagicMock()
    tt._bind_behaviours = MagicMock()
    matches = [("1.0", "1.4"), ("2.0", "2.4")]
    tt._find_all = MagicMock(return_value=matches)
    tt._create_tag = MagicMock(return_value="mock_tag")  # Mocking tag creation
    tag_map = {"tag1": "Tooltip for tag1", "tag2": "Tooltip for tag2"}

    tt.apply_to_text(text_widget, "1.0", tag_map)

    assert tt._find_all.call_count == len(tag_map)
    expected_hits = len(tag_map) * len(matches)
    assert tt._create_tag.call_count == expected_hits
    assert text_widget.tag_config.call_count == expected_hits
    assert tt._bind_behaviours.call_count == expected_hits

    for substring in tag_map:
        tt._find_all.assert_any_call(text_widget, substring, "1.0")

    for start, end in matches:
        tt._create_tag.assert_any_call(text_widget, start, end)

    text_widget.tag_config.assert_any_call("mock_tag", underline=False, foreground="#444444")
    for tooltip in tag_map.values():
        tt._bind_behaviours.assert_any_call(text_widget, "mock_tag", tooltip)


def test_apply_to_text_no_tags() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    text_widget.tag_config = MagicMock()
    text_widget.tag_bind = MagicMock()
    tt._bind_behaviours = MagicMock()
    tt._find_all = MagicMock()
    tt._create_tag = MagicMock()

    tt.apply_to_text(text_widget, "1.0", {})

    # Nothing should be called
    tt._find_all.assert_not_called()
    tt._create_tag.assert_not_called()
    text_widget.tag_config.assert_not_called()
    tt._bind_behaviours.assert_not_called()


def test_apply_to_text_passescorrecttooltip() -> None:
    tt = ToolTip()

    text_widget = MagicMock()
    tt._find_all = MagicMock(return_value=[("1.0", "1.4")])
    tt._create_tag = MagicMock(return_value="mock_tag")
    tt._bind_behaviours = MagicMock()

    tag_map = {
        "tag1": "Tooltip A",
        "tag2": "Tooltip B",
    }

    tt.apply_to_text(text_widget, "1.0", tag_map)

    calls = tt._bind_behaviours.call_args_list
    used_tooltips = [call.args[2] for call in calls]
    assert "Tooltip A" in used_tooltips
    assert "Tooltip B" in used_tooltips


# ._find_all
def test_find_all_multipleresults() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    text_widget.search = MagicMock(side_effect=["1.0", "2.0", ""])  # Simulate two matches

    results = list(tt._find_all(text_widget, "tag", "1.0"))

    assert results == [("1.0", "1.0+3c"), ("2.0", "2.0+3c")]  # "tag" has 3 letters
    calls = [call("tag", "1.0", stopindex=tk.END), call("tag", "1.0+3c", stopindex=tk.END), call("tag", "2.0+3c", stopindex=tk.END)]
    text_widget.search.assert_has_calls(calls)


def test_find_all_noresults() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    text_widget.search = MagicMock(side_effect=[""])  # Simulate no matches

    results = list(tt._find_all(text_widget, "tag", "1.0"))

    assert results == []  # No matches
    calls = [call("tag", "1.0", stopindex=tk.END)]
    text_widget.search.assert_has_calls(calls)


# ._create_tag
def test_create_tag() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    start = "1.0"
    end = "1.4"

    tag_name = tt._create_tag(text_widget, start, end)

    expected_tag_name = f"tt_1_0"
    assert tag_name == expected_tag_name
    text_widget.tag_add.assert_called_once_with(expected_tag_name, start, end)


# ._bind_behaviours
def test_bind_behaviours() -> None:
    tt = ToolTip()
    text_widget = MagicMock()
    tag_name = "mock_tag"
    tooltip_text = "Test Tooltip"

    tt.show = MagicMock()
    tt.hide = MagicMock()

    tt._bind_behaviours(text_widget, tag_name, tooltip_text)

    # Simulate motion event
    motion_event = MagicMock()
    motion_event.x_root = 10
    motion_event.y_root = 20
    motion_callback = text_widget.tag_bind.call_args_list[0][0][2]
    motion_callback(motion_event)
    tt.show.assert_called_once_with(text_widget, 10, 20, tooltip_text)

    # Simulate leave event
    leave_callback = text_widget.tag_bind.call_args_list[1][0][2]
    leave_callback(MagicMock())
    tt.hide.assert_called_once()
    
if __name__ == "__main__":
    pytest.main()