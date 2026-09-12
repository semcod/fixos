# Integracja z lokalnym Registry

Dokument opisuje kontrakt wdrożeniowy, który ma zostać wykorzystany przez
`subactor/registry`. Nie wprowadza nowego formatu artefaktów: preferowane są
OCI artifacts (z digestem), SLSA/in-toto attestations oraz standardowe klienty
Git, PyPI i npm.

## Tryb lokalny

Registry przechowuje polityki i artefakty w SQLite oraz lokalnym content store.
Usługa powinna udostępniać operacje `publish`, `get`, `list`, `verify` i
`gc`, a Docker Compose ma zapewniać jedynie uruchomienie usługi i trwały
wolumen. Brak sieci nie może uniemożliwiać odczytu ani walidacji.

## Adaptery synchronizacji

Adapter Git synchronizuje repozytoria i commity; adapter PyPI pobiera metadane
i wheel/sdist; adapter npm pobiera metadata i tarball. Adaptery zapisują źródło,
wersję, digest i czas pobrania w SQLite, ale nie nadają same uprawnień merge.

## Zaufanie i rollback

Snapshot jest checkpointowany, haszowany i podpisywany. Validator sprawdza
podpis, issuer, predicate type, subject (repozytorium/ref/HEAD) oraz digest
SQLite. Nieudana walidacja pozostawia poprzedni snapshot aktywny i zwraca błąd;
nie wolno automatycznie wracać do niezaufanego JSON.
