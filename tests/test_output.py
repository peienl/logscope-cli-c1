import json
from datetime import datetime

import pytest

from logscope import output as out


class TestResolveOutputPath:
    def test_md_without_output_option_defaults_to_report_file(self):
        path = out.resolve_output_path("app.log", "summary", "md", None)
        assert path == "app_summary_report.md"

    def test_md_with_explicit_output_option(self):
        path = out.resolve_output_path("app.log", "summary", "md", "custom.md")
        assert path == "custom.md"

    def test_json_without_output_option_means_stdout(self):
        assert out.resolve_output_path("app.log", "summary", "json", None) is None

    def test_text_with_output_option_uses_it(self):
        path = out.resolve_output_path("app.log", "grep", "text", "out.txt")
        assert path == "out.txt"


class TestWriteOutput:
    def test_none_target_prints_to_stdout(self, capsys):
        out.write_output("hello", None, "text")
        captured = capsys.readouterr()
        assert captured.out.strip() == "hello"

    def test_md_writes_file_and_prints_only_confirmation(self, tmp_path, capsys):
        target = tmp_path / "report.md"
        out.write_output("# Report\nbody", str(target), "md")
        captured = capsys.readouterr()
        assert "written to" in captured.out
        assert "# Report" not in captured.out
        assert target.read_text(encoding="utf-8") == "# Report\nbody\n"

    def test_json_writes_file_and_prints_confirmation(self, tmp_path, capsys):
        target = tmp_path / "out.json"
        out.write_output('{"a": 1}', str(target), "json")
        captured = capsys.readouterr()
        assert "Output written to" in captured.out
        assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}


class TestJsonHelpers:
    def test_dump_json_serializes_datetime_as_isoformat(self):
        payload = {"ts": datetime(2026, 10, 1, 9, 0, 0)}
        result = json.loads(out.dump_json(payload))
        assert result["ts"] == "2026-10-01T09:00:00"

    def test_dump_json_rejects_unknown_types(self):
        class Unserializable:
            pass

        with pytest.raises(TypeError):
            out.dump_json({"x": Unserializable()})

    def test_format_timestamp_none(self):
        assert out.format_timestamp(None) is None

    def test_format_timestamp_value(self):
        assert out.format_timestamp(datetime(2026, 10, 1)) == "2026-10-01T00:00:00"


class TestTextTable:
    def test_aligns_columns_and_includes_separator(self):
        table = out.text_table(["Level", "Count"], [["ERROR", 3], ["INFO", 10]])
        lines = table.splitlines()
        assert lines[0].startswith("Level")
        assert lines[1].startswith("-----")
        assert "ERROR" in lines[2]
        assert "INFO" in lines[3]


class TestBarChart:
    def test_empty_labels_returns_placeholder(self):
        assert out.bar_chart([], []) == "(no data)"

    def test_zero_max_value_renders_without_error(self):
        chart = out.bar_chart(["a", "b"], [0, 0])
        assert "a" in chart and "b" in chart

    def test_largest_value_gets_full_width_bar(self):
        chart = out.bar_chart(["a", "b"], [5, 10], width=20)
        lines = chart.splitlines()
        bar_b = lines[1].split("|")[1].strip().split(" ")[0]
        assert len(bar_b) == 20


class TestMarkdownHelpers:
    def test_md_table_escapes_pipe_characters(self):
        table = out.md_table(["Message"], [["a | b"]])
        assert "a \\| b" in table

    def test_md_table_collapses_embedded_newlines(self):
        table = out.md_table(["Message"], [["line1\nline2"]])
        assert "\n" not in table.splitlines()[2]

    def test_md_bullet_list(self):
        result = out.md_bullet_list(["one", "two"])
        assert result == "- one\n- two"

    def test_md_code_block_wraps_in_fences(self):
        block = out.md_code_block("some text")
        assert block.startswith("```\n")
        assert block.endswith("\n```")

    def test_md_document_assembles_title_and_sections(self):
        doc = out.md_document("Title", [("Heading", "body text")])
        assert doc.startswith("# Title")
        assert "## Heading" in doc
        assert "body text" in doc
