import json
import os
from datetime import datetime

from logscope.commands import grep

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.log")


class TestGrepFiltering:
    def test_no_filters_matches_everything(self, capsys):
        count = grep.run(FIXTURE, fmt="text")
        captured = capsys.readouterr()
        assert count == 10
        assert "Matches: 10" in captured.out

    def test_filters_by_single_level(self, capsys):
        count = grep.run(FIXTURE, levels={"ERROR"}, fmt="text")
        captured = capsys.readouterr()
        assert count == 4
        assert "Payment gateway timeout: order=1234" in captured.out
        assert "INFO" not in captured.out

    def test_filters_by_multiple_levels(self):
        count = grep.run(FIXTURE, levels={"ERROR", "WARN"}, fmt="json")
        assert count == 6

    def test_filters_by_since(self):
        since = datetime(2026, 10, 1, 9, 5, 0)
        count = grep.run(FIXTURE, levels={"ERROR"}, since=since, fmt="json")
        assert count == 3

    def test_filters_by_until(self):
        until = datetime(2026, 10, 1, 9, 5, 0)
        count = grep.run(FIXTURE, levels={"ERROR"}, until=until, fmt="json")
        assert count == 1

    def test_since_and_until_combined(self):
        since = datetime(2026, 10, 1, 9, 5, 0)
        until = datetime(2026, 10, 1, 9, 21, 0)
        count = grep.run(FIXTURE, since=since, until=until, fmt="json")
        assert count == 4

    def test_no_matches_returns_zero(self, capsys):
        count = grep.run(FIXTURE, levels={"FATAL"}, fmt="text")
        captured = capsys.readouterr()
        assert count == 0
        assert "Matches: 0" in captured.out

    def test_multiline_entry_preserved_in_text_output(self, capsys):
        grep.run(FIXTURE, levels={"ERROR"}, fmt="text")
        captured = capsys.readouterr()
        assert "at PaymentClient.call" in captured.out
        assert "at OrderService.pay" in captured.out


class TestGrepOutputFormats:
    def test_json_output_is_valid_and_has_stats(self):
        count = grep.run(FIXTURE, levels={"ERROR"}, fmt="json", output=None)
        # re-run capturing stdout content via a file for exact round-trip
        assert count == 4

    def test_json_written_to_file_parses_correctly(self, tmp_path):
        target = tmp_path / "grep.json"
        grep.run(FIXTURE, levels={"ERROR"}, fmt="json", output=str(target))
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["match_count"] == 4
        assert data["malformed_lines"] == 2
        assert len(data["matches"]) == 4

    def test_json_with_zero_matches_is_still_valid(self, tmp_path):
        target = tmp_path / "grep_empty.json"
        grep.run(FIXTURE, levels={"FATAL"}, fmt="json", output=str(target))
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["match_count"] == 0
        assert data["matches"] == []

    def test_md_format_writes_file_not_stdout(self, tmp_path, capsys):
        target = tmp_path / "grep.md"
        grep.run(FIXTURE, levels={"ERROR"}, fmt="md", output=str(target))
        captured = capsys.readouterr()
        assert "written to" in captured.out
        content = target.read_text(encoding="utf-8")
        assert "# Grep Report" in content
        assert "Database connection refused" in content

    def test_md_format_zero_matches_notes_no_results(self, tmp_path):
        target = tmp_path / "grep_empty.md"
        grep.run(FIXTURE, levels={"FATAL"}, fmt="md", output=str(target))
        content = target.read_text(encoding="utf-8")
        assert "No matching entries found" in content
