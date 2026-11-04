"""Explainable storage decisions. Rules never authorize an unlink."""

from pathlib import Path

RULESET_VERSION = "1"
_ARCHIVES = {".zip", ".gz", ".xz", ".bz2", ".7z", ".rar", ".tar", ".tgz", ".zst"}
_DISKS = {
    ".img",
    ".iso",
    ".raw",
    ".qcow",
    ".qcow2",
    ".vdi",
    ".vmdk",
    ".vhd",
    ".vhdx",
    ".ova",
}
_MODELS = {".gguf", ".safetensors", ".onnx", ".pt", ".pth", ".ckpt"}
_DATABASES = {".db", ".sqlite", ".sqlite3", ".mdb", ".ibd", ".db-wal"}


def file_kind(path: Path, header: bytes = b"") -> str:
    """Use a bounded signature when available; extensions remain heuristics."""
    if header.startswith(b"QFI\xfb"):
        return "disk-image"
    if header.startswith(b"SQLite format 3\0"):
        return "database"
    if header.startswith(b"GGUF"):
        return "model"
    if header.startswith(b"\x7fELF"):
        return "executable"
    if path.suffix.lower() in _ARCHIVES and any(
        suffix.lower() in _DISKS for suffix in path.suffixes[:-1]
    ):
        return "disk-image"
    if header.startswith(
        (b"PK\x03\x04", b"\x1f\x8b", b"7z\xbc\xaf\x27\x1c", b"\xfd7zXZ\0")
    ):
        return "archive"
    suffix = path.suffix.lower()
    if suffix in _DISKS:
        return "disk-image"
    if suffix in _MODELS:
        return "model"
    if suffix in _DATABASES or path.name.endswith(("-wal", "-shm")):
        return "database"
    if suffix in _ARCHIVES:
        return "archive"
    if suffix in {".mp4", ".mkv", ".mov", ".webm", ".avi", ".wav", ".flac"}:
        return "media"
    if suffix in {".log", ".journal"} or path.name.startswith("core."):
        return "log-or-dump"
    return "other"


