from datetime import timedelta

import pytest

from logscope.timeutil import (
    floor_to_bucket,
    humanize_duration,
    parse_duration,
    parse_timestamp,
    parse_user_datetime,
)


class TestParseTimestamp:
    def test_space_separator_no_fraction(self):
        ts = parse_timestamp("2026-10-01 09:00:03")
        assert ts.isoformat() == "2026-10-01T09:00:03"

    def test_t_separator_no_fraction(self):
        ts = parse_timestamp("2026-10-01T09:00:03")
        assert ts.isoformat() == "2026-10-01T09:00:03"

    def test_dot_milliseconds(self):
        ts = parse_timestamp("2026-10-01 09:00:03.123")
        assert ts.microsecond == 123000

    def test_comma_milliseconds(self):
        ts = parse_timestamp("2026-10-01 09:00:03,500")
        assert ts.microsecond == 500000

    def test_invalid_returns_none(self):
        assert parse_timestamp("not a timestamp") is None

    def test_invalid_calendar_date_returns_none(self):
        assert parse_timestamp("2026-99-99 09:00:00") is None


class TestParseUserDatetime:
    def test_full_datetime(self):
        dt = parse_user_datetime("2026-10-01 09:00:00")
        assert dt.isoformat() == "2026-10-01T09:00:00"

    def test_date_and_hour_minute(self):
        dt = parse_user_datetime("2026-10-01 09:00")
        assert dt.isoformat() == "2026-10-01T09:00:00"

    def test_date_only(self):
        dt = parse_user_datetime("2026-10-01")
        assert dt.isoformat() == "2026-10-01T00:00:00"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_user_datetime("not a date")


class TestParseDuration:
    @pytest.mark.parametrize(
        "raw,expected_seconds",
        [
            ("30s", 30),
            ("15m", 900),
            ("2h", 7200),
            ("1d", 86400),
        ],
    )
    def test_valid_units(self, raw, expected_seconds):
        assert parse_duration(raw) == timedelta(seconds=expected_seconds)

    def test_case_insensitive_unit(self):
        assert parse_duration("15M") == timedelta(minutes=15)

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            parse_duration("fifteen minutes")

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            parse_duration("0s")


class TestHumanizeDuration:
    def test_minutes(self):
        assert humanize_duration(timedelta(minutes=15)) == "15m"

    def test_seconds(self):
        assert humanize_duration(timedelta(seconds=30)) == "30s"

    def test_hours(self):
        assert humanize_duration(timedelta(hours=2)) == "2h"


class TestFloorToBucket:
    def test_floors_to_15_minute_window(self):
        ts = parse_timestamp("2026-10-01 09:07:03")
        floored = floor_to_bucket(ts, timedelta(minutes=15))
        assert floored.isoformat() == "2026-10-01T09:00:00"

    def test_exact_boundary_stays_same(self):
        ts = parse_timestamp("2026-10-01 09:15:00")
        floored = floor_to_bucket(ts, timedelta(minutes=15))
        assert floored.isoformat() == "2026-10-01T09:15:00"
