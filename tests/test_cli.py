import json
import os

from logscope.cli import main

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.log")


class TestCliSummary:
    def test_summary_text_exit_code_zero(self, capsys):
        exit_code = main(["summary", FIXTURE])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Counts by level" in captured.out

    def test_summary_json(self, capsys):
        exit_code = main(["summary", FIXTURE, "--format", "json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert data["counts_by_level"]["ERROR"] == 4

    def test_summary_md_writes_file(self, tmp_path):
        target = tmp_path / "out.md"
        exit_code = main(["summary", FIXTURE, "--format", "md", "--output", str(target)])
        assert exit_code == 0
        assert target.exists()


class TestCliTimeline:
    def test_timeline_default_bucket(self, capsys):
        exit_code = main(["timeline", FIXTURE])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Bucket size: 15m" in captured.out

    def test_timeline_custom_bucket(self, capsys):
        exit_code = main(["timeline", FIXTURE, "--bucket", "5m"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Bucket size: 5m" in captured.out

    def test_timeline_invalid_bucket_errors_cleanly(self, capsys):
        exit_code = main(["timeline", FIXTURE, "--bucket", "not-a-duration"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "logscope: error:" in captured.err


class TestCliGrep:
    def test_grep_filters_by_level(self, capsys):
        exit_code = main(["grep", FIXTURE, "--level", "ERROR"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Matches: 4" in captured.out

    def test_grep_filters_by_multiple_levels(self, capsys):
        exit_code = main(["grep", FIXTURE, "--level", "ERROR,WARN"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Matches: 6" in captured.out

    def test_grep_since_filter(self, capsys):
        exit_code = main(
            ["grep", FIXTURE, "--level", "ERROR", "--since", "2026-10-01 09:05"]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Matches: 3" in captured.out

    def test_grep_invalid_level_errors_cleanly(self, capsys):
        exit_code = main(["grep", FIXTURE, "--level", "BOGUS"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "logscope: error:" in captured.err

    def test_grep_invalid_since_errors_cleanly(self, capsys):
        exit_code = main(["grep", FIXTURE, "--since", "not-a-date"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "logscope: error:" in captured.err


class TestCliErrorHandling:
    def test_missing_file_errors_cleanly(self, capsys):
        exit_code = main(["summary", "no_such_file.log"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "file not found" in captured.err

    def test_missing_file_never_raises(self):
        # main() must catch the error internally, not propagate it.
        exit_code = main(["grep", "no_such_file.log"])
        assert exit_code == 1

    def test_requires_a_subcommand(self):
        try:
            main([])
            assert False, "expected SystemExit for missing subcommand"
        except SystemExit as exc:
            assert exc.code != 0
