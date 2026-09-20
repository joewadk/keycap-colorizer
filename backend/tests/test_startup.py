import socket
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest
from app import startup
from app.config import Settings


def test_missing_pillow_gives_install_instructions(monkeypatch):
    original = startup.importlib.import_module
    def load(name):
        if name == "PIL.Image":
            raise ImportError("internal path")
        return original(name)
    monkeypatch.setattr(startup.importlib, "import_module", load)
    with pytest.raises(startup.StartupError, match="Pillow.*install.ps1 or install.sh"):
        startup.check_dependencies()


def test_busy_port_is_reported_without_stopping_owner():
    with socket.socket() as owner:
        owner.bind(("127.0.0.1", 0))
        owner.listen(1)
        port = owner.getsockname()[1]
        with pytest.raises(startup.StartupError, match=f"Port {port} is unavailable"):
            startup.check_port(port)
        assert owner.fileno() != -1


def test_configuration_check_creates_no_database(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "products.db"
    monkeypatch.setattr("app.config.Settings", lambda: Settings(_env_file=None, database_path=str(path)))
    startup.check_configuration()
    assert not path.parent.exists()


def test_directory_database_path_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.Settings", lambda: Settings(_env_file=None, database_path=str(tmp_path)))
    with pytest.raises(startup.StartupError, match="directory"):
        startup.check_configuration()


def test_configuration_error_does_not_echo_inputs(monkeypatch):
    def invalid():
        return Settings(_env_file=None, ai_provider="secret-token-value")
    monkeypatch.setattr("app.config.Settings", invalid)
    with pytest.raises(startup.StartupError) as caught:
        startup.check_configuration()
    assert "secret-token-value" not in str(caught.value)


def test_failed_preflight_exits_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(startup, "check_dependencies", Mock(side_effect=startup.StartupError("Missing dependency")))
    assert startup.main() == 1
    assert "Startup check failed" in capsys.readouterr().err


def test_valid_preflight_checks_both_ports(monkeypatch):
    monkeypatch.setattr(startup, "check_dependencies", Mock())
    monkeypatch.setattr(startup, "check_configuration", Mock())
    ports = Mock()
    monkeypatch.setattr(startup, "check_port", ports)
    assert startup.main() == 0
    assert [call.args[0] for call in ports.call_args_list] == [8000, 5173]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell job-stream regression")
def test_powershell_launcher_accepts_native_stderr_and_detects_exit():
    powershell = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    executable = str(powershell) if powershell.is_file() else shutil.which("pwsh")
    if not executable:
        pytest.skip("PowerShell not installed")
    fixtures = Path(__file__).parent / "fixtures"
    result = subprocess.run([executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(fixtures / "check_job_logs.ps1"), "-Launcher", str(Path(__file__).resolve().parents[2] / "start.ps1"),
        "-Python", sys.executable, "-Fixture", str(fixtures / "startup_log.py")],
        capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "INFO: Started regression service" in result.stdout
    assert "HEALTHY_STDERR_ACCEPTED" in result.stdout
    assert "Fixture exited with code 7" in result.stdout
    assert "SERVICE_EXIT_DETECTED" in result.stdout
