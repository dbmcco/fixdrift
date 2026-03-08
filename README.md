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
