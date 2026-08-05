" SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
" SPDX-License-Identifier: MIT
"
" Project whichkey shortcuts for geocog, under <leader>p.
" Loaded by Neovim when 'exrc' is enabled (see .nvim.lua).

" <leader>p — project menu
nnoremap <leader>pr :!nix run .#geocog<CR>
nnoremap <leader>pt :!nix develop --command pytest<CR>
nnoremap <leader>pl :!nix develop --command ruff check .<CR>
nnoremap <leader>pf :!nix develop --command ruff format .<CR>
nnoremap <leader>pd :!nix run .#docs<CR>
nnoremap <leader>pD :!nix develop --command mkdocs build --strict<CR>
nnoremap <leader>pb :!nix build .#geocog -L<CR>
nnoremap <leader>pc :!nix develop --command pre-commit run --all-files<CR>
nnoremap <leader>ps :!nix develop --command reuse lint<CR>
