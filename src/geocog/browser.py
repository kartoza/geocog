# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""A small file/folder browser widget for geocog.

Navigate up and down the directory tree; select individual files, or select a
whole folder to grab every matching file underneath it (recursively). Only files
matching a caller-supplied predicate are shown/selectable; directories are always
shown so you can move through the hierarchy.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from textual.binding import Binding
from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

UP_ID = "::up::"
NONE_ID = "::none::"

MARK_ALL = "[b $success]☑[/]"
MARK_SOME = "[b $warning]◐[/]"
MARK_NONE = "☐"


class FileBrowser(OptionList):
    """An OptionList that browses the filesystem with multi-select."""

    # Shown in the footer for discoverability; the actual handling is in
    # on_key() because a focused OptionList does not bubble these keys to the
    # app's bindings.
    BINDINGS = [
        Binding("space", "noop", "Select"),
        Binding("backspace", "noop", "Up a level"),
    ]

    # keys forwarded to the app so the workflow shortcuts work while focused here
    _APP_KEYS = {
        "f2": ("show_mode", (1,)),
        "f3": ("show_mode", (2,)),
        "f4": ("show_mode", (3,)),
        "f5": ("run", ()),
        "ctrl+r": ("rescan", ()),
        "c": ("connections", ()),
        "tab": ("focus_other", ()),
        "f7": ("mkdir", ()),
        "f8": ("delete", ()),
    }

    def action_noop(self) -> None:  # footer labels only
        pass

    def on_key(self, event) -> None:
        key = event.key
        if key == "space":
            event.stop()
            event.prevent_default()
            self.action_toggle()
            return
        if key == "backspace":
            event.stop()
            event.prevent_default()
            self.action_up()
            return
        if key in self._APP_KEYS:
            name, params = self._APP_KEYS[key]
            event.stop()
            event.prevent_default()
            getattr(self.app, f"action_{name}")(*params)

    class SelectionChanged(Message):
        def __init__(self, browser: FileBrowser) -> None:
            self.browser = browser
            super().__init__()

    def __init__(
        self,
        match: Callable[[Path], bool],
        root: str | Path,
        id: str | None = None,
        selectable: bool = True,
        label: str = "",
    ):
        super().__init__(id=id)
        self._match = match
        self.path = Path(root).resolve()
        self.selected: set[Path] = set()
        self.can_focus = True
        self.selectable = selectable
        self.label = label

    def on_mount(self) -> None:
        self.border_title = str(self.path)
        self.reload()

    def set_match(self, match: Callable[[Path], bool]) -> None:
        """Change which files are shown/selectable and refresh."""
        self._match = match
        self.selected.clear()
        self.reload()

    @property
    def current_dir(self) -> Path:
        return self.path

    @property
    def highlighted_path(self) -> Path | None:
        """Filesystem path of the entry under the cursor (None for '..'/empty)."""
        if self.highlighted is None:
            return None
        oid = self.get_option_at_index(self.highlighted).id
        if oid in (UP_ID, NONE_ID, None):
            return None
        return Path(oid)

    # ---- filesystem helpers (pure) -------------------------------------- #
    def _subdirs(self, d: Path) -> list[Path]:
        try:
            return sorted(
                p for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")
            )
        except OSError:
            return []

    def _files(self, d: Path) -> list[Path]:
        try:
            return sorted(p for p in d.iterdir() if p.is_file() and self._match(p))
        except OSError:
            return []

    def _under(self, d: Path) -> list[Path]:
        try:
            return [p for p in d.rglob("*") if p.is_file() and self._match(p)]
        except OSError:
            return []

    def _dir_mark(self, d: Path) -> str:
        files = self._under(d)
        if not files:
            return " "
        sel = sum(1 for f in files if f in self.selected)
        if sel == 0:
            return MARK_NONE
        return MARK_ALL if sel == len(files) else MARK_SOME

    # ---- rendering ------------------------------------------------------ #
    def reload(self) -> None:
        keep = self.highlighted
        self.clear_options()
        options: list[Option] = []
        if self.path.parent != self.path:
            options.append(Option("⬆   ..", id=UP_ID))
        for d in self._subdirs(self.path):
            options.append(Option(f"{self._dir_mark(d)}  [b]{d.name}/[/]", id=str(d)))
        for f in self._files(self.path):
            mark = MARK_ALL if f in self.selected else MARK_NONE
            options.append(Option(f"{mark}  {f.name}", id=str(f)))
        if not self._subdirs(self.path) and not self._files(self.path):
            options.append(Option("[dim](no matching files here)[/]", id=NONE_ID))
        self.add_options(options)
        prefix = f"{self.label}  " if self.label else ""
        if self.selectable:
            self.border_title = (
                f"{prefix}{self.path}   ·   {len(self.selected)} selected"
            )
        else:
            self.border_title = f"{prefix}{self.path}"
        if keep is not None and options:
            self.highlighted = max(0, min(keep, len(options) - 1))

    # ---- interactions --------------------------------------------------- #
    def _open(self, path: Path) -> None:
        self.path = path
        self.reload()
        self.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        oid = event.option_id
        if oid == UP_ID:
            self._open(self.path.parent)
        elif oid in (None, NONE_ID):
            return
        else:
            p = Path(oid)
            if p.is_dir():
                self._open(p)
            else:
                self._toggle_file(p)

    def action_toggle(self) -> None:
        if not self.selectable or self.highlighted is None:
            return
        oid = self.get_option_at_index(self.highlighted).id
        if oid in (UP_ID, NONE_ID, None):
            return
        p = Path(oid)
        self._toggle_dir(p) if p.is_dir() else self._toggle_file(p)

    def action_up(self) -> None:
        if self.path.parent != self.path:
            self._open(self.path.parent)

    def _toggle_file(self, p: Path) -> None:
        self.selected.discard(p) if p in self.selected else self.selected.add(p)
        self.reload()
        self.post_message(self.SelectionChanged(self))

    def _toggle_dir(self, d: Path) -> None:
        files = self._under(d)
        if files and all(f in self.selected for f in files):
            self.selected.difference_update(files)
        else:
            self.selected.update(files)
        self.reload()
        self.post_message(self.SelectionChanged(self))

    # ---- public --------------------------------------------------------- #
    @property
    def selected_paths(self) -> list[str]:
        return [str(p) for p in sorted(self.selected)]

    def refresh_selection_pruning_missing(self) -> None:
        """Drop selections whose files disappeared, then reload."""
        self.selected = {p for p in self.selected if p.exists()}
        self.reload()
