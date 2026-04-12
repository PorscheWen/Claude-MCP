#!/usr/bin/env bash
# Claude Code Status Line Script

input=$(cat)

result=$(echo "$input" | PYTHONIOENCODING=utf-8 python -c "
import sys, json, os, time

GREEN  = '\033[32m'
YELLOW = '\033[33m'
ORANGE = '\033[38;5;208m'
RED    = '\033[31m'
RESET  = '\033[0m'

try:
    data = json.load(sys.stdin)
except:
    print('🧋 Claude')
    sys.exit(0)

# ── 模型名稱
model = (data.get('model') or {}).get('display_name', 'Claude')

# ── Context 使用量
ctx_block = ''
used_pct = (data.get('context_window') or {}).get('used_percentage')
if used_pct is not None:
    n     = round(used_pct)
    bar   = '\u2588' * (n // 10) + '\u2591' * (10 - n // 10)
    color = GREEN if n < 50 else (YELLOW if n < 80 else ORANGE)
    ctx_block = f'{color}{bar} {n}%{RESET}'

# ── 5小時剩餘時間 + 用量
session_block = ''
five = (data.get('rate_limits') or {}).get('five_hour', {})
five_pct     = five.get('used_percentage')
five_resets  = five.get('resets_at')
if five_pct is not None and five_resets is not None:
    secs = int(five_resets - time.time())
    if secs > 0:
        hl, ml = secs // 3600, (secs % 3600) // 60
        tl   = f'{hl}H{ml}m' if hl > 0 else f'{ml}m'
        used = round(five_pct)
        c    = RED if used > 80 else (YELLOW if used > 50 else '')
        session_block = f'{c}{tl} {used}% used{RESET}' if c else f'{tl} {used}% used'

# ── 7日剩餘
seven_block = ''
seven  = (data.get('rate_limits') or {}).get('seven_day', {})
s_pct  = seven.get('used_percentage')
s_resets = seven.get('resets_at')
if s_pct is not None and s_resets is not None:
    secs = int(s_resets - time.time())
    if secs > 0:
        hl, ml = secs // 3600, (secs % 3600) // 60
        tl  = f'{hl}H{ml}m' if hl > 0 else f'{ml}m'
        used = round(s_pct)
        c    = RED if used > 80 else (YELLOW if used > 50 else '')
        seven_block = f'{c}{tl} {used}% used{RESET}' if c else f'{tl} {used}% used'

# ── 組合
parts = [f'🧋 {model}']
if ctx_block:     parts.append(ctx_block)
if session_block: parts.append(session_block)
if seven_block:   parts.append(seven_block)
print(' | '.join(parts))
" 2>/dev/null || echo "🧋 Claude")

printf "%b\n" "$result"
