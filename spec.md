# logscope — CLI Log Summarizer Spec

## 1. Purpose

Quick command-line tool to summarize application logs after an incident, without
opening a dashboard. Targets large (100 MB+) single-file application logs.

## 2. Commands

### 2.1 `logscope summary <file>`
Reports:
- Line counts by level (INFO / WARN / ERROR, plus any other levels encountered)
- Top 5 most frequent error messages (by exact message text, ERROR/FATAL/CRITICAL levels)
- First and last timestamp seen in the file
- Total lines read and count of malformed/skipped lines

### 2.2 `logscope timeline <file> --bucket 15m`
- Buckets ERROR-level entries into fixed-size time windows (`--bucket`, e.g. `30s`,
  `15m`, `2h`, `1d`)
- Renders a text bar chart of error count per bucket (`text` format), or structured
  bucket list (`json`/`md`)
- Empty buckets between the first and last observed bucket are shown as zero (no gaps)

### 2.3 `logscope grep <file> --level ERROR --since "2026-10-01 09:00" [--until ...]`
- Streams and filters log entries by level (comma-separated list allowed, e.g.
  `ERROR,WARN`) and/or by timestamp range (`--since`, `--until`)
- Prints matching entries (including any attached multi-line continuation, e.g.
  stack traces)
- Reports count of matches and malformed lines skipped

## 3. Global Options (every command)

| Option | Values | Behavior |
|---|---|---|
| `--format` | `text` (default) \| `json` \| `md` | Output rendering |
| `--output`, `-o` | file path | Destination file. For `md`, defaults to `<logfile>_<command>_report.md` in the current directory if not given. For `text`/`json`, prints to stdout unless given. |
| `--encoding` | e.g. `utf-8` | Input file encoding (default `utf-8`) |
| `--errors` | `strict`\|`replace`\|`ignore` | Decoding error policy (default `replace`) |

`--format md` always writes a report file (never prints the report body to stdout);
it prints only a short confirmation line with the written path.

## 4. Log Line Format (assumption)

Since no concrete log format was supplied, logscope expects (and is built around)
a line-oriented format of:

```
<timestamp> <LEVEL> <message...>
```

- `<timestamp>`: `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DDTHH:MM:SS`, optional
  `.mmm`/`,mmm` fractional seconds.
- `<LEVEL>`: one of `TRACE, DEBUG, INFO, WARN, WARNING, ERROR, FATAL, CRITICAL`
  (case-insensitive). `WARNING` is normalized to `WARN`.
- Optional separator after the level: `:`, `-`, or `|`.
- Everything after is the message.

Example:
```
2026-10-01 09:00:03 ERROR Payment gateway timeout: order=1234
2026-10-01 09:00:03 ERROR   at PaymentClient.call(PaymentClient.java:88)
2026-10-01 09:00:03 ERROR   at OrderService.pay(OrderService.java:40)
```

A line that does **not** start with `<timestamp> <LEVEL>` is treated as a
**continuation** of the previous log entry (e.g. a stack trace) if a previous
entry exists on the current parse pass; otherwise it is **malformed**.

## 5. Malformed Line Handling

- Blank/whitespace-only lines are skipped silently (not counted as malformed).
- Any non-blank line that cannot be attributed to a header or a continuation of a
  preceding entry is counted in `malformed_lines` and skipped — it never raises
  an exception or aborts processing.
- A line with a valid header shape but an unparsable timestamp is also counted as
  malformed.
- Malformed counts are reported in every command's output.

## 6. Memory / Performance Constraint

- The file is read strictly line-by-line via buffered streaming I/O; it is never
  loaded fully into memory (`.read()`/`.readlines()` are not used).
- Aggregates kept in memory are bounded by the *distinct* values seen (level
  counts, distinct error messages, time buckets), not by file size or line count.
- `grep` output is streamed directly to stdout or the output file as matches are
  found; results are not buffered into a list before printing/writing.
- Must handle a 100 MB input file without excessive memory growth.

## 7. Output Formats

### `text` (default)
Human-readable: tables/lists for `summary`, ASCII bar chart for `timeline`, raw
matched lines for `grep`.

### `json`
Machine-readable structured document (object), e.g. for `summary`:
```json
{
  "file": "app.log",
  "total_lines": 102345,
  "malformed_lines": 3,
  "counts_by_level": {"ERROR": 12, "INFO": 1000, "WARN": 45},
  "top_errors": [{"message": "Payment gateway timeout", "count": 7}],
  "first_timestamp": "2026-10-01T08:55:00",
  "last_timestamp": "2026-10-01T10:02:11"
}
```
`grep --format json` streams a JSON object with a `matches` array plus trailing
stats, written incrementally.

### `md`
Markdown report, always written to a file (see `--output` rule above): headings,
tables, and a fenced-code-block bar chart for `timeline`.

## 8. Non-Goals / Out of Scope

- No live/follow mode (`tail -f` style).
- No dashboard/UI, no charts beyond text bar charts.
- No log format auto-detection beyond the single assumed format above (documented
  so it can be extended later, e.g. JSON-lines logs).
- No multi-file input in this version.

## 9. Proposed Project Layout

```
pyproject.toml              # packaging, console_script entry point "logscope"
logscope/
  __init__.py
  cli.py                    # argparse wiring, dispatch
  timeutil.py                # timestamp / duration parsing
  parsing.py                 # streaming line -> LogEntry parser, malformed tracking
  commands/
    summary.py
    timeline.py
    grep.py
  output.py                  # text/json/md renderers, report file helpers
tests/
  fixtures/sample.log
  test_parsing.py
  test_summary.py
  test_timeline.py
  test_grep.py
README.md
spec.md
```

## 10. Acceptance Checklist

- [ ] `logscope summary app.log` prints level counts, top 5 errors, first/last ts
- [ ] `logscope timeline app.log --bucket 15m` prints a bucketed bar chart
- [ ] `logscope grep app.log --level ERROR --since "2026-10-01 09:00"` filters correctly
- [ ] `--format json` and `--format md` work for all three commands
- [ ] `--format md` writes a report file and does not dump the body to stdout
- [ ] 100 MB file processes without loading it fully into memory
- [ ] Malformed lines are counted, reported, and never crash the tool
