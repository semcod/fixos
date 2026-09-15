"""
Natural language command (ask) for fixOS CLI
"""

import subprocess
from contextlib import suppress

import click
import yaml

from fixos.agent.session_core import package_cleanup_guard

_PACKAGE_TERMS = (
    "pakiet",
    "package",
    "packages",
    "autoremove",
    "debuginfo",
    "dnf",
    "apt",
    "rpm",
    "pacman",
)
_PACKAGE_ACTION_TERMS = (
    "usun",
    "usuń",
    "remove",
    "delete",
    "clean",
    "wyczysc",
    "wyczyść",
    "sprawdz",
    "sprawdź",
    "pokaz",
    "pokaż",
    "list",
    "lista",
    "przejrzyj",
    "triage",
)
_PACKAGE_TRIAGE_COMMAND = ("fixos", ["cleanup", "--full", "--dry-run", "--json"])


def _is_package_triage_request(prompt_lower: str) -> bool:
    """Recognize package cleanup/review requests without authorizing removal."""
    return any(term in prompt_lower for term in _PACKAGE_TERMS) and any(
        term in prompt_lower for term in _PACKAGE_ACTION_TERMS
    )


@click.command("ask")
@click.argument("prompt")
@click.option("--dry-run", is_flag=True, default=False, help="Symuluj bez wykonania")
def ask(prompt, dry_run) -> None:
    """Wykonaj polecenie w języku naturalnym."""
    _handle_natural_command(prompt, dry_run)


def _match_heuristic_command(prompt_lower: str) -> object | None:
    """
    Match user prompt against heuristic keyword mappings.
    Returns:
        - str: Direct shell command
        - tuple: (program, args) for subprocess
        - None: No match found
    """
    is_docker = any(
        kw in prompt_lower
        for kw in ["docker", "kontener", "kontenery", "container", "containers"]
    )
    is_audio = any(
        kw in prompt_lower
        for kw in [
            "audio",
            "dzwiek",
            "dzwięk",
            "dźwięk",
            "sound",
            "glosnik",
            "głośnik",
            "mikrofon",
        ]
    )
    is_network = any(
        kw in prompt_lower
        for kw in ["siec", "sieć", "network", "internet", "wifi", "eth0", "wlan"]
    )
    is_security = any(
        kw in prompt_lower
        for kw in ["bezpieczenstwo", "bezpieczeństwo", "security", "firewall", "porty"]
    )

    # Package cleanup is always an inventory-only JSON dry-run. This branch is
    # intentionally before Docker routing so an ambiguous "pakiety docker"
    # request cannot become a container-removal command.
    if _is_package_triage_request(prompt_lower):
        return _PACKAGE_TRIAGE_COMMAND

    # 1. Docker-specific actions
    if is_docker:
        if any(kw in prompt_lower for kw in ["wylacz", "wyłącz", "usun", "usuń", "rm", "remove", "delete"]):
            return "docker ps -aq | xargs -r docker rm -f"
        if any(kw in prompt_lower for kw in ["stop", "zatrzymaj"]):
            return "docker ps -aq | xargs -r docker stop"
        if any(kw in prompt_lower for kw in ["lista", "list", "ps", "pokaz", "pokaż"]):
            return ("docker", ["ps", "-a"])
        return ("docker", ["ps", "-aq"])

    # 2. Audio-specific actions
    if is_audio:
        if any(kw in prompt_lower for kw in ["fix", "napraw", "naprawa"]):
            return ("fixos", ["fix", "--modules", "audio"])
        return ("fixos", ["scan", "--modules", "audio"])

    # 3. Network-specific actions
    if is_network:
        if any(kw in prompt_lower for kw in ["fix", "napraw", "naprawa"]):
            return ("fixos", ["fix", "--modules", "system"])
        return ("fixos", ["scan", "--modules", "system"])

    # 4. Security-specific actions
    if is_security:
        if any(kw in prompt_lower for kw in ["fix", "napraw", "naprawa"]):
            return ("fixos", ["fix", "--modules", "security"])
        return ("fixos", ["scan", "--modules", "security"])

    # 5. General system actions (when no specific domain is targeted)
    if any(kw in prompt_lower for kw in ["scan", "diagnostyka", "zlap", "bledy", "błędy", "errors"]):
        return ("fixos", ["scan"])
    if any(kw in prompt_lower for kw in ["fix", "napraw", "naprawa"]):
        return ("fixos", ["fix"])

    return None


