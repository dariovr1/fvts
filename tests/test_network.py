import subprocess
import sys

import pytest

# A stable, short, widely-available video. Public and long-lived.
SAMPLE_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


@pytest.mark.network
def test_probe_cli_runs():
    result = subprocess.run(
        [sys.executable, "-m", "video_to_skill.cli", "probe", SAMPLE_URL],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0
    assert "RADAR REPORT" in result.stdout
