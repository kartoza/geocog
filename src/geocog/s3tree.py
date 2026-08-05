# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""S3 tree widget: connections → buckets → folders/files, lazily loaded."""

from __future__ import annotations

from dataclasses import dataclass

from textual import work
from textual.binding import Binding
from textual.widgets import Tree

from . import s3
from .vault import Connection

FOLDER = "🗀 "
FILE = "🗎 "
MARK_ON = "[b $success]◉[/] "
MARK_OFF = "○ "


@dataclass
class S3Node:
    kind: str  # conn | bucket | folder | file
    conn: Connection
    bucket: str | None = None
    path: str = ""  # key within bucket (no leading/trailing slash)
    loaded: bool = False

    @property
    def key(self) -> tuple:
        return (self.conn.name, self.bucket, self.path)

    @property
    def leaf_name(self) -> str:
        if self.kind == "bucket":
            return self.bucket or ""
        return self.path.rsplit("/", 1)[-1] or self.bucket or ""


class S3Tree(Tree):
    """A tree of registered connections and their bucket contents."""

    BINDINGS = [Binding("space", "noop", "Select")]

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

    def __init__(
        self, connections=None, multiselect: bool = False, id: str | None = None
    ):
        super().__init__("s3", id=id)
        self.show_root = False
        self.guide_depth = 3
        self.multiselect = multiselect
        self._connections = list(connections or [])
        self.selected: dict[tuple, S3Node] = {}

    def on_mount(self) -> None:
        self.set_connections(self._connections)

    def action_noop(self) -> None:
        pass

    def on_key(self, event) -> None:
        if event.key == "space":
            event.stop()
            event.prevent_default()
            self.toggle_selected()
            return
        if event.key in self._APP_KEYS:
            name, params = self._APP_KEYS[event.key]
            event.stop()
            event.prevent_default()
            getattr(self.app, f"action_{name}")(*params)

    # ---- population ----------------------------------------------------- #
    def set_connections(self, connections) -> None:
        self._connections = list(connections)
        self.selected.clear()
        self.root.remove_children()
        if not self._connections:
            self.root.add_leaf("[dim](no connections — press [b]c[/b] to add one)[/]")
            return
        for conn in self._connections:
            self.root.add(
                f"[b]{conn.name}[/]  [dim]{conn.endpoint}[/]",
                data=S3Node("conn", conn),
                allow_expand=True,
            )

    def _base_label(self, d: S3Node) -> str:
        if d.kind == "file":
            return FILE + d.leaf_name
        return FOLDER + d.leaf_name

    def _label(self, d: S3Node) -> str:
        if self.multiselect and d.kind in ("file", "folder"):
            mark = MARK_ON if d.key in self.selected else MARK_OFF
            return mark + self._base_label(d)
        return self._base_label(d)

    def on_tree_node_expanded(self, event) -> None:
        node = event.node
        d = node.data
        if not isinstance(d, S3Node) or d.loaded:
            return
        d.loaded = True
        node.remove_children()
        node.add_leaf("[dim]loading…[/]")
        self._load(node)

    @work(thread=True, group="s3")
    def _load(self, node) -> None:
        d: S3Node = node.data
        try:
            if d.kind == "conn":
                entries = s3.list_entries(d.conn, "")
                children = [
                    S3Node("bucket", d.conn, bucket=e.name, path="")
                    for e in entries
                    if e.is_dir
                ]
            else:
                base = f"{d.bucket}/{d.path}".strip("/") + "/"
                entries = s3.list_entries(d.conn, base)
                children = []
                for e in entries:
                    child = f"{d.path}/{e.name}".strip("/") if d.path else e.name
                    children.append(
                        S3Node(
                            "folder" if e.is_dir else "file", d.conn, d.bucket, child
                        )
                    )
        except Exception as exc:  # noqa: BLE001 - surface any mc/network error
            self.app.call_from_thread(self._error, node, str(exc))
            return
        self.app.call_from_thread(self._populate, node, children)

    def _populate(self, node, children: list[S3Node]) -> None:
        node.remove_children()
        if not children:
            node.add_leaf("[dim](empty)[/]")
            return
        for child in children:
            if child.kind == "file":
                node.add_leaf(self._label(child), data=child)
            else:
                node.add(self._label(child), data=child, allow_expand=True)

    def _error(self, node, message: str) -> None:
        node.remove_children()
        node.add_leaf(f"[red]✗ {message}[/]")

    # ---- selection ------------------------------------------------------ #
    def toggle_selected(self) -> None:
        node = self.cursor_node
        if node is None or not isinstance(node.data, S3Node):
            return
        d = node.data
        if not self.multiselect or d.kind not in ("file", "folder"):
            return
        if d.key in self.selected:
            del self.selected[d.key]
        else:
            self.selected[d.key] = d
        node.set_label(self._label(d))

    def upload_target(self) -> tuple[Connection, str, str] | None:
        """For mode 2: the highlighted bucket/folder as (conn, bucket, prefix)."""
        node = self.cursor_node
        d = node.data if node else None
        if isinstance(d, S3Node) and d.kind in ("bucket", "folder"):
            return (d.conn, d.bucket, d.path)
        return None

    def reload_node(self, node) -> None:
        """Force a lazy re-list of ``node``'s children."""
        if node is None:
            return
        d = node.data
        if isinstance(d, S3Node):
            d.loaded = False
        node.remove_children()
        if node.is_expanded and isinstance(d, S3Node):
            d.loaded = True
            node.add_leaf("[dim]loading…[/]")
            self._load(node)

    def selected_cog_urls(self) -> list[str]:
        """For mode 3: object URLs for every selected COG (folders expanded)."""
        urls: list[str] = []
        for d in self.selected.values():
            if d.kind == "file":
                urls.append(s3.object_url(d.conn, d.bucket, d.path))
            else:
                for key in s3.list_cogs_recursive(d.conn, d.bucket, d.path):
                    urls.append(s3.object_url(d.conn, d.bucket, key))
        return urls
