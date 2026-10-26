# Project Instructions — log-analysis-cli (logscope)

These are persistent instructions for aXet.code when working in this repository.
See `spec.md` for the full functional specification; this file is about *how*
to build and work on it.

## What this project is

A Python CLI tool, `logscope`, that summarizes application logs after an
incident without needing a dashboard. Three subcommands: `summary`,
`timeline`, `grep`. Full behavior is defined in `spec.md` — always check it
before implementing or changing a command's behavior, and keep it in sync if
behavior changes.

## Tech stack / conventions

- Language: Python (>= 3.8 compatible), stdlib only unless a dependency is
  explicitly approved — this is a lightweight CLI, avoid adding heavy deps.
- Packaging: `pyproject.toml` with a `logscope` console-script entry point.
- CLI parsing: `argparse` (subparsers for `summary` / `timeline` / `grep`).
- Layout (see `spec.md` §9 for the authoritative version):
  ```
  logscope/
    cli.py            # argparse wiring, dispatch
    timeutil.py        # timestamp / duration parsing
    parsing.py         # streaming line -> LogEntry parser, malformed tracking
    commands/           # summary.py, timeline.py, grep.py
    output.py           # text/json/md renderers
  tests/
  ```

## Hard constraints (do not violate)

- **Streaming only**: never read the whole log file into memory
  (`.read()`/`.readlines()` on the full file are forbidden). Iterate the file
  object line-by-line with buffered I/O. Any in-memory aggregate must be
  bounded by distinct values (levels, error messages, time buckets), not by
  file size. This must still hold for a 100 MB input file.
- **Malformed lines never crash the tool**: wrap per-line parsing so any
  unparsable line is counted in a malformed-line counter and skipped, not
  raised. No command should ever throw an unhandled exception because of bad
  input data in the log file itself.
- **`--format json|md` on every command**: all three subcommands must support
  `text` (default), `json`, and `md`. `md` always writes a report file (never
  prints the full report body to stdout — just a short confirmation of the
  written path).

## Build / test / run commands

Fill these in as the project is scaffolded (keep this section up to date):
- Install (editable): `pip install -e .`
- Run: `logscope summary app.log` (or `python -m logscope ...` before install)
- Tests: `pytest`
- Lint/typecheck: none configured yet — don't add linters/formatters unless
  asked.

## Testing expectations

- Unit tests for the streaming parser (`parsing.py`) must include: valid
  lines, multi-line stack-trace continuations, and malformed lines (assert
  they're counted, not raised).
- Add a small fixture log under `tests/fixtures/` covering INFO/WARN/ERROR
  lines, at least one multi-line error, and at least one malformed line.
- For the 100 MB streaming constraint, prefer a test that generates a large
  temp file and asserts memory stays bounded (or at minimum, asserts the
  parser never calls `.readlines()`/`.read()` by construction/review) rather
  than committing a 100 MB fixture to the repo.

## Working agreements

- Keep `spec.md` as the source of truth for *behavior*; keep this file as the
  source of truth for *how to build/test*. Update both together when scope
  changes.
- No dashboard/UI/live-follow mode — out of scope per `spec.md` §8.
- Don't add formatters, linters, or CI config unless explicitly requested.
