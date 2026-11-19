"""
Provider management commands for fixOS CLI.
"""

from __future__ import annotations

from typing import TypedDict

import click

from fixos.constants import UI_BORDER_WIDTH


class ProviderInfo(TypedDict):
    """Metadata describing a supported LLM provider."""

    name: str
    url: str
    key_url: str
    env_var: str
    models: list[str]
    pricing: str


PROVIDERS_INFO: dict[str, ProviderInfo] = {
    "gemini": {
        "name": "Google Gemini",
        "url": "https://ai.google.dev/",
        "key_url": "https://aistudio.google.com/app/apikey",
        "env_var": "GEMINI_API_KEY",
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"],
        "pricing": "FREE",
    },
    "groq": {
        "name": "Groq",
        "url": "https://groq.com/",
        "key_url": "https://console.groq.com/keys",
        "env_var": "GROQ_API_KEY",
        "models": ["llama3-8b-8192", "mixtral-8x7b", "gemma-7b-it"],
        "pricing": "FREE",
    },
    "mistral": {
        "name": "Mistral AI",
        "url": "https://mistral.ai/",
        "key_url": "https://console.mistral.ai/api-keys/",
        "env_var": "MISTRAL_API_KEY",
        "models": ["mistral-tiny", "mistral-small", "mistral-medium"],
        "pricing": "PAID",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "url": "https://www.anthropic.com/",
        "key_url": "https://console.anthropic.com/settings/keys",
        "env_var": "ANTHROPIC_API_KEY",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "pricing": "PAID",
    },
    "together": {
        "name": "Together AI",
        "url": "https://www.together.ai/",
        "key_url": "https://api.together.xyz/settings/api-keys",
        "env_var": "TOGETHER_API_KEY",
        "models": ["llama-3-8b", "mixtral-8x7b", "qwen-2.5-7b"],
        "pricing": "PAID",
    },
    "cohere": {
        "name": "Cohere",
        "url": "https://cohere.com/",
        "key_url": "https://dashboard.cohere.com/api-keys",
        "env_var": "COHERE_API_KEY",
        "models": ["command-r", "command-r-plus", "command"],
        "pricing": "FREE",
    },
    "deepseek": {
        "name": "DeepSeek",
        "url": "https://www.deepseek.com/",
        "key_url": "https://platform.deepseek.com/api_keys",
        "env_var": "DEEPSEEK_API_KEY",
        "models": ["deepseek-chat", "deepseek-coder"],
        "pricing": "PAID",
    },
    "cerebras": {
        "name": "Cerebras",
        "url": "https://cerebras.ai/",
        "key_url": "https://cloud.cerebras.ai/platform",
        "env_var": "CEREBRAS_API_KEY",
        "models": ["llama3.1-8b"],
        "pricing": "PAID",
    },
    "openai": {
        "name": "OpenAI",
        "url": "https://openai.com/",
        "key_url": "https://platform.openai.com/api-keys",
        "env_var": "OPENAI_API_KEY",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "pricing": "PAID",
    },
    "xai": {
        "name": "xAI (Grok)",
        "url": "https://x.ai/",
        "key_url": "https://console.x.ai/",
        "env_var": "XAI_API_KEY",
        "models": ["grok-1"],
        "pricing": "PAID",
    },
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/",
        "key_url": "https://openrouter.ai/keys",
        "env_var": "OPENROUTER_API_KEY",
        "models": ["meta-llama/llama-3-8b", "anthropic/claude-3-opus"],
        "pricing": "PAID",
    },
    "ollama": {
        "name": "Ollama (local)",
        "url": "https://ollama.ai/",
        "key_url": "N/A - local deployment",
        "env_var": "OLLAMA_HOST",
        "models": ["llama3", "mistral", "codellama"],
        "pricing": "FREE",
    },
}


def _echo_providers_header() -> None:
    click.echo(click.style("\nDostępni providerzy LLM:", fg="cyan", bold=True))
    click.echo(click.style("═" * min(UI_BORDER_WIDTH, 60), fg="cyan"))
    click.echo()


def _echo_provider_entry(
    provider_id: str,
    info: ProviderInfo,
    active_provider: str | None,
    *,
    include_details: bool,
) -> None:
    pricing = info.get("pricing", "PAID")
    badge = click.style(f"[{pricing}]", fg="green" if pricing == "FREE" else "yellow")
    active_marker = (
        click.style(" [aktywny]", fg="green", bold=True)
        if provider_id == active_provider
        else ""
    )
    name = click.style(info["name"], fg="yellow", bold=True)
    click.echo(f"  {badge} {name}{active_marker}")
    click.echo(f"    ID      : {provider_id}")
    if include_details:
        click.echo(f"    Strona  : {info['url']}")
    click.echo(
        f"    Klucz   : {click.style(info['key_url'], fg='blue', underline=True)}"
    )
    click.echo(f"    Zmienna : {info.get('env_var', 'N/A')}")
    if include_details:
        click.echo(f"    Modele  : {', '.join(info['models'][:3])}")
    click.echo()


