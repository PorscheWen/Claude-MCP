# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Purpose

This repo is a **Claude Code configuration backup** for cross-machine restoration. It tracks:

- `claude-backup/settings.json` — Global Claude Code permissions and UI settings
- `claude-backup/skills/` — Custom slash-command skills (`/stock-advisor`, etc.)
- `claude-backup/memory/` — Persistent memory files (user profile, feedback preferences)
- `claude-backup/CLAUDE.md` — User preferences / tool inventory (deployed to project directory on restore)
- `claude-backup/statusline-command.sh` — Custom status-bar script (Python-based, reads JSON from stdin)
- `claude-backup/setup.ps1` — Windows PowerShell restore script

The root `CLAUDE.md` (this file) documents the repository itself and is tracked in version control. Sensitive runtime tokens live in `C:\Users\BaoGo\Documents\ClaudeCode\.env` (not tracked).

---

## Restoration Workflow (Windows)

Run `setup.ps1` from the repo root in PowerShell:

```powershell
.\claude-backup\setup.ps1 -ProjectPath "C:\Users\BaoGo\Documents\ClaudeCode"
```

What the script does (in order):
1. Creates `~/.claude/skills/stock-advisor/` and the project memory directory
2. Copies `settings.json` and `statusline-command.sh` to `~/.claude/`
3. Copies `skills/stock-advisor/SKILL.md` to `~/.claude/skills/stock-advisor/`
4. Copies all `memory/*.md` files to `~/.claude/projects/<project-slug>/memory/`
5. Copies `CLAUDE.md` to the project directory **only if it does not already exist** (avoids overwriting customizations)

After running, restart Claude Code.

---

## Directory Layout

```
claude-backup/
├── CLAUDE.md               ← user prefs + tool inventory (deployed to project dir)
├── settings.json           ← global Claude Code settings
├── statusline-command.sh   ← status bar: model name, context %, rate-limit timers
├── setup.ps1               ← restoration entry point
├── memory/
│   ├── MEMORY.md           ← index of memory files
│   ├── user_profile.md     ← background / professional context
│   ├── feedback_response_style.md
│   ├── feedback_git_push.md
│   └── line_api_credentials.md
└── skills/
    └── stock-advisor/
        └── SKILL.md        ← triggered by stock-related queries; uses yfinance + TWSE API
```

---

## Key Conventions

### Memory files
Each file under `memory/` uses YAML frontmatter (`name`, `description`, `type`, `originSessionId`) followed by Markdown content. The index `memory/MEMORY.md` must be updated whenever a file is added or removed.

### Skills
Each skill lives in `skills/<name>/SKILL.md`. The frontmatter `description` field defines the trigger phrases Claude uses to auto-invoke the skill.

### Permissions (settings.json)
`defaultMode` is `bypassPermissions`. The `deny` list explicitly blocks destructive shell commands (`rm -rf`, `git reset --hard`, `git push --force`, `sudo`, `shutdown`, etc.). Do not remove or weaken the deny list entries.

### Language
Respond in **繁體中文 (Traditional Chinese)** by default; switch to English only when necessary.

### Git push behavior
After every commit, push automatically without prompting. If push fails due to remote changes, run `git pull --rebase` then push again — no manual confirmation needed.

### Response style
End multi-step responses with numbered continuation options so the user can reply with a number instead of retyping.

---

## Stock Advisor Skill

Triggered by phrases like "幫我看股票", "給我操作建議", or a ticker symbol with a buy/sell question. The skill:

1. Fetches 3-month OHLCV data via `yfinance` (Taiwan tickers use `.TW` suffix, e.g. `2330.TW`)
2. Calculates MA5/20/60, RSI(14), MACD, and Bollinger Bands using `pandas`
3. Queries TWSE public API for three-institution net buy/sell data
4. Searches for recent news via WebSearch
5. Outputs a structured Markdown report per ticker + a market summary

Dependencies: `pip install yfinance pandas requests`

Default watchlist is stored in `claude-backup/CLAUDE.md` under "stock-advisor 自選股清單".

---

## What Is NOT Tracked

- `.env` — all API tokens and secrets
- `CLAUDE.md` at any location other than the repo root and `claude-backup/`
- `*.pdf`, `*.png`, `*.jpg` — payslips and screenshots
- `__pycache__/`, `*.pyc`
