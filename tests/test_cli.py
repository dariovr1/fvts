import pytest

from video_to_skill.cli import build_parser, main


def test_parser_watch_defaults():
    parser = build_parser()
    args = parser.parse_args(["watch", "https://example.com/v"])
    assert args.command == "watch"
    assert args.mode == "auto"
    assert args.max_frames == 60
    assert args.glossary == ""


def test_parser_probe():
    parser = build_parser()
    args = parser.parse_args(["probe", "https://example.com/v", "--language", "en"])
    assert args.command == "probe"
    assert args.language == "en"


def test_main_probe_rejects_local_file(capsys):
    assert main(["probe", "local.mp4"]) == 2
    assert "only useful for URLs" in capsys.readouterr().out


def test_main_requires_command():
    with pytest.raises(SystemExit):
        main([])
