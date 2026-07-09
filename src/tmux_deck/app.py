#!/usr/bin/env python3
"""tmux-deck — a sleek interactive grid of your tmux sessions.

Each session is a card showing what the project is up to: git branch,
dirty/unpushed state, last commit, and what's running right now.
Navigate with arrows or mouse, Enter to attach, 1-9 to jump.
"""

__version__ = "0.1.0"

import math
import os
import subprocess
import sys
import time

os.environ.setdefault("ESCDELAY", "25")  # snappy Esc
import curses

SEP = "\x1f"
CARD_H = 6          # title border + 4 content lines + bottom border
ROW_GAP = 1
COL_GAP = 2
MIN_CARD_W = 36
MAX_CARD_W = 50

HOME = os.path.expanduser("~")

A = {}  # attribute palette, filled by init_colors()


# ── data ────────────────────────────────────────────────────────────────────

def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def out(args):
    return sh(args).stdout


def short_when(s):
    """Compress git's '%cr' style dates: '2 hours ago' -> '2h ago'."""
    for long, short in (
        ("seconds", "s"), ("second", "s"),
        ("minutes", "m"), ("minute", "m"),
        ("hours", "h"), ("hour", "h"),
        ("days", "d"), ("day", "d"),
        ("weeks", "w"), ("week", "w"),
        ("months", "mo"), ("month", "mo"),
        ("years", "y"), ("year", "y"),
    ):
        s = s.replace(" " + long, short).replace(long, short)
    return s


def git_info(path):
    if not path or not os.path.isdir(path):
        return None

    def g(*a):
        return sh(["git", "-C", path, *a])

    r = g("rev-parse", "--abbrev-ref", "HEAD")
    if r.returncode != 0:
        return None
    branch = r.stdout.strip()

    dirty = len([l for l in g("status", "--porcelain").stdout.splitlines() if l.strip()])

    log = g("log", "-1", "--format=%s" + SEP + "%cr").stdout.strip()
    subject, when = (log.split(SEP) + ["", ""])[:2]

    ab = ""
    r2 = g("rev-list", "--left-right", "--count", "@{u}...HEAD")
    if r2.returncode == 0 and r2.stdout.split():
        behind, ahead = r2.stdout.split()
        bits = []
        if int(ahead):
            bits.append("↑" + ahead)
        if int(behind):
            bits.append("↓" + behind)
        ab = " ".join(bits)

    return {
        "branch": branch,
        "dirty": dirty,
        "subject": subject,
        "when": short_when(when),
        "ab": ab,
    }


def tilde(path):
    return "~" + path[len(HOME):] if path.startswith(HOME) else path


def ell(text, n):
    if n <= 0:
        return ""
    return text if len(text) <= n else text[: max(0, n - 1)] + "…"


def get_sessions():
    fmt = SEP.join(
        [
            "#{session_name}",
            "#{session_windows}",
            "#{session_attached}",
            "#{session_activity}",
            "#{session_group}",
        ]
    )
    sessions = []
    for line in out(["tmux", "list-sessions", "-F", fmt]).splitlines():
        name, windows, attached, activity, group = line.split(SEP)
        target = f"={name}:"
        winfo = out(
            [
                "tmux",
                "display-message",
                "-p",
                "-t",
                target,
                SEP.join(
                    ["#{window_name}", "#{pane_current_command}", "#{pane_current_path}"]
                ),
            ]
        ).strip()
        wname, cmd, path = (winfo.split(SEP) + ["", "", ""])[:3]

        tail = ""
        for l in reversed(out(["tmux", "capture-pane", "-p", "-t", target]).splitlines()):
            if l.strip():
                tail = " ".join(l.split())
                break

        sessions.append(
            {
                "name": name,
                "windows": int(windows or 0),
                "attached": int(attached or 0) > 0,
                "activity": int(activity or 0),
                "group": group,
                "wname": wname,
                "cmd": cmd,
                "path": path,
                "git": git_info(path),
                "tail": tail,
            }
        )
    return sessions


def rel_time(ts):
    d = max(0, int(time.time()) - ts)
    if d < 60:
        return f"{d}s ago"
    if d < 3600:
        return f"{d // 60}m ago"
    if d < 86400:
        return f"{d // 3600}h ago"
    return f"{d // 86400}d ago"


