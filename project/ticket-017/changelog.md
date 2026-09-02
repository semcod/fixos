# Ticket Changelog (ticket-017)

## [0.1.0] - 2026-09-01

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Authorized a bounded application change for context-preserving anonymization,
  faithful alias previews and fail-closed local alias resolution.

## Implemented

- Preserve useful home-path suffixes while assigning stable primary and foreign
  user aliases.
- Parse IPv4 values into semantic or stable category aliases without exposing
  subnet prefixes, and keep invalid address-like text unchanged.
- Keep UUID identity stable within a mapping context while redacting secrets,
  MAC values and serials irreversibly.
- Bind previews to the exact anonymized payload digest and keep alias brackets
  visible.
- Resolve contextual aliases only from the local map and an exact selected set;
  reject unknown, semantic or context-free numbered aliases.
- Route the legacy LLM-shell anonymizer through the shared implementation and
  cover it with a regression test.
- Match a non-`/home` platform home only at full path boundaries, so container
  root-account homes cannot corrupt conventional `/home` paths or longer names
  that merely share the same prefix.
- Recognize serialized whitespace delimiters before an isolated home path, so
  dictionary-form diagnostics cannot retain a nested executor home.
- Publish exact head `610bcb1d...` through PR #35 after all hosted and OneDev
  checks passed.
- Record protected Validator approval `5084141876`, merge `31f3e6ec...` and
  deletion of the remote ticket branch.
- Close the integrated ticket as `DONE / DONE` on the resulting default branch.
