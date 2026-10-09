from video_to_skill._time import fmt_ts, fmt_ts_short, frange


def test_fmt_ts_minutes_and_centiseconds():
    assert fmt_ts(65.25) == "01:05.25"
    assert fmt_ts(0) == "00:00.00"


def test_fmt_ts_hours():
    assert fmt_ts(3723.0) == "01:02:03.00"


def test_fmt_ts_negative_clamped():
    assert fmt_ts(-5) == "00:00.00"


def test_fmt_ts_short():
    assert fmt_ts_short(65) == "01:05"
    assert fmt_ts_short(3723) == "1:02:03"


def test_frange():
    assert list(frange(0, 5, 2)) == [0, 2, 4]
    assert list(frange(0, 0, 1)) == []
