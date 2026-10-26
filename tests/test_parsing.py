import inspect
import os

import pytest

from logscope.parsing import ParseStats, iter_entries, normalize_level

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.log")


class TestNormalizeLevel:
    def test_warning_normalizes_to_warn(self):
        assert normalize_level("WARNING") == "WARN"

    def test_already_normal_level_unchanged(self):
        assert normalize_level("error") == "ERROR"


class TestIterEntriesIsStreaming:
    def test_iter_entries_is_a_generator(self):
        assert inspect.isgeneratorfunction(iter_entries)

    def test_source_never_reads_whole_file(self):
        source = inspect.getsource(iter_entries)
        assert ".read(" not in source
        assert ".readlines(" not in source


class TestIterEntriesOnFixture:
    def test_entry_count_and_levels(self):
        stats = ParseStats()
        entries = list(iter_entries(FIXTURE, stats=stats))
        levels = [e.level for e in entries]
        assert levels == [
            "INFO",
            "INFO",
            "WARN",
            "ERROR",
            "ERROR",
            "INFO",
            "ERROR",
            "WARN",
            "ERROR",
            "INFO",
        ]

    def test_malformed_lines_counted(self):
        stats = ParseStats()
        list(iter_entries(FIXTURE, stats=stats))
        assert stats.malformed_lines == 2

    def test_total_lines_counts_every_physical_line(self):
        stats = ParseStats()
        list(iter_entries(FIXTURE, stats=stats))
        with open(FIXTURE, "r", encoding="utf-8") as handle:
            expected = sum(1 for _ in handle)
        assert stats.total_lines == expected

    def test_multiline_entry_preserves_stack_trace(self):
        entries = list(iter_entries(FIXTURE))
        multiline = next(e for e in entries if len(e.lines) > 1)
        assert multiline.message == "Payment gateway timeout: order=1234"
        assert "at PaymentClient.call" in multiline.full_text
        assert "at OrderService.pay" in multiline.full_text

    def test_timestamps_are_chronological_in_fixture(self):
        entries = list(iter_entries(FIXTURE))
        timestamps = [e.timestamp for e in entries]
        assert timestamps == sorted(timestamps)


class TestIterEntriesMalformedHandling:
    def test_leading_garbage_with_no_prior_entry_is_malformed(self, tmp_path):
        log_file = tmp_path / "leading_garbage.log"
        log_file.write_text("garbage with no header\n", encoding="utf-8")
        stats = ParseStats()
        entries = list(iter_entries(str(log_file), stats=stats))
        assert entries == []
        assert stats.malformed_lines == 1

    def test_invalid_timestamp_header_is_malformed_and_flushes_prior_entry(
        self, tmp_path
    ):
        log_file = tmp_path / "bad_timestamp.log"
        log_file.write_text(
            "2026-10-01 09:00:00 INFO first entry\n"
            "2026-99-99 09:00:00 ERROR bad timestamp\n",
            encoding="utf-8",
        )
        stats = ParseStats()
        entries = list(iter_entries(str(log_file), stats=stats))
        assert len(entries) == 1
        assert entries[0].message == "first entry"
        assert stats.malformed_lines == 1

    def test_blank_lines_are_skipped_silently(self, tmp_path):
        log_file = tmp_path / "blank_lines.log"
        log_file.write_text(
            "2026-10-01 09:00:00 INFO first entry\n"
            "\n"
            "   \n"
            "2026-10-01 09:00:01 INFO second entry\n",
            encoding="utf-8",
        )
        stats = ParseStats()
        entries = list(iter_entries(str(log_file), stats=stats))
        assert len(entries) == 2
        assert stats.malformed_lines == 0

    def test_never_raises_on_arbitrary_garbage(self, tmp_path):
        log_file = tmp_path / "all_garbage.log"
        log_file.write_text(
            "\x00binary-ish garbage\n"
            "another broken line ###\n"
            "2026-10-01 09:00:00 INFO a real entry\n",
            encoding="utf-8",
        )
        stats = ParseStats()
        entries = list(iter_entries(str(log_file), stats=stats))
        assert len(entries) == 1
        assert stats.malformed_lines == 2

    def test_does_not_crash_on_missing_file(self):
        with pytest.raises(OSError):
            list(iter_entries("this/file/does/not/exist.log"))