def decide_file(row: dict) -> dict:
    """Ordered rules: positive protection wins over every convenience heuristic."""
    path = Path(row["path"])
    parts = {part.lower() for part in path.parts}
    kind = row["kind"]
    decision, rule, reason, next_step = (
        "review",
        "USER_REVIEW",
        "Brak dowodu, że plik jest zbędny.",
        "Potwierdź przeznaczenie i możliwość odtworzenia przed decyzją.",
    )
    if row.get("active_swap"):
        decision, rule, reason = (
            "protected",
            "ACTIVE_SWAP",
            "Plik jest aktywnym swapem.",
        )
        next_step = "Zachowaj; zmiana swapu wymaga osobnej procedury administracyjnej."
    elif row.get("open_pids"):
        decision, rule, reason = (
            "protected",
            "OPEN_OR_MAPPED",
            "Plik jest otwarty lub mapowany przez proces.",
        )
        next_step = "Ustal rolę procesu; nie usuwaj jego danych podczas pracy."
    elif parts & {".ssh", ".gnupg", ".git", "localhistory", ".worktrees", ".subactor"}:
        decision, rule, reason = (
            "protected",
            "RECOVERY_OR_SOURCE",
            "Dane źródeł, kluczy, historii lub odzyskiwania.",
        )
        next_step = (
            "Zachowaj; potrzebne są dowody integracji i jawna polityka retencji."
        )
    elif any(part.startswith(("jetbrains", "pycharm", "intellij")) for part in parts):
        decision, rule, reason = (
            "protected",
            "IDE_STATE",
            "Dane IDE mogą zawierać Local History i stan odzyskiwania.",
        )
        next_step = "Użyj diagnostyki IDE; nazwa cache nie dowodzi odtwarzalności."
    elif kind == "database" or parts & {"postgresql", "postgres", "mysql", "mongodb"}:
        decision, rule, reason = (
            "protected",
            "DATABASE",
            "Baza danych lub jej dziennik może zawierać jedyną kopię danych.",
        )
        next_step = "Sprawdź właściciela usługi, spójność i kopię odtworzeniową."
    elif path.name.lower().startswith("swap") or path.suffix.lower() == ".swap":
        decision, rule, reason = (
            "protected",
            "POSSIBLE_SWAP",
            "Nazwa wskazuje na swap; brak aktywnego wpisu nie jest zgodą na usunięcie.",
        )
        next_step = "Sprawdź konfigurację systemu i aktywny swap."
    elif parts & {"backup", "backups", "bck", "snapshots"} or path.suffix.lower() in {
        ".bak",
        ".backup",
    }:
        decision, rule, reason = (
            "protected",
            "BACKUP",
            "Kopia zapasowa lub snapshot; nie potwierdzono innej kopii.",
        )
        next_step = "Sprawdź retencję i możliwość odtworzenia."
    elif parts & {"docker", "containerd", "containers", "overlay2"}:
        decision, rule, reason = (
            "manager-review",
            "CONTAINER_STORE",
            "Magazyn kontenerów ma współdzielone warstwy i zależności.",
        )
        next_step = "Sprawdź także zatrzymane kontenery, piny i natywny inventory; użyj menedżera."
    elif kind == "model" or parts & {".ollama", "ollama", "huggingface"}:
        decision, rule, reason = (
            "manager-review",
            "MODEL_STORE",
            "Wagi mogą być współdzielone przez aliasy i konfiguracje.",
        )
        next_step = (
            "Sprawdź manifesty, konfiguracje i użycie; wycofuj przez menedżera modeli."
        )
    elif kind == "disk-image":
        decision, rule, reason = (
            "manager-review",
            "IMAGE_DEPENDENCIES",
            "Obraz może być bazą VM, snapshotu lub wydania IMG.",
        )
        next_step = "Sprawdź backing chain, manifesty buildu i kwalifikowane wydania."
    elif parts & {"artifacts", "releases"}:
        decision, rule, reason = (
            "manager-review",
            "RELEASE_ARTIFACT",
            "Artefakt buildu lub wydania może być przypięty manifestem albo retencją.",
        )
        next_step = "Sprawdź kwalifikację, manifesty wejść i wyjść oraz natywną retencję projektu."
    elif (
        parts & {".config", ".local"} and "cache" not in parts and ".cache" not in parts
    ):
        decision, rule, reason = (
            "protected",
            "APPLICATION_STATE",
            "Trwały stan aplikacji; wiek pliku nie określa jego wartości.",
        )
        next_step = "Sprawdź właściciela danych i kontrakt retencji aplikacji."
    elif row.get("repository") and not parts & {"build", "dist", "target", ".cache"}:
        decision, rule, reason = (
            "protected",
            "REPOSITORY_DATA",
            "Plik znajduje się w repozytorium; może być śledzony lub unikalny.",
        )
        next_step = "Sprawdź status Git, właściciela ticketu i odtwarzalność."
    elif ".cache" in parts or "__pycache__" in parts:
        rule, reason = (
            "CACHE_REVIEW",
            "Ścieżka sugeruje cache; odtwarzalność wymaga potwierdzenia.",
        )
        next_step = (
            "Sprawdź aplikację, otwarte pliki i udokumentowaną politykę czyszczenia."
        )
    elif kind in {"archive", "media", "log-or-dump"}:
        rule, reason = (
            "LARGE_USER_FILE",
            "Duży plik do decyzji użytkownika; typ i wiek nie dowodzą zbędności.",
        )
    reasons = [reason]
    if row["link_count"] > 1:
        reasons.append("Hardlink: usunięcie jednej ścieżki nie zwolni bloków danych.")
    if row.get("sparse"):
        reasons.append("Plik rzadki: rozmiar logiczny przewyższa przydzielone bloki.")
    if row.get("age_days", 0) < 7:
        reasons.append(
            "Plik niedawno modyfikowany; zachowaj ostrożność przy ocenie użycia."
        )
    if row.get("process_visibility") != "complete":
        reasons.append(
            "Widoczność procesów niepełna: brak wykrytego użycia nie oznacza nieużywania."
        )
    return {
        "decision": decision,
        "rule_id": rule,
        "reasons": reasons,
        "next_step": next_step,
        "dependency_status": "active"
        if row.get("open_pids") or row.get("active_swap")
        else "unverified",
        "automatic_delete": False,
        "reclaimable_bytes": None,
        "reclaim_upper_bound_bytes": row["allocated_bytes"]
        if decision == "review" and row["link_count"] == 1
        else 0,
    }
