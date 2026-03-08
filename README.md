# fixdrift

`fixdrift` is a Speedrift-suite sidecar for **root-cause fix quality drift**.

It flags bug-fix tasks that appear to stack patches without durable evidence:
- missing reproduction notes
- missing root-cause notes
- missing regression test evidence
- unresolved fix-related follow-up buildup

## Ecosystem Map

This project is part of the Speedrift suite for Workgraph-first drift control.

- Spine: [Workgraph](https://graphwork.github.io/)
- Orchestrator: [driftdriver](https://github.com/dbmcco/driftdriver)
- Baseline lane: [coredrift](https://github.com/dbmcco/coredrift)
- Optional lanes: [specdrift](https://github.com/dbmcco/specdrift), [datadrift](https://github.com/dbmcco/datadrift), [depsdrift](https://github.com/dbmcco/depsdrift), [uxdrift](https://github.com/dbmcco/uxdrift), [therapydrift](https://github.com/dbmcco/therapydrift), `fixdrift`, [yagnidrift](https://github.com/dbmcco/yagnidrift), [redrift](https://github.com/dbmcco/redrift)

## Task Spec Format

Add a per-task fenced TOML block:

````md
```fixdrift
schema = 1
min_open_fix_followups = 2
followup_prefixes = ["drift-harden-", "drift-scope-", "drift-therapy-", "drift-fix-"]
require_repro_log = true
repro_markers = ["Repro:", "Reproduction:"]
require_root_cause_log = true
root_cause_markers = ["RootCause:", "RCA:"]
require_regression_signal = true
regression_markers = ["RegressionTest:", "Added regression test:"]
regression_test_globs = ["tests/**", "**/*test*.py", "**/*.test.*", "**/*.spec.*"]
ignore_log_prefixes = ["Fixdrift:"]
```
````

## Workgraph Integration

From a Workgraph repo (where `driftdriver install` has written wrappers):

```bash
./.workgraph/drifts check --task <id> --write-log --create-followups
```

Standalone:

```bash
/path/to/fixdrift/bin/fixdrift --dir . wg check --task <id> --write-log --create-followups
```

Exit codes:
- `0`: clean
- `3`: findings exist (advisory)

## Agent Guidance

This section is for AI agents (Claude Code, Codex, Amplifier) working in Speedrift-managed repos.

### When This Lane Runs

`fixdrift` runs automatically when a task description contains a `fixdrift` TOML block (bug-fix tasks). It is also triggered by `driftdriver` during factory cycles and attractor loop passes.

### Per-Task Workflow

1. Add a `fixdrift` fence to bug-fix tasks to ensure reproduction notes, root-cause analysis, and regression test evidence
2. Run drift checks at task start and before completion:
   ```bash
   ./.workgraph/drifts check --task <id> --write-log --create-followups
   ```
3. Drift is advisory — never hard-block the current task
4. If findings appear, prefer follow-up tasks over scope expansion

### Key Rules

- Exit code `0` = clean, `3` = findings exist (advisory)
- Follow-up tasks are deduped and capped at 3 per lane per repo
- Do not suppress findings — let driftdriver manage significance scoring
- fixdrift flags patches that lack durable evidence (repro notes, root cause, regression tests)
- Always document reproduction steps before fixing
- Regression tests should be committed alongside the fix
- Do not close fix follow-ups without evidence artifacts
