# tmux-deck
Completely vibecoded interactive deck for tmux sessions. Each session is a card that
tells you what the project is actually up to:

```
 tmux deck · 4 sessions

 ╭╴api-server ●╶─────────────────────╮  ╭╴blog╶─────────────────────────────╮
 │  5 win · 3m ago                   │  │  2 win · 2h ago                   │
 │  ⎇ feat/rate-limiting ±3 ↑1       │  │  ⎇ main                           │
 │  Add sliding-window li…   20h ago │  │  publish: zero-downtime d…  3d ago│
 │  ▸ server · vim                   │  │  ▸ blog · zsh                     │
 ╰───────────────────────────────╴1╶─╯  ╰───────────────────────────────╴2╶─╯

 ╭╴dotfiles╶─────────────────────────╮  ╭╴scratch╶──────────────────────────╮
 │  3 win · 1d ago                   │  │  1 win · 40s ago                  │
 │  ⎇ main ±12                       │  │  ~/tmp                            │
 │  waybar: battery module…   2w ago │  │  $ python bench.py --runs 50      │
 │  ▸ hypr · zsh                     │  │  ▸ scratch · python               │
 ╰───────────────────────────────╴3╶─╯  ╰───────────────────────────────╴4╶─╯

   ←↑↓→ move   ↵ attach   / search   1-9 jump   x kill   r refresh   q quit
```

Each card shows:

- **session name**, with a green `●` when attached
- **windows · last activity**, and the session group if any
- **git status** of the active pane's directory — branch, `±N` dirty files,
  `↑N`/`↓N` unpushed/unpulled commits (yellow when dirty, green when clean)
- **last commit subject + age** — the project's latest update, straight from
  `git log` (falls back to the last line of pane output outside a repo)
- **what's running** — active window name and current command

## Install

```sh
pipx install tmux-deck      # or: uv tool install tmux-deck
```

Requires Python ≥ 3.9 and tmux. No Python dependencies — it's a single
stdlib-curses file.

## Use

```sh
tmux-deck
```

| key | action |
| --- | --- |
| `←↑↓→` / mouse | move between cards |
| `Enter` / click selected / double-click | attach (uses `switch-client` inside tmux) |
| `/` | search sessions by name — a centered box live-filters as you type; arrows move among matches, `Enter` attaches, `Esc` cancels |
| `1`–`9` | jump straight into that session |
| `x` | kill selected session (confirms) |
| `r` | refresh |
| `q` / `Esc` | quit |

Handy tmux binding — the deck as a centered popup on `prefix + S`:

```tmux
bind S display-popup -E -w 90% -h 80% tmux-deck
```

## License

MIT
