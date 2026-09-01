"""
Testy jednostkowe – anonymizer (v2.2 fixes).
Pokrywa: pyenv paths, kolejność zastąpień, pełne ścieżki /home.
"""

from __future__ import annotations

import getpass
import socket


from fixos.utils.anonymizer import (
    AnonymizationContext,
    AnonymizationReport,
    ResolutionError,
    anonymize,
    deanonymize,
)


class TestHomePaths:
    """Testy anonimizacji ścieżek /home – fix v2.2."""

    def test_pyenv_full_path_anonymized(self):
        """Pełna ścieżka /home/user/.pyenv/versions/... musi być zamaskowana."""
        username = getpass.getuser()
        data = f"/home/{username}/.pyenv/versions/3.12.0/bin/python3.12"
        anon, report = anonymize(data)
        assert username not in anon
        assert "/home/[USER]" in anon

    def test_deep_nested_home_path(self):
        """Głęboko zagnieżdżona ścieżka /home/user/a/b/c/d musi być zamaskowana."""
        data = "/home/jankowalski/projects/myapp/src/utils/helper.py"
        anon, _ = anonymize(data)
        assert "jankowalski" not in anon
        assert "/home/[USER-2]" in anon

    def test_multiple_home_paths_all_masked(self):
        """Wiele ścieżek /home w jednym stringu – wszystkie muszą być zamaskowane."""
        data = (
            "python at /home/alice/.pyenv/versions/3.11/bin/python "
            "config at /home/alice/.config/fixos/settings.conf "
            "log at /home/alice/.local/share/fixos/session.log"
        )
        anon, report = anonymize(data)
        assert "alice" not in anon
        assert anon.count("/home/[USER-2]") == 3

    def test_home_path_with_spaces_in_context(self):
        """Ścieżka /home/user/... w kontekście z innymi słowami."""
        data = "executable: /home/tom/.local/bin/fixos version 2.2"
        anon, _ = anonymize(data)
        assert "tom" not in anon

    def test_home_path_in_error_message(self):
        """Ścieżka /home/user w komunikacie błędu."""
        data = "FileNotFoundError: /home/testuser/.config/app.conf not found"
        anon, _ = anonymize(data)
        assert "testuser" not in anon
        assert "/home/[USER-2]" in anon

    def test_home_path_already_anonymized_not_double_replaced(self):
        """Już zanonimizowana ścieżka /home/[USER] nie powinna być podwójnie zastąpiona."""
        data = "/home/[USER]/some/path"
        anon, report = anonymize(data)
        assert "/home/[USER]" in anon
        assert "/home/[USER]/[USER]" not in anon

    def test_non_home_paths_not_affected(self):
        """Ścieżki poza /home nie powinny być zmieniane."""
        data = "config at /etc/fixos/config and /usr/local/bin/fixos"
        anon, report = anonymize(data)
        assert "/etc/fixos/config" in anon
        assert "/usr/local/bin/fixos" in anon

    def test_literal_home_dir_replaced_first(self):
        """Dosłowny katalog domowy (~) powinien być zastąpiony przed regex."""
        import os

        home = os.path.expanduser("~")
        data = f"path: {home}/.config/fixos"
        anon, report = anonymize(data)
        assert home not in anon

    def test_username_replaced_after_paths(self):
        """Username jako słowo powinien być zastąpiony nawet po zastąpieniu ścieżek."""
        username = getpass.getuser()
        data = f"user {username} logged in from /home/{username}/.ssh/id_rsa"
        anon, report = anonymize(data)
        assert username not in anon