def _format_command(matched_cmd: object) -> str:
    """Convert matched command to string format."""
    if isinstance(matched_cmd, str):
        return matched_cmd
    elif isinstance(matched_cmd, (list, tuple)):
        cmd_program = matched_cmd[0]
        cmd_args = matched_cmd[1] if len(matched_cmd) > 1 else []
        return " ".join([str(cmd_program)] + [str(a) for a in cmd_args])
    return str(matched_cmd)


def _build_output_dict(
    status: str,
    prompt: str,
    source: str,
    command: str,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    llm: str | None = None,
    reason: str | None = None,
    message: str | None = None,
    error: str | None = None,
) -> dict:
    """Build standardized output dictionary for YAML serialization."""
    output = {
        "status": status,
        "prompt": prompt,
        "source": source,
        "command": command,
    }
    if exit_code != 0 or status == "failed":
        output["exit_code"] = exit_code
    if stdout:
        output["stdout"] = stdout
    if stderr:
        output["stderr"] = stderr
    if llm is not None:
        output["llm"] = llm
    if reason:
        output["reason"] = reason
        output["message"] = message
    if error:
        output["error"] = error
    return output


def _execute_heuristic_command(cmd_str: str, prompt: str, dry_run: bool, cfg) -> None:
    """Execute a heuristic-matched command and output result."""

    package_guard = package_cleanup_guard(cmd_str)
    if package_guard:
        output = _build_output_dict(
            status="dry_run" if dry_run else "blocked",
            prompt=prompt,
            source="heuristics",
            command=cmd_str,
            reason=package_guard,
            message=(
                "Czyszczenie pakietów wymaga listy dokładnych celów, podglądu "
                "transakcji i osobnego potwierdzenia; operacja zbiorcza została zablokowana."
            ),
        )
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
        return

    if dry_run:
        output = _build_output_dict(
            status="dry_run",
            prompt=prompt,
            source="heuristics",
            command=cmd_str,
            llm=None,
        )
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
        return

    try:
        result = subprocess.run(
            cmd_str, capture_output=True, text=True, shell=True, check=False
        )

        output = _build_output_dict(
            status="success" if result.returncode == 0 else "failed",
            prompt=prompt,
            source="heuristics",
            command=cmd_str,
            exit_code=result.returncode,
            stdout=result.stdout if result.stdout else "",
            stderr=result.stderr if result.stderr else "",
        )

        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))

        # Optional LLM validation
        if cfg.api_key and result.returncode == 0:
            with suppress(Exception):
                _validate_result_with_llm(prompt, cmd_str, result, cfg)

    except Exception as e:  # noqa: BLE001
        output = _build_output_dict(
            status="error",
            prompt=prompt,
            source="heuristics",
            command=cmd_str,
            error=str(e),
            llm=None,
        )
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))


