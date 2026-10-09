from video_to_skill.subtitles import choose_language, choose_track, parse_vtt

VTT_SLIDING = """WEBVTT

00:00:00.000 --> 00:00:02.000
hello world

00:00:02.000 --> 00:00:04.000
world how are you

00:00:04.000 --> 00:00:06.000
how are you today
"""

VTT_TAGS = """WEBVTT

00:00:00.000 --> 00:00:01.500
<c>Hello</c> &amp; welcome&nbsp;here
"""


def test_parse_vtt_collapses_sliding_duplicates(tmp_path):
    path = tmp_path / "source.en.vtt"
    path.write_text(VTT_SLIDING, encoding="utf-8")
    segments = parse_vtt(path)
    text = " ".join(s["text"] for s in segments)
    assert text == "hello world how are you today"


def test_parse_vtt_strips_tags_and_entities(tmp_path):
    path = tmp_path / "source.en.vtt"
    path.write_text(VTT_TAGS, encoding="utf-8")
    segments = parse_vtt(path)
    assert segments[0]["text"] == "Hello & welcome here"


def test_choose_track_prefers_manual():
    manual = {"en": [{"ext": "vtt", "url": "m"}]}
    automatic = {"en": [{"ext": "vtt", "url": "a"}]}
    lang, track = choose_track(manual, automatic, None)
    assert lang == "en"
    assert track["url"] == "m"


def test_choose_language_falls_back_to_default():
    assert choose_language({"en": []}, None) == "en"
    assert choose_language({"fr": []}, None) is None