class TestAnonymizerOrder:
    """Testy kolejności zastąpień – fix v2.2."""

    def test_hostname_replaced_before_username(self):
        """Hostname zastępowany przed username (hostname może zawierać username)."""
        hostname = socket.gethostname()
        data = f"connected to {hostname}"
        anon, report = anonymize(data)
        assert hostname not in anon
        assert "[HOSTNAME]" in anon

    def test_home_path_replaced_before_username_word(self):
        """Ścieżka /home/user zastąpiona zanim username jako słowo."""
        username = getpass.getuser()
        data = f"/home/{username}/file.txt and user {username} is active"
        anon, _ = anonymize(data)
        assert username not in anon

    def test_report_categories_present(self):
        """Raport powinien zawierać kategorie dla każdego zastąpienia."""
        username = getpass.getuser()
        hostname = socket.gethostname()
        data = (
            f"host={hostname} user={username} "
            f"ip=192.168.1.1 mac=aa:bb:cc:dd:ee:ff "
            f"uuid=a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )
        _, report = anonymize(data)
        assert isinstance(report, AnonymizationReport)
        assert report.original_length > 0
        assert report.anonymized_length > 0
        assert len(report.replacements) >= 3

    def test_report_summary_format(self):
        """Raport summary powinien zawierać czytelne linie."""
        data = "ip=192.168.1.1"
        _, report = anonymize(data)
        summary = report.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestAnonymizerEdgeCases:
    """Testy przypadków brzegowych."""

    def test_empty_string(self):
        anon, report = anonymize("")
        assert anon == ""
        assert len(report.replacements) == 0

    def test_none_converted_to_string(self):
        anon, _ = anonymize(None)
        assert isinstance(anon, str)

    def test_dict_converted_to_string(self):
        anon, _ = anonymize({"key": "value", "ip": "192.168.1.1"})
        assert isinstance(anon, str)
        assert "192.168.1.1" not in anon

    def test_very_long_path(self):
        """Bardzo długa ścieżka nie powinna powodować błędów."""
        data = "/home/user/" + "subdir/" * 20 + "file.txt"
        anon, _ = anonymize(data)
        assert isinstance(anon, str)

    def test_path_with_special_chars(self):
        """Ścieżka ze spacją i specjalnymi znakami."""
        data = "file at /home/jan/My Documents/report.pdf"
        anon, _ = anonymize(data)
        assert isinstance(anon, str)

    def test_api_token_sk_or_masked(self):
        """Token OpenRouter sk-or-v1-... musi być zamaskowany."""
        data = "using key sk-or-v1-abcdefghijklmnopqrstuvwxyz1234567890"
        anon, report = anonymize(data)
        assert "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234567890" not in anon
        assert report.replacements.get("Tokeny API", 0) > 0

    def test_api_token_gemini_masked(self):
        """Token Gemini AIzaSy... musi być zamaskowany."""
        data = "GEMINI_API_" "KEY=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        anon, report = anonymize(data)
        assert "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ123456" not in anon

    def test_uuid_hardware_masked(self):
        """UUID hardware identifiers muszą być zamaskowane."""
        data = "disk UUID=a1b2c3d4-e5f6-7890-abcd-ef1234567890 mounted at /mnt"
        anon, report = anonymize(data)
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" not in anon
        assert report.replacements.get("UUID (serial/hardware)", 0) > 0

    def test_mac_address_masked(self):
        """Adresy MAC muszą być zamaskowane."""
        data = "interface eth0 hwaddr aa:bb:cc:dd:ee:ff"
        anon, report = anonymize(data)
        assert "aa:bb:cc:dd:ee:ff" not in anon
        assert "XX:XX:XX:XX:XX:XX" in anon

    def test_ipv4_subnet_is_not_exposed(self):
        """Alias zachowuje klasę adresu bez ujawniania prefiksu sieci."""
        data = "connected to 192.168.1.100"
        anon, _ = anonymize(data)
        assert anon == "connected to [IP-PRIVATE-1]"
        assert "192.168" not in anon
        assert "192.168.1.100" not in anon

    def test_password_in_env_masked(self):
        """Hasła w zmiennych środowiskowych muszą być zamaskowane."""
        data = "DB_PASS" "WORD=supersecret123 API_" "KEY=mytoken456"
        anon, report = anonymize(data)
        assert "supersecret123" not in anon
        assert report.replacements.get("Hasła/sekrety", 0) > 0


class TestContextPreservingAliases:
    """Regresje kontraktu wellmanifest.anonym/v1 dla FixOS."""

    def test_legacy_llm_shell_facade_uses_shared_policy(self):
        from fixos.anonymizer import anonymize as legacy_anonymize

        anon = legacy_anonymize(
            "/home/alice/.cache/JetBrains peer=192.168.1.10"
        )
        assert "/home/[USER-2]/.cache/JetBrains" in anon
        assert "[IP-PRIVATE-1]" in anon
        assert "alice" not in anon
        assert "192.168.1.10" not in anon

    def test_home_suffix_and_distinct_users_are_preserved(self):
        context = AnonymizationContext("paths", primary_user="primary")
        data = (
            "/home/primary/.config/fixos/settings.toml "
            "/home/alice/.cache/JetBrains/PyCharm/index "
            "/home/alice/projects/api/pyproject.toml "
            "/home/bob/.local/share/app/state"
        )

        anon, report = anonymize(data, context=context)

        assert "/home/[USER]/.config/fixos/settings.toml" in anon
        assert "/home/[USER-2]/.cache/JetBrains/PyCharm/index" in anon
        assert "/home/[USER-2]/projects/api/pyproject.toml" in anon
        assert "/home/[USER-3]/.local/share/app/state" in anon
        assert "alice" not in anon
        assert "bob" not in anon
        assert report.mapping_id == "paths"

    def test_aliases_stay_stable_across_explicit_context_calls(self):
        context = AnonymizationContext("session", primary_user="primary")
        first, _ = anonymize("/home/alice/.cache/a peer=10.1.2.3", context=context)
        second, _ = anonymize("/home/alice/.config/b peer=10.1.2.3", context=context)

        assert "/home/[USER-2]/.cache/a" in first
        assert "/home/[USER-2]/.config/b" in second
        assert "[IP-PRIVATE-1]" in first
        assert "[IP-PRIVATE-1]" in second

    def test_ip_semantics_and_identity_are_preserved(self):
        context = AnonymizationContext("network")
        data = (
            "0.0.0.0 127.0.0.1 127.0.0.2 255.255.255.255 "
            "192.168.1.10 192.168.1.10 8.8.8.8 169.254.1.4 "
            "224.0.0.1 192.0.2.1"
        )

        anon, _ = anonymize(data, context=context)

        assert "[IP-ANY]" in anon
        assert anon.count("[IP-LOOPBACK]") == 2
        assert "[IP-BROADCAST]" in anon
        assert anon.count("[IP-PRIVATE-1]") == 2
        assert "[IP-PUBLIC-1]" in anon
        assert "[IP-LINKLOCAL-1]" in anon
        assert "[IP-MULTICAST-1]" in anon
        assert "[IP-RESERVED-1]" in anon

    def test_invalid_ipv4_candidate_is_not_misclassified(self):
        anon, report = anonymize("peer=999.2.3.4")
        assert anon == "peer=999.2.3.4"
        assert report.replacements.get("Adresy IPv4", 0) == 0

    def test_uuid_alias_is_stable_and_other_secrets_are_irreversible(self):
        context = AnonymizationContext("identity")
        uuid = "123e4567-e89b-12d3-a456-426614174000"
        data = (
            f"disk={uuid} again={uuid} mac=aa:bb:cc:dd:ee:ff "
            "Serial: PF1A2B3C4D pass" "word=top-secret"
        )

        anon, _ = anonymize(data, context=context)

        assert anon.count("[UUID-1]") == 2
        assert "XX:XX:XX:XX:XX:XX" in anon
        assert "[SERIAL-REDACTED]" in anon
        assert "top-secret" not in anon
        assert "top-secret" not in context.reverse_map.values()
        assert "aa:bb:cc:dd:ee:ff" not in context.reverse_map.values()

    def test_idempotence_preserves_existing_aliases(self):
        context = AnonymizationContext("idempotent", primary_user="primary")
        payload = (
            "/home/[USER]/.cache /home/[USER-2]/.config "
            "[IP-PRIVATE-1] [IP-ANY] [UUID-1]"
        )
        again, _ = anonymize(payload, context=context)
        assert again == payload

    def test_contextual_resolution_is_selected_and_fail_closed(self):
        context = AnonymizationContext("resolution", primary_user="primary")
        payload, _ = anonymize("ls /home/alice/.cache", context=context)

        resolved = deanonymize(
            payload,
            context=context,
            allowed_aliases={"[USER-2]"},
        )
        assert resolved == "ls /home/alice/.cache"

        try:
            deanonymize(payload)
        except ResolutionError as exc:
            assert "mapping_context_required" in str(exc)
        else:
            raise AssertionError("numbered alias without its context should fail closed")

        try:
            deanonymize(payload, context=context, allowed_aliases=set())
        except ResolutionError as exc:
            assert "unselected_alias" in str(exc)
        else:
            raise AssertionError("unselected alias should fail closed")

        for value, allowed in (
            ("ls /home/[USER-99]/.cache", {"[USER-99]"}),
            ("listen [IP-ANY]", {"[IP-ANY]"}),
        ):
            try:
                deanonymize(value, context=context, allowed_aliases=allowed)
            except ResolutionError as exc:
                assert "unknown_or_semantic_alias" in str(exc)
            else:
                raise AssertionError("unknown or semantic alias should fail closed")

    def test_report_contains_digest_but_not_reverse_map(self):
        context = AnonymizationContext("report", primary_user="primary")
        payload, report = anonymize(
            "/home/alice/.cache peer=10.2.3.4",
            context=context,
        )
        report_text = repr(report)

        assert len(report.payload_sha256) == 64
        assert report.mapping_id == "report"
        assert "alice" not in report_text
        assert "10.2.3.4" not in report_text
        assert report.payload_sha256
        assert payload
