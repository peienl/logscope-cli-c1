import os

import pytest

from logscope.commands import summary
from logscope.parsing import ParseStats, iter_entries


class TestEncodingOption:
    def test_reads_latin1_encoded_file(self, tmp_path):
        log_file = tmp_path / "latin1.log"
        line = "2026-10-01 09:00:00 ERROR café outage\n"
        log_file.write_bytes(line.encode("latin-1"))

        stats = ParseStats()
        entries = list(iter_entries(str(log_file), encoding="latin-1", stats=stats))

        assert len(entries) == 1
        assert entries[0].message == "café outage"
        assert stats.malformed_lines == 0

    def test_wrong_encoding_does_not_crash_with_replace_errors(self, tmp_path):
        log_file = tmp_path / "latin1.log"
        line = "2026-10-01 09:00:00 ERROR café outage\n"
        log_file.write_bytes(line.encode("latin-1"))

        # Reading latin-1 bytes as utf-8 is invalid for the accented byte;
        # errors="replace" (the default) must swallow it instead of raising.
        stats = ParseStats()
        entries = list(
            iter_entries(str(log_file), encoding="utf-8", errors="replace", stats=stats)
        )
        assert len(entries) == 1
        assert stats.malformed_lines == 0

    def test_strict_errors_raises_on_bad_decoding(self, tmp_path):
        log_file = tmp_path / "latin1.log"
        line = "2026-10-01 09:00:00 ERROR café outage\n"
        log_file.write_bytes(line.encode("latin-1"))

        with pytest.raises(UnicodeDecodeError):
            list(iter_entries(str(log_file), encoding="utf-8", errors="strict"))


class TestEncodingOptionViaCommands:
    def test_summary_run_accepts_encoding_and_errors(self, tmp_path, capsys):
        log_file = tmp_path / "latin1.log"
        log_file.write_bytes(
            "2026-10-01 09:00:00 ERROR café outage\n".encode("latin-1")
        )
        data = summary.run(str(log_file), fmt="json", encoding="latin-1")
        assert data["counts_by_level"] == {"ERROR": 1}
        assert data["malformed_lines"] == 0


class TestCliEncodingOptions:
    def test_cli_passes_through_encoding_flag(self, tmp_path, capsys):
        from logscope.cli import main

        log_file = tmp_path / "latin1.log"
        log_file.write_bytes(
            "2026-10-01 09:00:00 ERROR café outage\n".encode("latin-1")
        )
        exit_code = main(
            ["summary", str(log_file), "--format", "json", "--encoding", "latin-1"]
        )
        captured = capsys.readouterr()
        assert exit_code == 0
        assert '"ERROR": 1' in captured.out

    def test_cli_strict_errors_on_bad_encoding_exits_cleanly(self, tmp_path, capsys):
        from logscope.cli import main

        log_file = tmp_path / "latin1.log"
        log_file.write_bytes(
            "2026-10-01 09:00:00 ERROR café outage\n".encode("latin-1")
        )
        exit_code = main(
            ["summary", str(log_file), "--errors", "strict"]
        )
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "logscope: error:" in captured.err
