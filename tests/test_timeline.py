import json
import os
from datetime import timedelta

from logscope.commands import timeline

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.log")


class TestTimelineData:
    def test_bucket_counts_and_gap_filling(self):
        data = timeline.run(FIXTURE, bucket=timedelta(minutes=5), fmt="json")
        starts = [b[0].isoformat() for b in data["buckets"]]
        counts = [b[1] for b in data["buckets"]]
        assert starts == [
            "2026-10-01T09:00:00",
            "2026-10-01T09:05:00",
            "2026-10-01T09:10:00",
            "2026-10-01T09:15:00",
            "2026-10-01T09:20:00",
        ]
        assert counts == [1, 1, 0, 0, 2]

    def test_bucket_size_label(self):
        data = timeline.run(FIXTURE, bucket=timedelta(minutes=15), fmt="json")
        assert data["bucket_size"] == "15m"

    def test_no_error_entries_gives_empty_buckets(self, tmp_path):
        log_file = tmp_path / "no_errors.log"
        log_file.write_text("2026-10-01 09:00:00 INFO all good\n", encoding="utf-8")
        data = timeline.run(str(log_file), bucket=timedelta(minutes=15), fmt="json")
        assert data["buckets"] == []

    def test_single_bucket_when_all_errors_in_one_window(self, tmp_path):
        log_file = tmp_path / "one_bucket.log"
        log_file.write_text(
            "2026-10-01 09:00:00 ERROR a\n2026-10-01 09:01:00 ERROR b\n",
            encoding="utf-8",
        )
        data = timeline.run(str(log_file), bucket=timedelta(minutes=15), fmt="json")
        assert len(data["buckets"]) == 1
        assert data["buckets"][0][1] == 2


class TestTimelineOutputFormats:
    def test_text_format_renders_bar_chart(self, capsys):
        timeline.run(FIXTURE, bucket=timedelta(minutes=5), fmt="text")
        captured = capsys.readouterr()
        assert "Error counts per bucket" in captured.out
        assert "#" in captured.out

    def test_json_format_is_valid_and_has_error_counts(self, capsys):
        timeline.run(FIXTURE, bucket=timedelta(minutes=5), fmt="json")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["buckets"][0]["error_count"] == 1

    def test_md_format_writes_file_with_chart_and_table(self, tmp_path, capsys):
        target = tmp_path / "timeline.md"
        timeline.run(FIXTURE, bucket=timedelta(minutes=5), fmt="md", output=str(target))
        captured = capsys.readouterr()
        assert "written to" in captured.out
        content = target.read_text(encoding="utf-8")
        assert "# Timeline Report" in content
        assert "```" in content
        assert "| Bucket Start | Error Count |" in content

    def test_md_format_handles_no_errors_without_crashing(self, tmp_path):
        log_file = tmp_path / "no_errors.log"
        log_file.write_text("2026-10-01 09:00:00 INFO all good\n", encoding="utf-8")
        target = tmp_path / "report.md"
        timeline.run(str(log_file), bucket=timedelta(minutes=15), fmt="md", output=str(target))
        content = target.read_text(encoding="utf-8")
        assert "No ERROR-level entries found" in content
