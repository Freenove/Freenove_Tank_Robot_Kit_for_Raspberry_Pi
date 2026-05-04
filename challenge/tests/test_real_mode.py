import subprocess
import sys

import pytest


def test_real_mode_fails_clearly_on_non_linux():
    if sys.platform.startswith("linux"):
        pytest.skip("real mode platform guard is only expected on non-Linux dev hosts")

    result = subprocess.run(
        [sys.executable, "-m", "challenge.main", "--mode", "real"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "real mode requires Raspberry Pi/Linux hardware" in result.stderr
    assert "Traceback" not in result.stderr
