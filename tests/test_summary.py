import json
import os

from logscope.commands import summary

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.log")


class TestSummaryData:
    def test_counts_by_level(self):
        data = summary.run(FIXTURE, fmt="json", output=None)
        assert data["counts_by_level"] == {"ERROR": 4, "INFO": 4, "WARN": 2}

    def test_malformed_and_total_lines(self):
        data = summary.run(FIXTURE, fmt="json", output=None)
        assert data["malformed_lines"] == 2
        assert data["total_lines"] > 0

    def test_first_and_last_timestamp(self):
        data = summary.run(FIXTURE, fmt="json", output=None)
        assert data["first_timestamp"].isoformat() == "2026-10-01T09:00:01"
        assert data["last_timestamp"].isoformat() == "2026-10-01T10:02:11"

    def test_top_errors_sorted_by_count_desc(self):
        data = summary.run(FIXTURE, fmt="json", output=None)
        top = data["top_errors"]
        assert top[0] == {"message": "Payment gateway timeout: order=1234", "count": 2}
        counts = [e["count"] for e in top]
        assert counts == sorted(counts, reverse=True)

    def test_top_errors_capped_at_five(self, tmp_path):
        lines = [
            f"2026-10-01 09:00:{i:02d} ERROR unique error {i}\n" for i in range(10)
        ]
        log_file = tmp_path / "many_errors.log"
        log_file.write_text("".join(lines), encoding="utf-8")
        data = summary.run(str(log_file), fmt="json", output=None)
        assert len(data["top_errors"]) == 5

    def test_no_entries_does_not_crash(self, tmp_path):
        log_file = tmp_path / "empty.log"
        log_file.write_text("", encoding="utf-8")
        data = summary.run(str(log_file), fmt="json", output=None)
        assert data["counts_by_level"] == {}
        assert data["top_errors"] == []
        assert data["first_timestamp"] is None
        assert data["last_timestamp"] is None


class TestSummaryOutputFormats:
    def test_text_format_prints_to_stdout(self, capsys):
        summary.run(FIXTURE, fmt="text")
        captured = capsys.readouterr()
        assert "Counts by level" in captured.out
        assert "Top 5 error messages" in captured.out

    def test_json_format_is_valid_json_on_stdout(self, capsys):
        summary.run(FIXTURE, fmt="json")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["counts_by_level"]["ERROR"] == 4

    def test_md_format_writes_file_not_stdout(self, tmp_path, capsys):
        target = tmp_path / "summary.md"
        summary.run(FIXTURE, fmt="md", output=str(target))
        captured = capsys.readouterr()
        assert "written to" in captured.out
        assert "Counts by Level" not in captured.out
        content = target.read_text(encoding="utf-8")
        assert "# Summary Report" in content
        assert "| ERROR | 4 |" in content

    def test_md_format_default_output_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        summary.run(FIXTURE, fmt="md")
        expected = "sample_summary_report.md"
        assert os.path.exists(expected)