# ── drawing ─────────────────────────────────────────────────────────────────

def init_colors():
    curses.use_default_colors()
    ext = curses.has_colors() and curses.COLORS >= 256

    def mk(pid, ext_fg, base_fg, extra=0):
        curses.init_pair(pid, ext_fg if ext else base_fg, -1)
        return curses.color_pair(pid) | extra

    A["accent"] = mk(1, 45, curses.COLOR_CYAN)                        # selection
    A["green"] = mk(2, 114, curses.COLOR_GREEN)                       # clean / attached
    A["yellow"] = mk(3, 179, curses.COLOR_YELLOW)                     # dirty
    A["text"] = mk(4, 252, -1)                                        # primary text
    A["grey"] = mk(5, 246, -1, 0 if ext else curses.A_DIM)            # secondary
    A["dim"] = mk(6, 241, -1, 0 if ext else curses.A_DIM)             # tertiary
    A["border"] = mk(7, 238, -1, 0 if ext else curses.A_DIM)          # card frame


def draw_card(scr, s, idx, y, x, w, selected, scr_h):
    border = (A["accent"] | curses.A_BOLD) if selected else A["border"]

    def put(dy, col, text, attr=0):
        yy = y + dy
        if 0 <= yy < scr_h and 0 <= col < w:
            try:
                scr.addnstr(yy, x + col, text, w - col, attr)
            except curses.error:
                pass

    # top border carries the title:  ╭╴name ●╶──────╮
    put(0, 0, "╭╴", border)
    title = ell(s["name"], w - 12)
    name_attr = curses.A_BOLD | (A["accent"] if selected else A["text"])
    put(0, 2, title, name_attr)
    col = 2 + len(title)
    if s["attached"]:
        put(0, col, " ●", A["green"])
        col += 2
    put(0, col, "╶" + "─" * max(0, w - 2 - col) + "╮", border)

    # side walls
    for dy in range(1, CARD_H - 1):
        put(dy, 0, "│", border)
        put(dy, w - 1, "│", border)

    # bottom border carries the quick-jump digit:  ╰────╴3╶─╯
    if idx < 9:
        put(CARD_H - 1, 0, "╰" + "─" * (w - 6) + "╴", border)
        put(CARD_H - 1, w - 4, str(idx + 1), A["dim"])
        put(CARD_H - 1, w - 3, "╶─╯", border)
    else:
        put(CARD_H - 1, 0, "╰" + "─" * (w - 2) + "╯", border)

    left = 3
    iw = w - left - 2

    def puti(dy, text, attr=0, col=0):
        if col < iw:
            put(dy, left + col, ell(text, iw - col), attr)

    # 1 — windows · activity · group
    meta = f"{s['windows']} win · {rel_time(s['activity'])}"
    if s["group"]:
        meta += f" · ⧉ {s['group']}"
    puti(1, meta, A["grey"])

    # 2 — git branch state, or the working directory
    g = s["git"]
    if g:
        suffix = ""
        if g["dirty"]:
            suffix += f" ±{g['dirty']}"
        if g["ab"]:
            suffix += f" {g['ab']}"
        state = ell(f"⎇ {g['branch']}", iw - len(suffix)) + suffix
        puti(2, state, A["yellow"] if g["dirty"] else A["green"])
    else:
        puti(2, tilde(s["path"]), A["grey"])

    # 3 — last commit as the project's "latest update", age right-aligned
    if g and g["subject"]:
        when = g["when"]
        wcol = max(0, iw - len(when))
        puti(3, ell(g["subject"], wcol - 1), A["text"])
        puti(3, when, A["dim"], wcol)
    else:
        puti(3, s["tail"], A["dim"])

    # 4 — what's running right now
    running = f"▸ {s['wname']}"
    if s["cmd"] and s["cmd"] != s["wname"]:
        running += f" · {s['cmd']}"
    puti(4, running, A["grey"])


