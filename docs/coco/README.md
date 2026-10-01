# CoCo evidence pack

The PS1 brief requires CoCo to be used across the full lifecycle, and that
*"judges will look for evidence of it at every stage."* This directory is that
evidence. Nothing here is written after the fact - every transcript is CoCo's
own record of a real session.

## Verifying this yourself

CoCo persists every session. Any transcript here can be re-derived on a machine
with this project's connection:

```
cortex conversations list
cortex conversations transcript <session-id>
```

`transcripts/session-<uuid>.txt` files are verbatim exports of exactly that.

## Phase coverage

| Phase | Document | Sessions |
|---|---|---|
| 1 · Planning | [01-planning.md](01-planning.md) | `2d46d885` |
| 2 · Development | [02-development.md](02-development.md) | `dbfd0f33`, `bf873376`, `1c1f3daa`, `22d50ebb`, `c6fc48ed`, `9bc3452c`, `0fe59759` |
| 3 · Execution | *pending* | - |
| 4 · Testing & validation | [04-validation.md](04-validation.md) | `f0b21309`, `ce256aab`, `06-audit` |

`prompts/` holds the verbatim prompt given to CoCo for each session, so the
instruction and the result can be read side by side.

## Why some sessions failed

Three sessions did not complete what they were asked. They are kept, not pruned.

| Session | What happened | How it was caught | Resolution |
|---|---|---|---|
| `dbfd0f33` | Exceeded its invocation window; the calling shell lost stdout | Follow-up query found RAW tables empty | Transcript intact (23 KB); load re-run in `1c1f3daa` |
| `bf873376` | Backgrounded invocation terminated before executing the load | Same | Superseded by `1c1f3daa` |
| `9bc3452c` | Wrote all three SQL files and reported success, having created 2 of 5 GOLD objects and 0 DMFs | Audit session `ce256aab` queried Snowflake directly | Completed by `0fe59759` |

The pattern across all three: **the agent's own summary said success; the
database said otherwise.** Every claim in this project is therefore verified by
querying Snowflake, never by reading a transcript.

That discipline caught two further issues worth recording:

- A generator that declared itself deterministic while minting IDs with
  `uuid.uuid4()`, which ignores `random.seed()` - silently invalidating the
  held-out answer key. See [02-development.md](02-development.md).
- An audit that produced two **false failures** of its own: it looked for data
  metric functions *defined in* `PAPERTRAIL` (the attached ones are
  system-defined `SNOWFLAKE.CORE.*`, so none were visible), and it counted NULL
  foreign keys as orphans. Re-querying with
  `INFORMATION_SCHEMA.DATA_METRIC_FUNCTION_REFERENCES` found all 17 attachments,
  and the true orphan count is 0. See [04-validation.md](04-validation.md).

A verification step that can itself be wrong is worth saying out loud.
