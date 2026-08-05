# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""geocog — a Midnight-Commander-style dual-pane TUI for COG → MinIO → VRT.

Three modes switch what the panes show and what F5 does:

  Mode 1 · COG creation  left: local rasters   right: local output folder
  Mode 2 · COG upload    left: local COGs      right: S3 tree (buckets)
  Mode 3 · VRT creation  left: local dest dir  right: S3 tree of COGs (multi)
"""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import Footer, Header, RichLog, Static

from . import engine, s3
from .browser import FileBrowser
from .s3tree import S3Node, S3Tree
from .screens import (
    ConfirmScreen,
    ConnectionsScreen,
    InputPrompt,
    PassphraseScreen,
    VrtNameScreen,
)
from .vault import BadPassphrase, Vault

KARTOZA_THEME = Theme(
    name="kartoza",
    primary="#E67E22",
    secondary="#16A085",
    accent="#2E6FB0",
    foreground="#E8EEF4",
    background="#0D1B2A",
    surface="#132A40",
    panel="#1F3A5F",
    success="#16A085",
    warning="#E67E22",
    error="#C0392B",
    dark=True,
)

CREDIT = "Made with 💗 by Kartoza  ·  Donate  ·  GitHub"

MODES = {
    1: "COG creation",
    2: "COG upload",
    3: "VRT creation",
}


def _any_file(_p: Path) -> bool:
    return True


class GeoCog(App):
    CSS_PATH = "app.tcss"
    TITLE = "geocog"

    BINDINGS = [
        ("f2", "show_mode(1)", "COG"),
        ("f3", "show_mode(2)", "Upload"),
        ("f4", "show_mode(3)", "VRT"),
        ("f5", "run", "Run"),
        ("tab", "focus_other", "Pane"),
        ("f7", "mkdir", "Mkdir"),
        ("f8", "delete", "Delete"),
        ("ctrl+r", "rescan", "Rescan"),
        ("c", "connections", "Connections"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self, root: str | Path | None = None, vault_path: str | Path | None = None
    ) -> None:
        super().__init__()
        self.root = Path(root or Path.cwd())
        self.vault = Vault(vault_path) if vault_path else Vault()
        self.connections: list = []
        self.passphrase: str | None = None
        self.mode = 1
        self._right = None

    # ---- layout ---------------------------------------------------------- #
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="modebar")
        with Horizontal(id="panes"):
            with Vertical(id="leftpane"):
                yield FileBrowser(
                    engine.is_raster, self.root, id="local", label="local"
                )
            yield Vertical(id="rightpane")
        yield RichLog(id="log", markup=True, wrap=True)
        yield Static(CREDIT, id="credit")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(KARTOZA_THEME)
        self.theme = "kartoza"
        self._apply_mode()
        self.query_one("#local", FileBrowser).focus()
        missing = engine.missing_tools(
            ["gdalinfo", "gdal_translate", "gdalbuildvrt", "mc"]
        )
        if missing:
            tools = ", ".join(missing)
            self.log_line(
                f"[yellow]⚠ tools not on PATH: {tools} — run inside `nix develop`[/]"
            )
        if self.vault.exists():
            self._unlock()
        else:
            self.log_line(
                "[dim]No connection vault yet — press [b]c[/b] "
                "to add a bucket connection.[/]"
            )

    # ---- helpers --------------------------------------------------------- #
    def log_line(self, message: str) -> None:
        self.query_one("#log", RichLog).write(message)

    def _log_from_thread(self, message: str) -> None:
        self.call_from_thread(self.log_line, message)

    @property
    def left(self) -> FileBrowser:
        return self.query_one("#local", FileBrowser)

    # ---- mode handling --------------------------------------------------- #
    def _apply_mode(self) -> None:
        local = self.left
        right = self.query_one("#rightpane", Vertical)
        right.remove_children()
        if self.mode == 1:
            local.set_match(engine.is_raster)
            local.label = "rasters"
            self._right = FileBrowser(
                _any_file, local.current_dir, selectable=False, label="→ output"
            )
        elif self.mode == 2:
            local.set_match(engine.is_cog)
            local.label = "COGs"
            self._right = S3Tree(self.connections, multiselect=False)
        else:
            local.set_match(_any_file)
            local.label = "destination"
            self._right = S3Tree(self.connections, multiselect=True)
        local.reload()
        right.mount(self._right)
        self.sub_title = f"{self.mode} · {MODES[self.mode]}"
        self._update_modebar()

    def _update_modebar(self) -> None:
        parts = []
        for n, label in MODES.items():
            marker = "[b $primary]" if n == self.mode else "[dim]"
            parts.append(f"{marker}F{n + 1} · {label}[/]")
        self.query_one("#modebar", Static).update("     ".join(parts))

    def action_show_mode(self, n: int) -> None:
        if n == self.mode:
            return
        self.set_focus(None)
        self.mode = n
        self._apply_mode()
        self.call_after_refresh(self.left.focus)

    def action_focus_other(self) -> None:
        left = self.left
        if self._right is None:
            return
        target = self._right if self.focused is left else left
        target.focus()

    def action_rescan(self) -> None:
        self.left.refresh_selection_pruning_missing()
        if isinstance(self._right, FileBrowser):
            self._right.reload()
        elif isinstance(self._right, S3Tree):
            self._right.set_connections(self.connections)

    # ---- file operations (F7 mkdir, F8 delete) -------------------------- #
    def _reveal_node(self, node) -> None:
        """Expand ``node`` and (re)list its children with a single fetch."""
        tree = self._right
        if not isinstance(tree, S3Tree) or node is None:
            return
        if node.is_expanded:
            tree.reload_node(node)
        else:
            if isinstance(node.data, S3Node):
                node.data.loaded = False
            node.expand()

    @work
    async def action_mkdir(self) -> None:
        pane = self.focused
        if isinstance(pane, FileBrowser):
            name = await self.push_screen_wait(
                InputPrompt(
                    "New folder", placeholder="name", note=str(pane.current_dir)
                )
            )
            if not name:
                return
            try:
                created = engine.make_dir(pane.current_dir, name)
                pane.reload()
                self.log_line(f"[green]created {created.name}/[/]")
            except OSError as exc:
                self.log_line(f"[red]mkdir failed: {exc}[/]")
        elif isinstance(pane, S3Tree):
            node = pane.cursor_node
            d = node.data if node else None
            if not isinstance(d, S3Node) or d.kind == "file":
                self.log_line(
                    "[yellow]highlight a connection, bucket or folder first[/]"
                )
                return
            title = "New bucket" if d.kind == "conn" else "New folder"
            note = (
                d.conn.name if d.kind == "conn" else f"{d.bucket}/{d.path}".rstrip("/")
            )
            name = await self.push_screen_wait(
                InputPrompt(title, placeholder="name", note=note)
            )
            if not name:
                return
            self._s3_mkdir(node, d, name)
        else:
            self.log_line("[yellow]focus a pane first (Tab)[/]")

    @work(thread=True, group="s3op")
    def _s3_mkdir(self, node, d: S3Node, name: str) -> None:
        try:
            if d.kind == "conn":
                s3.make_bucket(d.conn, name)
            else:
                s3.make_folder(d.conn, d.bucket, d.path, name)
        except engine.EngineError as exc:
            self._log_from_thread(f"[red]mkdir failed: {exc}[/]")
            return
        self._log_from_thread(f"[green]created {name}[/]")
        self.call_from_thread(self._reveal_node, node)

    @work
    async def action_delete(self) -> None:
        pane = self.focused
        if isinstance(pane, FileBrowser):
            target = pane.highlighted_path
            if target is None:
                self.log_line("[yellow]nothing under the cursor to delete[/]")
                return
            kind = "folder" if target.is_dir() else "file"
            if await self.push_screen_wait(
                ConfirmScreen(f"Delete {kind} '{target.name}'?")
            ):
                try:
                    engine.delete_path(target)
                    pane.reload()
                    self.log_line(f"[green]deleted {target.name}[/]")
                except OSError as exc:
                    self.log_line(f"[red]{exc}[/]")
        elif isinstance(pane, S3Tree):
            node = pane.cursor_node
            d = node.data if node else None
            if not isinstance(d, S3Node) or d.kind == "conn":
                self.log_line("[yellow]select a bucket, folder or file to delete[/]")
                return
            label = d.bucket if d.kind == "bucket" else f"{d.bucket}/{d.path}"
            if await self.push_screen_wait(
                ConfirmScreen(f"Delete {d.kind} '{label}' from {d.conn.name}?")
            ):
                self._s3_delete(node, d)
        else:
            self.log_line("[yellow]focus a pane first (Tab)[/]")

    @work(thread=True, group="s3op")
    def _s3_delete(self, node, d: S3Node) -> None:
        try:
            if d.kind == "bucket":
                s3.remove_bucket(d.conn, d.bucket, log=self._log_from_thread)
            elif d.kind == "folder":
                s3.remove(
                    d.conn, d.bucket, d.path, recursive=True, log=self._log_from_thread
                )
            else:
                s3.remove(
                    d.conn, d.bucket, d.path, recursive=False, log=self._log_from_thread
                )
        except engine.EngineError as exc:
            self._log_from_thread(f"[red]delete failed: {exc}[/]")
            return
        self._log_from_thread(f"[green]deleted {d.kind} {d.bucket}/{d.path}[/]")
        self.call_from_thread(self._right.reload_node, node.parent)

    # ---- run (F5) -------------------------------------------------------- #
    def action_run(self) -> None:
        if self.mode == 1:
            self._run_convert()
        elif self.mode == 2:
            self._run_upload()
        else:
            self._run_vrt()

    @work(thread=True, exclusive=True, group="run")
    def _run_convert(self) -> None:
        files = self.left.selected_paths
        outdir = (
            self._right.current_dir
            if isinstance(self._right, FileBrowser)
            else self.root
        )
        if not files:
            self._log_from_thread(
                "[yellow]select rasters on the left (Space), then F5[/]"
            )
            return
        self._log_from_thread(f"[b]› converting {len(files)} file(s) → {outdir}[/b]")
        for f in files:
            self._log_from_thread(f"  {Path(f).name}")
            try:
                out = engine.to_cog(f, outdir=outdir, log=self._log_from_thread)
                self._log_from_thread(f"[green]  ✓ {out.name}[/]")
            except engine.EngineError as exc:
                self._log_from_thread(f"[red]  ✗ {exc}[/]")
        self.call_from_thread(self.action_rescan)

    @work(thread=True, exclusive=True, group="run")
    def _run_upload(self) -> None:
        tree = self._right
        files = self.left.selected_paths
        node = tree.cursor_node if isinstance(tree, S3Tree) else None
        target = tree.upload_target() if isinstance(tree, S3Tree) else None
        if not files:
            self._log_from_thread("[yellow]select COGs on the left (Space)[/]")
            return
        if target is None:
            self._log_from_thread(
                "[yellow]highlight a bucket or folder on the right to upload into[/]"
            )
            return
        conn, bucket, prefix = target
        dest = f"{bucket}/{prefix}".rstrip("/")
        self._log_from_thread(
            f"[b]› uploading {len(files)} file(s) → {conn.name}:{dest}[/b]"
        )
        try:
            urls = s3.upload(files, conn, bucket, prefix, log=self._log_from_thread)
        except engine.EngineError as exc:
            self._log_from_thread(f"[red]  ✗ {exc}[/]")
            return
        for u in urls:
            self._log_from_thread(f"[green]  ✓ {u}[/]")
        # rescan the destination node so the uploaded objects appear
        self.call_from_thread(self._reveal_node, node)

    @work
    async def _run_vrt(self) -> None:
        if not isinstance(self._right, S3Tree) or not self._right.selected:
            self.log_line("[yellow]select COG files/folders on the right (Space)[/]")
            return
        target_dir = str(self.left.current_dir)
        name = await self.push_screen_wait(VrtNameScreen(target_dir=target_dir))
        if not name:
            return
        self._build_vrt(name, target_dir)

    @work(thread=True, exclusive=True, group="run")
    def _build_vrt(self, name: str, outdir: str) -> None:
        self._log_from_thread("[b]› resolving COGs…[/b]")
        try:
            urls = self._right.selected_cog_urls()
        except engine.EngineError as exc:
            self._log_from_thread(f"[red]  ✗ {exc}[/]")
            return
        if not urls:
            self._log_from_thread("[yellow]no COGs found in the selection[/]")
            return
        out = Path(outdir) / name
        self._log_from_thread(f"[b]› building {out}[/b]")
        try:
            engine.build_vrt(urls, out, log=self._log_from_thread)
            self._log_from_thread(f"[green]  ✓ wrote {out}[/]")
            for line in engine.gdalinfo_summary(out).splitlines():
                self._log_from_thread(f"    {line}")
        except engine.EngineError as exc:
            self._log_from_thread(f"[red]  ✗ {exc}[/]")
        self.call_from_thread(self.left.reload)

    # ---- connections / vault -------------------------------------------- #
    def _refresh_s3(self) -> None:
        if isinstance(self._right, S3Tree):
            self._right.set_connections(self.connections)

    @work
    async def _unlock(self) -> None:
        while True:
            pw = await self.push_screen_wait(PassphraseScreen(create=False))
            if pw is None:
                self.log_line(
                    "[yellow]vault locked — connections unavailable until unlocked[/]"
                )
                return
            try:
                self.connections = self.vault.load(pw)
                self.passphrase = pw
                self._refresh_s3()
                self.log_line(
                    f"[green]unlocked {len(self.connections)} connection(s)[/]"
                )
                return
            except BadPassphrase:
                self.notify("Incorrect passphrase", severity="error")

    @work
    async def action_connections(self) -> None:
        result = await self.push_screen_wait(ConnectionsScreen(self.connections))
        if result is None:
            return
        self.connections = result
        await self._save_vault()
        self._refresh_s3()

    async def _save_vault(self) -> None:
        if self.passphrase is None:
            pw = await self.push_screen_wait(PassphraseScreen(create=True))
            if not pw:
                self.notify("Not saved — no passphrase set", severity="warning")
                return
            self.passphrase = pw
        try:
            self.vault.save(self.connections, self.passphrase)
            self.notify(f"Saved {len(self.connections)} connection(s)")
        except Exception as exc:  # noqa: BLE001
            self.notify(f"Save failed: {exc}", severity="error")


def main() -> None:
    GeoCog().run()


if __name__ == "__main__":
    main()