def _execute_with_llm(prompt: str, dry_run: bool, cfg) -> None:
    """Generate and execute command using LLM when no heuristic match found."""
    from fixos.providers.llm import LLMClient

    llm_provider = f"{cfg.provider}/{cfg.model}"

    try:
        llm = LLMClient(cfg)

        # Prompt for command generation
        llm_prompt = f"""Jesteś asystentem CLI fixOS. Użytkownik wpisał: '{prompt}'
Wybierz najlepszą, bezpieczną komendę systemową Linux do wykonania.
ZASADY BEZPIECZEŃSTWA:
- NIGDY nie proponuj poleceń usuwania pakietów ani autoremove (np. 'apt autoremove'), chyba że użytkownik wprost o to poprosił.
- NIGDY nie proponuj poleceń destrukcyjnych kasujących dane użytkownika lub środowisko IDE.
- Preferuj polecenia diagnostyczne lub sprawdzające stan.
Odpowiedz TYLKO komendą (bez żadnego dodatkowego tekstu).
Przykłady:
- "wyłącz docker" → docker ps -aq | xargs -r docker stop
- "pokaż procesy" → ps aux
- "sprawdź sieć" → ip addr
- "napraw dźwięk" → fixos fix --modules audio
- "diagnostyka" → fixos scan
- "usuń pakiety" → fixos cleanup --full --dry-run --json
"""
        resp = llm.chat([{"role": "user", "content": llm_prompt}], max_tokens=200)
        cmd_str = resp.strip().split("\n")[0].strip()
        cmd_str = cmd_str.strip("`").strip()

        if not cmd_str or len(cmd_str) <= 2:
            output = {
                "status": "error",
                "reason": "llm_empty_response",
                "message": "LLM nie zwrócił komendy",
            }
            click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
            return

        package_guard = package_cleanup_guard(cmd_str)
        if package_guard:
            output = _build_output_dict(
                status="dry_run" if dry_run else "blocked",
                prompt=prompt,
                source="llm",
                command=cmd_str,
                reason=package_guard,
                message=(
                    "Zablokowano zbiorcze czyszczenie pakietów. Najpierw wymagane są "
                    "dokładne cele ze skanu, podgląd transakcji i jawne potwierdzenie."
                ),
                llm=llm_provider,
            )
            click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
            return

        # Safety validation: check for dangerous commands
        from fixos.platform_utils import is_dangerous, is_interactive_blocker

        danger = is_dangerous(cmd_str)
        if danger:
            output = _build_output_dict(
                status="blocked",
                prompt=prompt,
                source="llm",
                command=cmd_str,
                reason="dangerous_command",
                message=f"Zablokowano niebezpieczną komendę: {danger}",
                llm=llm_provider,
            )
            click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
            return

        blocker = is_interactive_blocker(cmd_str)
        if blocker:
            output = _build_output_dict(
                status="blocked",
                prompt=prompt,
                source="llm",
                command=cmd_str,
                reason="interactive_blocker",
                message=f"Komenda wymaga sesji interaktywnej: {blocker}",
                llm=llm_provider,
            )
            click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
            return

        if dry_run:
            output = _build_output_dict(
                status="dry_run",
                prompt=prompt,
                source="llm",
                command=cmd_str,
                llm=llm_provider,
            )
            click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
            return

        # Safety: modifying commands require confirmation in interactive session or are blocked non-interactively
        import sys

        modifying_keywords = [
            "sudo",
            "rm ",
            "apt",
            "dnf",
            "pacman",
            "systemctl",
            "kill",
            "pip uninstall",
        ]
        is_modifying = any(kw in cmd_str.lower() for kw in modifying_keywords)

        if is_modifying:
            if sys.stdin.isatty():
                click.echo(
                    click.style(
                        f"\n⚠️  Wygenerowano komendę modyfikującą system:\n   {cmd_str}\n",
                        fg="yellow",
                        bold=True,
                    )
                )
                if not click.confirm(
                    "Czy na pewno chcesz wykonać to polecenie?", default=False
                ):
                    output = _build_output_dict(
                        status="cancelled",
                        prompt=prompt,
                        source="llm",
                        command=cmd_str,
                        message="Anulowano przez użytkownika",
                        llm=llm_provider,
                    )
                    click.echo(
                        yaml.dump(output, default_flow_style=False, allow_unicode=True)
                    )
                    return
            else:
                output = _build_output_dict(
                    status="blocked",
                    prompt=prompt,
                    source="llm",
                    command=cmd_str,
                    reason="requires_confirmation",
                    message="Komenda modyfikująca system wymaga interaktywnego potwierdzenia użytkownika.",
                    llm=llm_provider,
                )
                click.echo(
                    yaml.dump(output, default_flow_style=False, allow_unicode=True)
                )
                return

        # Execute the generated command
        result = subprocess.run(
            cmd_str, capture_output=True, text=True, shell=True, check=False
        )
        output = _build_output_dict(
            status="success" if result.returncode == 0 else "failed",
            prompt=prompt,
            source="llm",
            command=cmd_str,
            exit_code=result.returncode,
            stdout=result.stdout if result.stdout else "",
            stderr=result.stderr if result.stderr else "",
            llm=llm_provider,
        )
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))

        # Validate result
        _validate_result_with_llm(prompt, cmd_str, result, cfg)

    except Exception as e:  # noqa: BLE001
        output = {
            "status": "error",
            "reason": "llm_error",
            "message": str(e),
            "hint": 'fixos ask "wylacz wszystkie kontenery docker"',
        }
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))


def _handle_natural_command(prompt: str, dry_run: bool = False) -> None:
    """
    Handle natural language commands with heuristic matching and LLM fallback.
    """
    from fixos.config import FixOsConfig

    prompt_lower = prompt.lower()

    # Stage 1: Try heuristic matching
    matched_cmd = _match_heuristic_command(prompt_lower)

    if matched_cmd:
        # Heuristic match found - execute directly
        cmd_str = _format_command(matched_cmd)
        cfg = FixOsConfig.load()
        _execute_heuristic_command(cmd_str, prompt, dry_run, cfg)
        return

    # Stage 2: No heuristic match - use LLM
    cfg = FixOsConfig.load()
    if not cfg.api_key:
        output = {
            "status": "error",
            "reason": "no_api_key",
            "message": "Brak klucza API. Użyj: fixos token set <KLUCZ>",
            "hint": 'fixos ask "wylacz wszystkie kontenery docker"',
        }
        click.echo(yaml.dump(output, default_flow_style=False, allow_unicode=True))
        return

    _execute_with_llm(prompt, dry_run, cfg)


