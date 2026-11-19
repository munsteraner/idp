# idp

Document parsing first, schema extraction second. Step one: find the best open-weight way to turn PDFs into faithful structured content (text, tables, forms, charts, positions), measured on ParseBench 2. Step two, once parsing is good: fill user schemas from the parsed result, measured on ExtractBench. Everything runs on the PALMA II cluster.

## Start here

1. `STATUS.md`: where the work stands and what is next. Update it at the end of every working session and whenever a job is submitted or finishes.
2. `PRD.md`: the plan. Section 8 holds the user's standing limits, section 9a the research loop.
3. `DECISIONS.md`: every deviation from the PRD, with evidence.
4. `.claude/skills/palma/SKILL.md`: how to use the cluster. All cluster access goes through `palma.py`.

## Rules

- Open-weight models on PALMA II GPUs only. No paid APIs (decided 2026-11-19: too expensive for iteration).
- Public datasets only.
- No benchmark runs on the laptop (14 GB RAM); they run as Slurm jobs.
- Scores come from the official harness (ParseBench and ExtractBench scorers in one package), pinned in `pyproject.toml`. Never reshape model output before scoring, never edit the scorer.
- Jobs run from a committed code snapshot (`palma.py sync`), so commit before submitting.
- Secrets live in `.env` (git-ignored) and on PALMA in `/scratch/tmp/$USER/idp/.env`. Never print them.
- State belongs in files, not in chat: results, decisions and status must survive a cleared conversation.

## Commands

- `uv run pytest -q`: tests.
- `uv run idp-bench pipelines`: list pipelines (the official `extract-bench` CLI plus ours).
- `.claude/skills/palma/palma.py status`: jobs, GPU-hours used today, free GPUs.
