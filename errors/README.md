# Error Runbooks (`fixos`)

Index of error runbooks and diagnostic remediation guides for `semcod/fixos` in accordance with `wellmanifest/logs`.

| Code | Component | Summary | Remediation |
| --- | --- | --- | --- |
| `FIXOS-LLM-001` | `fixos.cli.fix_cmd` / `fixos.agent` | LLM provider unavailable or `--no-llm` active during autonomous repair | Automatic fallback to deterministic heuristic diagnostics and safe cleanup (`fixos auto --no-llm`) |
| `FIXOS-DISK-001` | `fixos.cli._cleanup_space` | Low disk space on `/` or `/tmp` | Run `fixos auto --no-llm --yes` or `fixos cleanup-space --yes` |
| `FIXOS-SNAP-001` | `fixos.agent.autonomous_session` | Disabled Snap revisions consuming root disk space | Remove disabled Snap revisions via `snap list --all` and `sudo -n snap remove <pkg> --revision=<rev>` |
