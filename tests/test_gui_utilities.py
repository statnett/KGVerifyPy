import pytest
import tkinter as tk
from tkinter import ttk
from src.kgverifypy.gui_utilites import CollapsibleSection


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


if __name__ == "__main__":
    pytest.main()