# Archiwum artykułów i planów

> Te pliki są historycznymi materiałami redakcyjnymi z marca 2026. Nie są
> bieżącą listą zadań i mogą opisywać stan sprzed refaktoryzacji. Aktualne
> zadania znajdują się w [`../TODO.md`](../TODO.md), a wykonane prace w
> [`../CHANGELOG.md`](../CHANGELOG.md).

Artykuły o statusie projektów w organizacji [wronai](https://github.com/wronai), przygotowane do publikacji na WordPress.

## Struktura

Każdy plik `.md` to jeden artykuł z frontmatter YAML (kompatybilny z WordPress via WP REST API lub wtyczki importu Markdown).

## Artykuły

| Plik | Projekt | Temat |
|------|---------|-------|
| `fixos-project-status.md` | fixOS | Status projektu, metryki kodu, plan refaktoryzacji i roadmapa nowych funkcji |
| `fixos-refactoring-roadmap.md` | fixOS | Szczegółowy techniczny plan refaktoryzacji — rozbijanie god-functions, eliminacja duplikacji |
| `fixos-new-features-roadmap.md` | fixOS | Projekt nowych funkcji: plugin system, rollback, structured output, profiles, watch mode |

## Frontmatter

Każdy artykuł zawiera standardowy frontmatter WordPress:

```yaml
---
title: "Tytuł artykułu"
slug: url-slug
date: 2026-03-15
author: wronai
categories:
  - Projekty
tags:
  - fixOS
  - Python
excerpt: "Opis artykułu"
status: publish
---
```

## Publikacja

Artykuły można opublikować przez:

1. **WP REST API** — `POST /wp-json/wp/v2/posts` z contentem z pliku
2. **Plugin WP Markdown Import** — bezpośredni import plików `.md`
3. **Ręcznie** — skopiowanie treści do edytora WordPress (Gutenberg obsługuje markdown)
