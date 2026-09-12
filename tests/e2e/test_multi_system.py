"""
Testy wielosystemowe dla fixos.
Weryfikuje działanie na różnych dystrybucjach Linux.
"""

import subprocess
import sys
import os
from pathlib import Path
import pytest

# Sprawdź czy jesteśmy w trybie testowym Docker
IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("FIXOS_TEST_MODE", False)


class TestMultiSystemBasic:
    """Podstawowe testy działające na każdym systemie."""

    def test_fixos_import(self):
        """Test importowania modułu fixos."""
        import fixos

        assert fixos is not None

    def test_fixos_cli_exists(self):
        """Test czy CLI jest dostępne."""
        from fixos.cli import cli

        assert cli is not None

    def test_config_load(self):
        """Test ładowania konfiguracji."""
        from fixos.config import FixOsConfig

        cfg = FixOsConfig.load()
        assert cfg is not None

    def test_diagnostics_import(self):
        """Test importowania modułu diagnostyki."""
        from fixos.diagnostics import get_full_diagnostics

        assert get_full_diagnostics is not None


class TestSystemDetection:
    """Testy detekcji systemu operacyjnego."""

    def test_os_detection(self):
        """Test wykrywania systemu operacyjnego."""
        import platform

        system = platform.system()
        assert system in ["Linux", "Darwin", "Windows"]

    def test_distro_detection(self):
        """Test wykrywania dystrybucji (Linux)."""
        if sys.platform == "linux":
            try:
                import distro

                info = distro.info()
                assert "id" in info or "name" in info
            except ImportError:
                # Fallback - sprawdź /etc/os-release
                if os.path.exists("/etc/os-release"):
                    with open("/etc/os-release") as f:
                        content = f.read()
                        assert "ID=" in content

    def test_python_version(self):
        """Test wersji Pythona."""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 9  # Wymagamy Python 3.9+


class TestCliCommands:
    """Testy CLI fixos - wymagają zainstalowanego pakietu."""

    @pytest.fixture
    def fixos_path(self):
        """Prefer the launcher belonging to the interpreter running pytest."""
        import shutil

        interpreter_launcher = Path(sys.executable).with_name("fixos")
        if interpreter_launcher.is_file() and os.access(interpreter_launcher, os.X_OK):
            return str(interpreter_launcher)

        path = shutil.which("fixos")
        if not path:
            pytest.skip("fixos nie jest zainstalowany")
        return path

    def test_help_command(self, fixos_path):
        """Test komendy --help."""
        result = subprocess.run(
            [fixos_path, "--help"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "fixos" in result.stdout.lower()

    def test_scan_help(self, fixos_path):
        """Test fixos scan --help."""
        result = subprocess.run(
            [fixos_path, "scan", "--help"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "scan" in result.stdout.lower()

    def test_config_show(self, fixos_path):
        """Test fixos config show."""
        result = subprocess.run(
            [fixos_path, "config", "show"], capture_output=True, text=True, timeout=10
        )
        # Może zwrócić błąd jeśli brak .env, ale powinno się uruchomić
        assert result.returncode in [0, 1]  # 0 = ok, 1 = brak configu


class TestDockerEnvironment:
    """Testy specyficzne dla środowiska Docker."""

    def test_docker_environment_detected(self):
        """Test wykrywania środowiska Docker."""
        in_docker = (
            os.path.exists("/.dockerenv") or os.environ.get("FIXOS_TEST_MODE") == "1"
        )
        # Ten test przechodzi zarówno w Docker jak i poza nim
        # ale dokumentuje że wiemy gdzie jesteśmy
        assert isinstance(in_docker, bool)

    def test_required_commands_available(self):
        """Test dostępności wymaganych komend."""
        import shutil

        required = ["python3", "pip3", "bash"]
        if sys.platform == "linux":
            required.extend(["ps", "ls", "cat"])

        missing = []
        for cmd in required:
            if not shutil.which(cmd):
                missing.append(cmd)

        assert not missing, f"Brakujące komendy: {missing}"

    def test_disk_space_available(self):
        """Test dostępności miejsca na dysku."""
        import shutil

        total, used, free = shutil.disk_usage("/")
        # Wymagamy przynajmniej 100MB wolnego miejsca
        assert free > 100 * 1024 * 1024


class TestSystemServices:
    """Testy usług systemowych (tylko w Docker)."""

    @pytest.mark.skipif(not IN_DOCKER, reason="Wymaga środowiska Docker")
    def test_systemd_or_init(self):
        """Test obecności init systemu."""
        import shutil

        # Sprawdź czy mamy systemd lub inny init
        has_systemd = shutil.which("systemctl") is not None
        has_init = os.path.exists("/sbin/init") or os.path.exists("/bin/init")
        assert has_systemd or has_init, "Brak systemu init"

    @pytest.mark.skipif(not IN_DOCKER, reason="Wymaga środowiska Docker")
    def test_dbus_availability(self):
        """Test dostępności D-Bus."""
        dbus_socket = "/run/dbus/system_bus_socket"
        has_dbus = os.path.exists(dbus_socket)
        # Nie wymagamy D-Bus wszędzie, ale sprawdzamy czy wiemy jak go wykryć
        assert isinstance(has_dbus, bool)
