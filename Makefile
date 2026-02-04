# Red Letters Development Makefile
# Sprint 21: Verification gate + reproducible dev commands

.PHONY: dev dev-backend dev-gui clean-ports help verify test test-gui test-e2e test-e2e-real

# Default port for backend
BACKEND_PORT ?= 47200
GUI_PORT ?= 1420

help:
	@echo "Red Letters Development Commands"
	@echo "================================"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start both backend (full mode) and GUI"
	@echo "  make dev-backend  - Start only the backend (full mode)"
	@echo "  make dev-gui      - Start only the GUI"
	@echo "  make clean-ports  - Kill processes on ports $(BACKEND_PORT) and $(GUI_PORT)"
	@echo ""
	@echo "Verification (run before merge):"
	@echo "  make verify       - Run ALL verification gates (unit + E2E)"
	@echo "  make test         - Python backend tests only"
	@echo "  make test-gui     - GUI unit tests only (vitest)"
	@echo "  make test-e2e     - Playwright mocked tests only"
	@echo "  make test-e2e-real - Real backend smoke (requires running backend)"
	@echo ""
	@echo "Ports:"
	@echo "  Backend: $(BACKEND_PORT)"
	@echo "  GUI:     $(GUI_PORT)"

# Kill any process using the backend port
clean-ports:
	@echo "Cleaning up ports..."
	-@lsof -ti:$(BACKEND_PORT) | xargs -r kill -9 2>/dev/null || true
	-@lsof -ti:$(GUI_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "Ports cleaned."

# Start the backend in full mode (with translate/sources routes)
dev-backend: clean-ports
	@echo "Starting backend (full mode) on port $(BACKEND_PORT)..."
	python -m redletters engine start --port $(BACKEND_PORT)

# Start the GUI dev server
dev-gui:
	@echo "Starting GUI on port $(GUI_PORT)..."
	cd gui && npm run dev

# Start both backend and GUI
# Backend runs in background, GUI runs in foreground
dev: clean-ports
	@echo "Starting Red Letters development environment..."
	@echo ""
	@echo "Backend: http://127.0.0.1:$(BACKEND_PORT)"
	@echo "GUI:     http://localhost:$(GUI_PORT)"
	@echo ""
	@echo "Starting backend (full mode)..."
	@python -m redletters engine start --port $(BACKEND_PORT) &
	@sleep 2
	@echo "Starting GUI..."
	@cd gui && npm run dev

# ════════════════════════════════════════════════════════════════════════════
# VERIFICATION GATE - Run before every merge
# ════════════════════════════════════════════════════════════════════════════
#
# POLICY: Mocked suite must be 100% pass or we fix/remove tests before merging.
# If anyone wants to merge with failures, they must delete/skip with an issue
# link and an expiry date. Otherwise it becomes permanent trash.
#
# See: docs/TESTING.md for full policy

verify: test test-gui test-e2e
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "✓ ALL VERIFICATION GATES PASSED"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Ready to merge. For real-backend smoke (optional):"
	@echo "  make dev-backend  # in terminal 1"
	@echo "  make test-e2e-real  # in terminal 2"
	@echo ""

# Python backend tests
test:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Running Python backend tests..."
	@echo "════════════════════════════════════════════════════════════════════"
	pytest tests/ -v

# GUI unit tests (vitest)
test-gui:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Running GUI unit tests (vitest)..."
	@echo "════════════════════════════════════════════════════════════════════"
	cd gui && npm run test

# Playwright mocked E2E tests (no backend required)
test-e2e:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Running Playwright mocked E2E tests..."
	@echo "════════════════════════════════════════════════════════════════════"
	cd gui && npm run test:e2e

# Playwright real-backend smoke (requires running backend)
test-e2e-real:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Running Playwright real-backend smoke test..."
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "NOTE: Requires backend running on port $(BACKEND_PORT)"
	@echo ""
	cd gui && npm run test:e2e:real

# Real-backend smoke with auto-boot (CI mode)
test-e2e-real-boot:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "Running Playwright real-backend smoke (with auto-boot)..."
	@echo "════════════════════════════════════════════════════════════════════"
	cd gui && npm run test:e2e:real:boot

# Type checking
typecheck:
	mypy src/redletters/
	cd gui && npx tsc --noEmit
