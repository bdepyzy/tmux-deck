# tmux-board

A sleek interactive grid of your tmux sessions. Each session is a card that
tells you what the project is actually up to — no LLMs, just your environment:

```
 tmux board · 6 sessions

 ╭╴candidex-4╶───────────────────────╮  ╭╴scratchpad-5 ●╶────────────────────╮
 │  5 win · 3m ago                   │  │  3 win · 35s ago                   │
 │  ⎇ SECURITY/hardening-speed ±3 ↑1 │  │  ~                                 │
 │  Harden imports and fro…  20h ago │  │  ⏵⏵ bypass permissions on (shift+… │
 │  ▸ candidex · claude              │  │  ▸ bdepyzy · claude                │
 ╰──────────────────────────────╴1╶──╯  ╰──────────────────────────────╴2╶──╯
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
pipx install tmux-board     # or: uv tool install tmux-board
```

Requires Python ≥ 3.9 and tmux. No Python dependencies — it's a single
stdlib-curses file.

## Use

```sh
tmux-board
```

| key | action |
| --- | --- |
| `←↑↓→` / mouse | move between cards |
| `Enter` / click selected / double-click | attach (uses `switch-client` inside tmux) |
| `1`–`9` | jump straight into that session |
| `x` | kill selected session (confirms) |
| `r` | refresh |
| `q` / `Esc` | quit |

Handy tmux binding — the board as a centered popup on `prefix + S`:

```tmux
bind S display-popup -E -w 90% -h 80% tmux-board
```

## License

MIT
