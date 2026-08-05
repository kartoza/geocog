# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Headless smoke tests for the dual-pane app."""

from __future__ import annotations

import asyncio

from geocog.app import GeoCog
from geocog.browser import FileBrowser
from geocog.s3tree import S3Tree


def _run(coro_factory, tmp_path):
    async def scenario():
        app = GeoCog(root=tmp_path, vault_path=tmp_path / "v.vault")
        async with app.run_test() as pilot:
            await coro_factory(app, pilot)

    asyncio.run(scenario())


def test_boots_in_mode1_dual_pane(tmp_path):
    async def body(app, pilot):
        assert app.mode == 1
        assert isinstance(app.left, FileBrowser)
        assert isinstance(app._right, FileBrowser)  # local output folder

    _run(body, tmp_path)


def test_mode_switching_swaps_right_pane(tmp_path):
    async def body(app, pilot):
        await pilot.press("f3")  # mode 2 upload
        assert app.mode == 2
        assert isinstance(app._right, S3Tree)
        await pilot.press("f4")  # mode 3 vrt
        assert app.mode == 3
        assert isinstance(app._right, S3Tree)
        assert app._right.multiselect is True
        await pilot.press("f2")  # back to mode 1
        assert app.mode == 1
        assert isinstance(app._right, FileBrowser)

    _run(body, tmp_path)


def test_tab_toggles_active_pane(tmp_path):
    async def body(app, pilot):
        app.left.focus()
        await pilot.pause()
        assert app.focused is app.left
        await pilot.press("tab")
        assert app.focused is app._right

    _run(body, tmp_path)


def test_left_filter_changes_with_mode(tmp_path):
    (tmp_path / "a.tif").write_text("x")
    (tmp_path / "a.cog.tif").write_text("x")

    async def body(app, pilot):
        # mode 1: raster shown, cog hidden
        labels = _option_names(app.left)
        assert "a.tif" in labels and "a.cog.tif" not in labels
        await pilot.press("f3")  # mode 2: cogs shown
        labels = _option_names(app.left)
        assert "a.cog.tif" in labels and "a.tif" not in labels

    _run(body, tmp_path)


def test_mkdir_on_focused_local_pane(tmp_path):
    async def body(app, pilot):
        app.left.focus()
        await pilot.pause()
        await pilot.press("f7")
        await pilot.pause()
        # InputPrompt is now on screen; type a name and confirm
        await pilot.press("n", "e", "w", "d", "i", "r")
        await pilot.press("enter")
        await pilot.pause()
        assert (tmp_path / "newdir").is_dir()

    _run(body, tmp_path)


def test_delete_confirm_removes_local_file(tmp_path):
    (tmp_path / "gone.tif").write_text("x")

    from geocog.screens import ConfirmScreen

    async def body(app, pilot):
        app.left.focus()
        await pilot.pause()
        browser = app.left
        idx = next(
            i
            for i in range(browser.option_count)
            if str(browser.get_option_at_index(i).id).endswith("gone.tif")
        )
        browser.highlighted = idx
        await pilot.press("f8")
        await pilot.pause()
        assert isinstance(app.screen, ConfirmScreen)
        app.screen._ok()  # confirm the delete
        await pilot.pause()
        await pilot.pause()
        assert not (tmp_path / "gone.tif").exists()

    _run(body, tmp_path)


def _option_names(browser: FileBrowser) -> set[str]:
    names = set()
    for i in range(browser.option_count):
        prompt = browser.get_option_at_index(i).prompt
        names.add(str(prompt).split("  ")[-1])
    return names