def _validate_result_with_llm(prompt: str, cmd_str: str, result, cfg) -> None:
    """Validate command result using LLM - generates check command and assesses outcome."""
    from fixos.providers.llm import LLMClient

    try:
        llm = LLMClient(cfg)
        llm_provider = f"{cfg.provider}/{cfg.model}"

        # Get stdout for validation (limit 2000 chars)
        stdout_preview = result.stdout[:2000] if result.stdout else "(puste)"

        # LLM generates check command
        check_prompt = f"""Jesteś asystentem CLI. Użytkownik chciał: "{prompt}"
Wykonana komenda: {cmd_str}
Wynik (stdout):
{stdout_preview}

Wynik (stderr): {result.stderr[:500] if result.stderr else "(brak)"}
Exit code: {result.returncode}

Wygeneruj komendę Linux która sprawdzi czy oczekiwany efekt został osiągnięty.
Odpowiedz TYLKO komendą (bez żadnego dodatkowego tekstu).
Przykłady:
- "wyłącz docker" → docker ps -a
- "zatrzymaj usługę" → systemctl status usługa
- "sprawdź sieć" → ip addr
- "napraw dźwięk" → pactl info
"""

        check_cmd_resp = llm.chat(
            [{"role": "user", "content": check_prompt}], max_tokens=200
        )
        check_cmd = check_cmd_resp.strip().split("\n")[0].strip()
        check_cmd = check_cmd.strip("`").strip()

        if not check_cmd or len(check_cmd) <= 2:
            return

        # Verification command must be strictly read-only and safe
        from fixos.platform_utils import is_dangerous

        if is_dangerous(check_cmd) or any(
            bad in check_cmd.lower()
            for bad in ["sudo", "rm ", "apt", "dnf", "pacman", "kill", "mkfs", "dd "]
        ):
            return

        # Execute check command
        check_result = subprocess.run(
            check_cmd, capture_output=True, text=True, shell=True, check=False
        )

        # Now assess the result
        validation_prompt = f"""Jesteś walidatorem wyników poleceń systemowych.
Oczekiwany efekt: "{prompt}"
Komenda wykonana: {cmd_str}
Wynik wykonania (stdout): {stdout_preview}

Komenda sprawdzająca: {check_cmd}
Wynik sprawdzenia (stdout): {check_result.stdout[:2000] if check_result.stdout else "(puste)"}
Wynik sprawdzenia (stderr): {check_result.stderr[:500] if check_result.stderr else "(brak)"}

Odpowiedz w formacie YAML:
validation:
  success: true/false - czy komenda osiągnęła to co użytkownik chciał
  interpretation: "krótka interpretacja wyniku"
  user_intent_met: true/false - czy oczekiwania użytkownika zostały spełnione
  suggestion: "opcjonalna sugestia jeśli coś poszło nie tak"
"""

        resp = llm.chat(
            [{"role": "user", "content": validation_prompt}], max_tokens=500
        )

        # Try to parse YAML from response
        try:
            yaml_start = resp.find("---")
            yaml_content = resp[yaml_start:] if yaml_start >= 0 else resp

            validation = yaml.safe_load(yaml_content)
            if validation and "validation" in validation:
                # Add check command info
                validation["validation"]["check_command"] = check_cmd
                validation["validation"]["check_result"] = (
                    check_result.stdout[:500] if check_result.stdout else ""
                )
                validation["validation"]["llm_provider"] = llm_provider
                click.echo(
                    yaml.dump(
                        {"validation": validation["validation"]},
                        default_flow_style=False,
                        allow_unicode=True,
                    )
                )
                return
        except Exception:  # noqa: BLE001, S110
            pass

        # Fallback: show check command info
        click.echo(
            yaml.dump(
                {
                    "validation": {
                        "llm_provider": llm_provider,
                        "check_command": check_cmd,
                        "check_result": check_result.stdout[:500]
                        if check_result.stdout
                        else "",
                        "raw_response": resp[:500],
                    }
                },
                default_flow_style=False,
                allow_unicode=True,
            )
        )
    except Exception:  # noqa: BLE001, S110
        pass