def _echo_usage_footer(lines: tuple[str, ...]) -> None:
    click.echo(click.style("Użycie:", fg="green", bold=True))
    for line in lines:
        click.echo(f"  {line}")
    click.echo()


@click.command("llm")
@click.option("--free", is_flag=True, help="Tylko darmowe providery")
def llm_providers(free: bool) -> None:
    """
    Lista dostępnych providerów LLM.

    \b
    Pokazuje wszystkich providerów z linkami do kluczy API.
    Użyj --free aby zobaczyć tylko darmowe opcje.
    """
    from fixos.config import FixOsConfig

    cfg = FixOsConfig.load()
    _echo_providers_header()

    for provider_id, info in PROVIDERS_INFO.items():
        if free and info.get("pricing") != "FREE":
            continue
        _echo_provider_entry(
            provider_id,
            info,
            cfg.provider,
            include_details=True,
        )

    _echo_usage_footer(
        (
            "fixos token set <KLUCZ>  # auto-detect providera",
            "fixos fix --provider <ID>  # wymuszony provider",
        )
    )


@click.command("providers")
def providers() -> None:
    """
    Lista providerów LLM z oznaczeniem FREE/PAID.
    """
    from fixos.config import FixOsConfig

    cfg = FixOsConfig.load()
    _echo_providers_header()

    for provider_id, info in PROVIDERS_INFO.items():
        _echo_provider_entry(
            provider_id,
            info,
            cfg.provider,
            include_details=False,
        )

    _echo_usage_footer(
        (
            "fixos llm  # szczegółowa lista z modelami",
            "fixos token set <KLUCZ>  # zapisz klucz API",
        )
    )


@click.command("test-llm")
@click.option("--provider", "-p", default=None, help="Provider do testu")
@click.option("--token", "-t", default=None, envvar="API_KEY", help="Token API")
@click.option("--model", "-m", default=None, help="Model")
@click.option("--no-banner", is_flag=True, help="Ukryj baner")
def test_llm(
    provider: str | None,
    token: str | None,
    model: str | None,
    no_banner: bool,
) -> None:
    """
    Test połączenia z LLM.

    \b
    Wysyła proste zapytanie "Hello" i wyświetla odpowiedź.
    Sprawdza czy token działa i provider jest dostępny.

    \b
    Przykłady:
      fixos test-llm                    # użyj domyślnej konfiguracji
      fixos test-llm -p openai -t sk-...  # test konkretnego providera
    """
    from fixos.config import FixOsConfig
    from fixos.providers.llm import LLMClient, LLMError

    if not no_banner:
        from fixos.cli.shared import BANNER

        click.echo(click.style(BANNER, fg="cyan"))

    cfg = FixOsConfig.load()
    if provider:
        cfg.provider = provider
    if token:
        cfg.api_key = token
    if model:
        cfg.model = model

    click.echo(click.style("\nTest połączenia z LLM...", fg="yellow", bold=True))
    click.echo(f"  Provider : {cfg.provider}")
    click.echo(f"  Model    : {cfg.model}")
    key_status = (
        click.style("skonfigurowany", fg="green")
        if cfg.api_key
        else click.style("BRAK", fg="red", bold=True)
    )
    click.echo(f"  Klucz    : {key_status}")

    if not cfg.api_key:
        click.echo(
            click.style(
                "\nBłąd: Brak klucza API. Użyj: fixos token set <KLUCZ>", fg="red"
            )
        )
        return

    try:
        llm = LLMClient(cfg)
        click.echo(click.style("\nWysyłam testowe zapytanie...", fg="cyan"))

        response = llm.chat(
            [
                {
                    "role": "user",
                    "content": "Hello! Please respond with 'Hello from fixOS test.'",
                }
            ],
            max_tokens=50,
        )

        click.echo(click.style("✅ Połączenie udane!", fg="green", bold=True))
        click.echo("\nOdpowiedź LLM:")
        click.echo(f"  {response.strip()}")
        click.echo(f"\nZużyte tokeny: {llm.total_tokens}")

    except LLMError as exc:
        click.echo(click.style(f"\n❌ Błąd połączenia: {exc}", fg="red"))
        click.echo("\nMożliwe przyczyny:")
        click.echo("  - Nieprawidłowy klucz API")
        click.echo("  - Problem z połączeniem internetowym")
        click.echo("  - Provider niedostępny")
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        click.echo(click.style(f"\n❌ Nieoczekiwany błąd: {exc}", fg="red"))
