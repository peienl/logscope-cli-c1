"""Verifies the streaming / bounded-memory constraint from spec.md §6:

  'Must handle a 100 MB input file without excessive memory growth.'

Rather than committing a 100 MB fixture, these tests generate a large file
on the fly (streamed to disk, never held fully in memory) and then assert
that processing it keeps peak Python-heap usage small and roughly constant
regardless of file size — i.e. memory usage is bounded by the number of
distinct aggregate keys (levels, error messages, buckets), not by file size
or line count.

These tests are marked `slow` (generating + fully processing a ~100MB /
1.5M-line file four times takes tens of minutes) and are excluded from the
default `pytest` run (see `addopts` in pyproject.toml). Run them explicitly
with `pytest -m slow tests/test_large_file_streaming.py` when you need to
re-verify the memory-bound claim, e.g. after changing the parser/commands.
"""
from __future__ import annotations

import gc
import os
import tracemalloc
from datetime import datetime, timedelta

import pytest

from logscope.commands import grep, summary, timeline
from logscope.parsing import ParseStats, iter_entries

pytestmark = pytest.mark.slow

LARGE_FILE_TARGET_BYTES = 100 * 1024 * 1024  # 100 MB
PEAK_MEMORY_CEILING_BYTES = 20 * 1024 * 1024  # generous bound for a "small" aggregate


def _generate_log(path: str, target_bytes: int) -> int:
    """Stream-write a synthetic log of roughly `target_bytes` size.

    Returns the number of ERROR-level entries written. Writing is done
    line-by-line to the file handle (never building the whole content in
    memory) to keep the *test* itself honest about memory too.
    """
    base_time = datetime(2026, 10, 1, 0, 0, 0)
    error_count = 0
    bytes_written = 0
    i = 0
    with open(path, "w", encoding="utf-8") as handle:
        while bytes_written < target_bytes:
            ts = base_time + timedelta(seconds=i)
            level = "ERROR" if i % 50 == 0 else ("WARN" if i % 10 == 0 else "INFO")
            line = f"{ts:%Y-%m-%d %H:%M:%S} {level} message number {i} of a synthetic stress log\n"
            handle.write(line)
            bytes_written += len(line)
            if level == "ERROR":
                error_count += 1
            i += 1
    return error_count


@pytest.fixture(scope="module")
def large_log_file(tmp_path_factory):
    path = tmp_path_factory.mktemp("large_log") / "large.log"
    error_count = _generate_log(str(path), LARGE_FILE_TARGET_BYTES)
    size = os.path.getsize(path)
    assert size >= LARGE_FILE_TARGET_BYTES
    return str(path), error_count, size


class TestStreamingParserIsBounded:
    def test_iter_entries_peak_memory_is_small_relative_to_file_size(self, large_log_file):
        path, _error_count, file_size = large_log_file
        gc.collect()
        tracemalloc.start()
        try:
            count = 0
            stats = ParseStats()
            for _entry in iter_entries(path, stats=stats):
                count += 1
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        assert count > 0
        assert stats.total_lines > 0
        # The whole point: peak heap usage must not scale with the 100MB
        # input — it must stay far below the file size.
        assert peak < PEAK_MEMORY_CEILING_BYTES
        assert peak < file_size / 4


class TestSummaryOnLargeFile:
    def test_summary_run_handles_100mb_file_with_bounded_memory(self, large_log_file, tmp_path):
        path, error_count, file_size = large_log_file
        target = tmp_path / "summary.json"
        gc.collect()
        tracemalloc.start()
        try:
            data = summary.run(path, fmt="json", output=str(target))
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        assert data["counts_by_level"]["ERROR"] == error_count
        assert peak < PEAK_MEMORY_CEILING_BYTES
        assert peak < file_size / 4


class TestTimelineOnLargeFile:
    def test_timeline_run_handles_100mb_file_with_bounded_memory(self, large_log_file, tmp_path):
        path, error_count, file_size = large_log_file
        target = tmp_path / "timeline.json"
        gc.collect()
        tracemalloc.start()
        try:
            data = timeline.run(
                path, bucket=timedelta(minutes=15), fmt="json", output=str(target)
            )
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        total_errors = sum(count for _ts, count in data["buckets"])
        assert total_errors == error_count
        assert peak < PEAK_MEMORY_CEILING_BYTES
        assert peak < file_size / 4


class TestGrepOnLargeFile:
    def test_grep_run_streams_matches_without_buffering(self, large_log_file, tmp_path):
        path, error_count, file_size = large_log_file
        target = tmp_path / "grep_out.txt"
        gc.collect()
        tracemalloc.start()
        try:
            match_count = grep.run(path, levels={"ERROR"}, fmt="text", output=str(target))
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        assert match_count == error_count
        assert peak < PEAK_MEMORY_CEILING_BYTES
        assert peak < file_size / 4