def draw_chrome(scr, n, w, h):
    try:
        scr.addnstr(0, 2, "tmux deck", min(w - 3, 10), curses.A_BOLD | A["text"])
        count = f"· {n} session{'s' if n != 1 else ''}"
        scr.addnstr(0, 12, count, max(0, w - 14), A["grey"])
    except curses.error:
        pass
    hints = "←↑↓→ move   ↵ attach   1-9 jump   x kill   r refresh   q quit"
    try:
        scr.addnstr(h - 1, max(0, (w - len(hints)) // 2), hints, w - 1, A["dim"])
    except curses.error:
        pass


def confirm(scr, msg):
    h, w = scr.getmaxyx()
    try:
        scr.addnstr(h - 1, 0, msg.center(w - 1), w - 1, A["yellow"] | curses.A_REVERSE)
    except curses.error:
        pass
    scr.refresh()
    return scr.getch() in (ord("y"), ord("Y"))


# ── main loop ───────────────────────────────────────────────────────────────

def run(scr):
    curses.curs_set(0)
    init_colors()
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    curses.mouseinterval(200)
    scr.keypad(True)

    sessions = get_sessions()
    sel, off = 0, 0
    stride_y = CARD_H + ROW_GAP

    while True:
        if not sessions:
            return None
        sel = max(0, min(sel, len(sessions) - 1))

        h, w = scr.getmaxyx()
        n = len(sessions)
        ncols = max(1, min((w - 2 + COL_GAP) // (MIN_CARD_W + COL_GAP), n))
        card_w = min(MAX_CARD_W, (w - 2 - (ncols - 1) * COL_GAP) // ncols)
        grid_w = ncols * card_w + (ncols - 1) * COL_GAP
        x0 = max(1, (w - grid_w) // 2)
        y0 = 2
        nrows = math.ceil(n / ncols)
        view_h = h - 1 - y0

        sel_top = (sel // ncols) * stride_y
        if sel_top < off:
            off = sel_top
        if sel_top + CARD_H > off + view_h:
            off = sel_top + CARD_H - view_h
        off = max(0, min(off, max(0, nrows * stride_y - ROW_GAP - view_h)))

        scr.erase()
        draw_chrome(scr, n, w, h)

        boxes = []
        for i, s in enumerate(sessions):
            r, c = divmod(i, ncols)
            y = y0 + r * stride_y - off
            x = x0 + c * (card_w + COL_GAP)
            boxes.append((y, x, CARD_H, card_w))
            if y + CARD_H > y0 - 1 and y < h - 1:
                draw_card(scr, s, i, y, x, card_w, i == sel, h - 1)
        scr.refresh()

        ch = scr.getch()
        if ch in (ord("q"), 27):
            return None
        elif ch in (curses.KEY_ENTER, 10, 13):
            return sessions[sel]["name"]
        elif ord("1") <= ch <= ord("9"):
            i = ch - ord("1")
            if i < n:
                return sessions[i]["name"]
        elif ch == curses.KEY_LEFT:
            sel = max(0, sel - 1)
        elif ch == curses.KEY_RIGHT:
            sel = min(n - 1, sel + 1)
        elif ch == curses.KEY_UP:
            if sel - ncols >= 0:
                sel -= ncols
        elif ch == curses.KEY_DOWN:
            if sel + ncols < n:
                sel += ncols
        elif ch == ord("r"):
            sessions = get_sessions()
        elif ch == ord("x"):
            name = sessions[sel]["name"]
            if confirm(scr, f"kill session '{name}'?  y/N"):
                sh(["tmux", "kill-session", "-t", f"={name}"])
                sessions = get_sessions()
        elif ch == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except curses.error:
                continue
            hit = None
            for i, (by, bx, bh, bw) in enumerate(boxes):
                if by <= my < by + bh and bx <= mx < bx + bw:
                    hit = i
                    break
            if hit is None:
                continue
            if bstate & curses.BUTTON1_DOUBLE_CLICKED:
                return sessions[hit]["name"]
            if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                if hit == sel:
                    return sessions[hit]["name"]
                sel = hit


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"tmux-deck {__version__}")
        return
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__.strip())
        print("\nusage: tmux-deck [--version]")
        return
    if not out(["tmux", "list-sessions", "-F", "#{session_name}"]).strip():
        print("No tmux sessions are running.", file=sys.stderr)
        sys.exit(1)
    name = curses.wrapper(run)
    if not name:
        sys.exit(0)
    if os.environ.get("TMUX"):
        os.execvp("tmux", ["tmux", "switch-client", "-t", f"={name}"])
    else:
        os.execvp("tmux", ["tmux", "attach-session", "-t", f"={name}"])


if __name__ == "__main__":
    main()
