# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repository Purpose

This repo is a **Claude Code configuration backup** for cross-machine restoration. It mirrors the canonical project at `PorscheWen/ClaudeCode` and tracks:

- `claude-backup/settings.json` — Global Claude Code permissions and UI settings
- `claude-backup/skills/` — Custom slash-command skills (`/stock-advisor`, etc.)
- `claude-backup/memory/` — Persistent memory files (user profile, feedback preferences)
- `claude-backup/CLAUDE.md` — User preferences / tool inventory (deployed to project directory on restore)
- `claude-backup/statusline-command.sh` — Custom status-bar script (Python-based, reads JSON from stdin)
- `claude-backup/setup.ps1` — Windows PowerShell restore script
- `run_claude.py` — Interactive Claude CLI chatbot (uses prompt caching on the system prompt)
- `example.py` — Minimal Claude API usage example
- `requirements.txt` — Python dependencies (`anthropic>=0.94.0`, `python-dotenv>=1.0.0`)
- `.env.example` — Environment variable template (copy to `.env` and fill in secrets)

All secrets (API keys, tokens, passwords) live in `.env` — never tracked.

---

## Restoration Workflow (Windows)

Run `setup.ps1` from inside the `claude-backup/` directory in PowerShell:

```powershell
.\claude-backup\setup.ps1 -ProjectPath "C:\Users\BaoGo\Documents\ClaudeCode"
```

What the script does (in order):
1. Creates `~/.claude/skills/stock-advisor/` and the project memory directory
2. Copies `settings.json` and `statusline-command.sh` to `~/.claude/`
3. Copies `skills/stock-advisor/SKILL.md` to `~/.claude/skills/stock-advisor/`
4. Copies all `memory/*.md` files to `~/.claude/projects/<project-slug>/memory/`
5. Copies `CLAUDE.md` to the project directory **only if it does not already exist**
6. Copies `run_claude.py`, `example.py`, `requirements.txt`, `.env.example` to the project directory (skips existing files)

After running:
```powershell
cd C:\Users\BaoGo\Documents\ClaudeCode
pip install -r requirements.txt
cp .env.example .env   # then fill in your secrets
```

Then restart Claude Code.

---

## Python Scripts

### `run_claude.py` — Interactive CLI
Starts a terminal chat session with Claude. Uses `cache_control: ephemeral` on the system prompt to reduce token costs on repeated turns.

```bash
python run_claude.py
```

Requires `ANTHROPIC_API_KEY` in `.env`. Model: `claude-sonnet-4-6`, max 2048 tokens per turn.

### `example.py` — One-shot API example
Sends a single greeting message and prints the response + token usage. Uses `claude-3-5-sonnet-20241022`.

```bash
python example.py
```

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
│   ├── user_profile.md     ← professional background (SQA, 13yr)
│   ├── feedback_response_style.md   ← numbered continuation options
│   ├── feedback_git_push.md         ← auto-push after every commit
│   └── line_api_credentials.md     ← LINE bot connection info
└── skills/
    └── stock-advisor/
        └── SKILL.md        ← triggered by stock queries; yfinance + TWSE API
```

---

## Key Conventions

### Memory files
Each file under `memory/` uses YAML frontmatter (`name`, `description`, `type`, `originSessionId`) followed by Markdown content. The index `memory/MEMORY.md` must be updated whenever a file is added or removed.

### Skills
Each skill lives in `skills/<name>/SKILL.md`. The frontmatter `description` field defines the trigger phrases Claude uses to auto-invoke the skill. At runtime, skills are installed to `~/.claude/skills/`.

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

## Integrated Tools (from `claude-backup/CLAUDE.md`)

| Tool | Purpose | Credentials |
|------|---------|-------------|
| Notion | Salary records, personal DB | `NOTION_TOKEN` in `.env` |
| LINE What_To_Eat Bot | Lunch recommendation bot | `LINE_CHANNEL_SECRET`, `LINE_ACCESS_TOKEN` in `.env` |
| LINE Memo Bot | Personal assistant bot | `MEMO_BOT_CHANNEL_SECRET`, `MEMO_BOT_ACCESS_TOKEN` in `.env` |
| Google Workspace MCP | Gmail search, Drive files | Configured in Claude Code MCP settings |

---

## What Is NOT Tracked

- `.env` — all API tokens and secrets
- `*.pdf`, `*.png`, `*.jpg` — payslips and screenshots
- `__pycache__/`, `*.pyc`
