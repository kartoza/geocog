-- SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
-- SPDX-License-Identifier: MIT
--
-- Project-local Neovim customisations for geocog. Loaded when Neovim's 'exrc'
-- option is enabled and this directory is trusted (:trust).

-- Register the <leader>p group with which-key if it is available.
local ok, wk = pcall(require, "which-key")
if ok then
  wk.add({
    { "<leader>p", group = "geocog project" },
    { "<leader>pr", "<cmd>!nix run .#geocog<cr>", desc = "Run TUI" },
    { "<leader>pt", "<cmd>!nix develop --command pytest<cr>", desc = "Test" },
    { "<leader>pl", "<cmd>!nix develop --command ruff check .<cr>", desc = "Lint" },
    { "<leader>pf", "<cmd>!nix develop --command ruff format .<cr>", desc = "Format" },
    { "<leader>pd", "<cmd>!nix run .#docs<cr>", desc = "Docs (serve)" },
    { "<leader>pD", "<cmd>!nix develop --command mkdocs build --strict<cr>", desc = "Docs (build)" },
    { "<leader>pb", "<cmd>!nix build .#geocog -L<cr>", desc = "Build package" },
    { "<leader>pc", "<cmd>!nix develop --command pre-commit run --all-files<cr>", desc = "Pre-commit" },
    { "<leader>ps", "<cmd>!nix develop --command reuse lint<cr>", desc = "REUSE lint" },
  })
end

-- Treat the Textual stylesheet as CSS for syntax highlighting.
vim.filetype.add({ extension = { tcss = "css" } })
