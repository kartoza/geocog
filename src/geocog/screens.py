# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Modal dialogs for geocog: passphrase, connection manager, VRT name."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList
from textual.widgets.option_list import Option

from .vault import Connection


class PassphraseScreen(ModalScreen[str | None]):
    """Prompt for the vault master passphrase (optionally with confirmation)."""

    def __init__(self, create: bool = False, message: str | None = None) -> None:
        super().__init__()
        self.create = create
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(
                self.message
                or (
                    "Set a master passphrase for the connection vault"
                    if self.create
                    else "Unlock connection vault"
                ),
                classes="dialog-title",
            )
            yield Input(password=True, id="p1", placeholder="passphrase")
            if self.create:
                yield Input(password=True, id="p2", placeholder="confirm passphrase")
            yield Label("", id="err", classes="error")
            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#p1", Input).focus()

    @on(Input.Submitted)
    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        p1 = self.query_one("#p1", Input).value
        if not p1:
            self.query_one("#err", Label).update("passphrase cannot be empty")
            return
        if self.create:
            p2 = self.query_one("#p2", Input).value
            if p1 != p2:
                self.query_one("#err", Label).update("passphrases do not match")
                return
        self.dismiss(p1)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class VrtNameScreen(ModalScreen[str | None]):
    """Ask for the output VRT filename."""

    def __init__(self, default: str = "mosaic.vrt", target_dir: str = "") -> None:
        super().__init__()
        self.default = default
        self.target_dir = target_dir

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("Create VRT", classes="dialog-title")
            if self.target_dir:
                yield Label(f"in {self.target_dir}", classes="dim")
            yield Input(value=self.default, id="name")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Create", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    @on(Input.Submitted)
    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        if name:
            if not name.endswith(".vrt"):
                name += ".vrt"
            self.dismiss(name)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class InputPrompt(ModalScreen[str | None]):
    """Generic single-line text prompt (e.g. new folder name)."""

    def __init__(
        self, title: str, default: str = "", placeholder: str = "", note: str = ""
    ) -> None:
        super().__init__()
        self._title = title
        self._default = default
        self._placeholder = placeholder
        self._note = note

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label(self._title, classes="dialog-title")
            if self._note:
                yield Label(self._note, classes="dim")
            yield Input(value=self._default, placeholder=self._placeholder, id="value")
            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#value", Input).focus()

    @on(Input.Submitted)
    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        value = self.query_one("#value", Input).value.strip()
        if value:
            self.dismiss(value)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class ConfirmScreen(ModalScreen[bool]):
    """Yes/no confirmation, defaulting to the safe (cancel) choice."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, message: str, confirm_label: str = "Delete") -> None:
        super().__init__()
        self._message = message
        self._confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("Confirm", classes="dialog-title")
            yield Label(self._message)
            with Horizontal(classes="dialog-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button(self._confirm_label, variant="error", id="ok")

    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss(False)


class ConnectionEditScreen(ModalScreen[Connection | None]):
    """Add or edit a single connection."""

    def __init__(self, connection: Connection | None = None) -> None:
        super().__init__()
        self.connection = connection

    def compose(self) -> ComposeResult:
        c = self.connection or Connection(name="")
        with Vertical(classes="dialog"):
            yield Label(
                "Edit connection" if self.connection else "Add connection",
                classes="dialog-title",
            )
            yield Input(value=c.name, placeholder="name", id="name")
            yield Input(value=c.endpoint, placeholder="S3 API endpoint", id="endpoint")
            yield Input(value=c.access_key, placeholder="access key", id="access")
            yield Input(
                value=c.secret_key, placeholder="secret key", password=True, id="secret"
            )
            yield Label("", id="err", classes="error")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        endpoint = self.query_one("#endpoint", Input).value.strip()
        if not name or not endpoint:
            self.query_one("#err", Label).update("name and endpoint are required")
            return
        self.dismiss(
            Connection(
                name=name,
                endpoint=endpoint,
                access_key=self.query_one("#access", Input).value.strip(),
                secret_key=self.query_one("#secret", Input).value.strip(),
            )
        )

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class ConnectionsScreen(ModalScreen[list | None]):
    """Manage the list of connections. Returns the updated list, or None."""

    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, connections: list[Connection]) -> None:
        super().__init__()
        self.connections = [Connection(**vars(c)) for c in connections]
        self.changed = False

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog wide"):
            yield Label("Connections", classes="dialog-title")
            yield OptionList(id="conn_list")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Edit", id="edit")
                yield Button("Delete", id="delete")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        ol = self.query_one("#conn_list", OptionList)
        ol.clear_options()
        if not self.connections:
            ol.add_option(Option("[dim](none yet — Add one)[/]", disabled=True))
            return
        for i, c in enumerate(self.connections):
            ol.add_option(Option(f"[b]{c.name}[/]  [dim]{c.endpoint}[/]", id=str(i)))

    def _selected_index(self) -> int | None:
        ol = self.query_one("#conn_list", OptionList)
        if ol.highlighted is None or not self.connections:
            return None
        opt = ol.get_option_at_index(ol.highlighted)
        return int(opt.id) if opt.id is not None else None

    @on(Button.Pressed, "#add")
    def _add(self) -> None:
        def done(conn: Connection | None) -> None:
            if conn:
                self.connections.append(conn)
                self.changed = True
                self._refresh()

        self.app.push_screen(ConnectionEditScreen(), done)

    @on(Button.Pressed, "#edit")
    def _edit(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return

        def done(conn: Connection | None) -> None:
            if conn:
                self.connections[idx] = conn
                self.changed = True
                self._refresh()

        self.app.push_screen(ConnectionEditScreen(self.connections[idx]), done)

    @on(Button.Pressed, "#delete")
    def _delete(self) -> None:
        idx = self._selected_index()
        if idx is not None:
            del self.connections[idx]
            self.changed = True
            self._refresh()

    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        self.dismiss(self.connections if self.changed else None)
