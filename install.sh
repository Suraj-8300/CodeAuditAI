#!/usr/bin/env bash
# ==============================================================================
# CodeAuditAI — One-Line Installer & Setup Script
# ==============================================================================

set -e

echo ""
echo "🛡️  ========================================================"
echo "    CodeAuditAI — Autonomous Multi-Agent Code Review Studio"
echo "============================================================"
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.10+."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Found Python $PY_VERSION"

INSTALL_DIR="${HOME}/.codeaudit"

if [ -d "$INSTALL_DIR" ]; then
    echo "♻️  Existing installation found at $INSTALL_DIR. Updating to latest release..."
    git -C "$INSTALL_DIR" pull --ff-only || (echo "⚠️ Fast-forward pull failed; resetting to origin/main..." && git -C "$INSTALL_DIR" fetch origin main && git -C "$INSTALL_DIR" reset --hard origin/main)
else
    echo "📥 Cloning CodeAuditAI into $INSTALL_DIR..."
    git clone --depth=1 --branch main https://github.com/Suraj-8300/CodeAuditAI.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing and verifying dependencies..."
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .

# Create symlink in ~/.local/bin if available
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"
ln -sf "${INSTALL_DIR}/codeaudit" "${BIN_DIR}/codeaudit"

echo ""
echo "🎉 CodeAuditAI successfully installed!"
echo "   Binary linked to: ${BIN_DIR}/codeaudit"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "⚠️  Note: '${BIN_DIR}' is not currently in your system PATH."
    echo "   Add it by running:"
    echo "   export PATH=\"\${HOME}/.local/bin:\${PATH}\""
fi
echo ""
echo "🚀 To get started:"
echo "   1. Add your Google AI Studio API key:"
echo "      export GOOGLE_API_KEY=\"your-free-key\""
echo "   2. Launch the Web Review Studio:"
echo "      codeaudit web"
echo "   3. Or audit a repository directly in your terminal:"
echo "      codeaudit audit https://github.com/owner/repo"
echo ""
