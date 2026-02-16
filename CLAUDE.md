# Frida GEO - Claude Instructions

## Compound Engineering Workflow Guide

### The Loop (For Each Task)

```
/plan → /work → /review → /triage → /resolve_todo_parallel → /compound
```

### Commands Reference

| Step | Command | What It Does |
|------|---------|--------------|
| 1 | `/compound-engineering:workflows:plan "Task description"` | 3 research agents in parallel → creates `plans/<title>.md` |
| 2 | `/compound-engineering:workflows:work plans/<file>.md` | Executes plan with TodoWrite tracking → code + PR |
| 3 | `/compound-engineering:workflows:review latest` | 10+ review agents in parallel → creates `todos/*.md` |
| 4 | `/compound-engineering:triage` | Walk through findings one-by-one (yes/next/custom) |
| 5 | `/compound-engineering:resolve_todo_parallel` | Fix all approved todos in parallel |
| 6 | `/compound-engineering:workflows:compound` | Document learnings → `docs/solutions/*.md` |

### Quick Version (What to Say)

```
"Plan Task N from docs/poc-task-list-AGENT.md"
"Work on that plan"
"Review this"
"Triage"
"Resolve the todos"
"Commit"
"Document this" (if you learned something)
```

### Detail Levels for /plan

| Level | Use For |
|-------|---------|
| **MINIMAL** | Simple bugs, small improvements |
| **MORE** | Most features, team collaboration |
| **A LOT** | Major features, architectural changes |

### What Each Command Creates

```
/plan    → plans/<task-title>.md
/review  → todos/001-pending-p1-*.md, 002-pending-p2-*.md, ...
/triage  → todos/*-ready-*.md (approved) or deleted (skipped)
/resolve → todos/*-complete-*.md
/compound → docs/solutions/<category>/<filename>.md
```

### Priority Levels

| Priority | Meaning | Action |
|----------|---------|--------|
| P1 | CRITICAL - blocks merge | Must fix |
| P2 | Important - should fix | Fix before shipping |
| P3 | Nice-to-have | Optional |

### POC Phase Checkpoints

| Phase | After Tasks | Check |
|-------|-------------|-------|
| 1 | 1-3 | `pytest` passes, health endpoint works |
| 2 | 4-11 | All tools registered, RLS working |
| 3 | 12-15 | UI renders, SSE streaming works |
| 4 | 17-25 | Dashboard pages functional |
| 5 | 26-30 | Full integration working |

### Philosophy

> Each unit of engineering work should make subsequent units easier.

- `/plan` prevents blank-page syndrome
- `/review` catches issues before they ship
- `/compound` means you never solve the same bug twice

---

## Gemini CLI Offloading

Offload heavy analysis tasks to Gemini CLI to leverage its 1M+ token context window.

### Setup

```bash
npm install -g @google/gemini-cli
# Add GEMINI_API_KEY to .env (get from aistudio.google.com/apikey)
```

### Usage Pattern (Serial - Recommended)

```bash
# Analyze a file
source .env && gemini -m gemini-3-flash-preview "Analyze for security issues" < src/api.py

# Review with output to file
source .env && gemini -m gemini-3-flash-preview "Review for performance" < src/large-file.py > /tmp/review.md

# Filter debug output
source .env && gemini -m gemini-3-flash-preview "Your prompt" < file.py 2>&1 | grep -v "^\[" | grep -v "^Server"
```

**Always use `-m gemini-3-flash-preview`** - it's the latest and fastest model.

### When to Offload to Gemini

| Task | Why Offload |
|------|-------------|
| Large file analysis (500+ lines) | Gemini has 1M+ token context |
| Bulk code review | Process many files in sequence |
| Documentation generation | Repetitive, well-defined task |
| Security audits | Thorough analysis with fresh perspective |

### Example Workflow

```
User: "Review src/api.py for security issues"

Claude:
1. source .env && gemini -m gemini-3-flash-preview "Review for security issues, output markdown" < src/api.py > /tmp/security-review.md
2. Read /tmp/security-review.md
3. Summarize findings and create todos
```

### Important Notes

- **Serial execution recommended** - Claude waits ~5s between background checks, negating parallelism benefits
- **Background only when Claude has independent work** - Use `&` suffix only if Claude can do other tasks meanwhile
- **Always `source .env`** - GEMINI_API_KEY must be loaded before each call
- **Filter startup logs** - Use `grep -v "^\["` to remove debug output
