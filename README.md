# logscope

Quick CLI to summarize application logs after an incident — no dashboard required.

See `spec.md` for the full functional specification.

## Install

```
pip install -e .
```

## Usage

```
logscope summary app.log
logscope timeline app.log --bucket 15m
logscope grep app.log --level ERROR --since "2026-10-01 09:00"
```

Add `--format json` or `--format md` to any command. `md` always writes a
report file instead of printing to stdout.
