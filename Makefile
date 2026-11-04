# ══════════════════════════════════════════════════════════
#  fixOS – Makefile
#  Użycie: make <cel>
# ══════════════════════════════════════════════════════════

.PHONY: help install install-dev test test-unit test-e2e test-real test-fast \
        test-unit-fast test-unit-par test-quick lint format clean build docker-build \
        docker-test docker-test-fedora docker-test-ubuntu docker-test-debian \
        docker-test-arch docker-test-alpine docker-test-all \
        config-init run-scan run-fix publish

GOAL ?= goal
BUILD_OUT ?= dist

# ── Domyślna komenda ──────────────────────────────────────
help:
	@echo ""
	@echo "  fixOS – dostępne komendy Makefile"
	@echo ""
	@echo "  Instalacja:"
	@echo "    make install        instaluj paczkę (runtime)"
	@echo "    make install-dev    instaluj z zależnościami dev"
	@echo ""
	@echo "  Testy:"
	@echo "    make test           wszystkie testy (unit + e2e mock)"
	@echo "    make test-fast      testy z paralelizacją (4x szybciej)"
	@echo "    make test-quick     szybkie testy bez docker/slow"
	@echo "    make test-unit      tylko unit testy"
	@echo "    make test-unit-par  unit testy z paralelizacją (4 procesy)"
	@echo "    make test-e2e       e2e testy z mock LLM"
	@echo "    make test-real      e2e testy z prawdziwym API (wymaga .env)"
	@echo "    make test-cov       testy + raport pokrycia"
	@echo ""
	@echo "  Jakość kodu:"
	@echo "    make lint           sprawdź kod (ruff)"
	@echo "    make format         sformatuj kod (black)"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-build        zbuduj wszystkie obrazy testowe"
	@echo "    make docker-test-fedora  testuj na Fedora"
	@echo "    make docker-test-ubuntu  testuj na Ubuntu"
	@echo "    make docker-test-debian  testuj na Debian"
	@echo "    make docker-test-arch    testuj na Arch Linux"
	@echo "    make docker-test-alpine  testuj na Alpine"
	@echo "    make docker-test-all     testuj na wszystkich systemach"
	@echo "    make docker-audio        testuj broken-audio w Docker"
	@echo "    make docker-thumb        testuj broken-thumbnails w Docker"
	@echo "    make docker-full         testuj broken-full w Docker"
	@echo "    make docker-e2e          uruchom e2e testy w Docker"
	@echo ""
	@echo "  Uruchomienie:"
	@echo "    make config-init    utwórz plik .env"
	@echo "    make run-scan       skanuj system (wszystkie moduły)"
	@echo "    make run-fix        uruchom sesję naprawczą (HITL)"
	@echo ""
	@echo "  Paczka:"
	@echo "    make build          zbuduj dystrybucję PyPI"
	@echo "    make clean          usuń pliki tymczasowe"
	@echo ""

# ── Instalacja ────────────────────────────────────────────
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	@echo "✅ Zainstalowano z zależnościami dev"

# ── Testy ─────────────────────────────────────────────────
test: test-unit test-e2e

test-fast:
	@echo "⚡ Testy z paralelizacją (4 procesy)..."
	pytest tests/ -v --tb=short -n auto -m "not slow and not docker"

test-quick:
	@echo "⚡ Szybkie testy (bez slow/docker)..."
	pytest tests/unit tests/e2e/test_anonymization_layers.py tests/e2e/test_executor.py -v --tb=short -m "not slow and not docker"

test-unit:
	@echo "🧪 Unit testy..."
	pytest tests/unit/ -v --tb=short

test-unit-fast:
	@echo "🧪 Unit testy (paralelizacja - 4 procesy)..."
	pytest tests/unit/ -v --tb=short -n 4

test-unit-par:
	@echo "🧪 Unit testy (paralelizacja - auto, = CPU count)..."
	pytest tests/unit/ -v --tb=short -n auto

test-e2e:
	@echo "🧪 E2E testy (mock LLM)..."
	pytest tests/e2e/ -v --tb=short -k "not real_llm" -m "not slow and not docker"

test-real:
	@echo "🧪 E2E testy (prawdziwe API – wymaga .env)..."
	pytest tests/e2e/ -v --tb=short -k "real_llm"

test-cov:
	@echo "📊 Testy + raport pokrycia (z paralelizacją)..."
	pytest tests/ -v --tb=short --cov=fixos --cov-report=term-missing --cov-report=html:htmlcov -n auto -m "not slow"
	@echo "📊 Raport pokrycia: htmlcov/index.html"

# ── Jakość kodu ───────────────────────────────────────────
lint:
	ruff check fixos/ tests/ || true

format:
	black fixos/ tests/

# ── Docker ───────────────────────────────────────────────
docker-build:
	docker compose -f docker/docker-compose.yml build

docker-audio:
	docker compose -f docker/docker-compose.yml run --rm broken-audio

docker-thumb:
	docker compose -f docker/docker-compose.yml run --rm broken-thumbnails

docker-full:
	docker compose -f docker/docker-compose.yml run --rm broken-full

docker-e2e:
	docker compose -f docker/docker-compose.yml run --rm e2e-tests

# ── Multi-System Docker Tests ────────────────────────────
docker-test-fedora:
	@echo "🐧 Testing on Fedora..."
	docker compose -f docker/docker-compose.multi-system.yml run --rm test-fedora

docker-test-ubuntu:
	@echo "🐧 Testing on Ubuntu..."
	docker compose -f docker/docker-compose.multi-system.yml run --rm test-ubuntu

docker-test-debian:
	@echo "🐧 Testing on Debian..."
	docker compose -f docker/docker-compose.multi-system.yml run --rm test-debian

docker-test-arch:
	@echo "🐧 Testing on Arch Linux..."
	docker compose -f docker/docker-compose.multi-system.yml run --rm test-arch

docker-test-alpine:
	@echo "🐧 Testing on Alpine..."
	docker compose -f docker/docker-compose.multi-system.yml run --rm test-alpine

docker-test-all:
	@echo "🐧 Testing on all systems..."
	./docker/test-multi-system.sh

# ── Uruchomienie ──────────────────────────────────────────
config-init:
	fixos config init

run-scan:
	fixos scan

run-fix:
	fixos fix

# ── Paczka ───────────────────────────────────────────────
build:
	@echo "🔨 Budowanie paczki..."
	wellman run --root . --allow-primary-venv -- python -m build --outdir "$(BUILD_OUT)"
	@echo "✅ Paczka gotowa w $(BUILD_OUT)/"

publish:
	$(GOAL) -a

clean:
	@echo "🧹 Czyszczenie cache i artefaktów..."
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage htmlcov/ __pycache__ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✅ Wyczyszczono"
