#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Risalah Codespaces Setup ==="

# 1. Install opencode CLI
if ! command -v opencode &>/dev/null; then
  echo "[1] Installing opencode..."
  curl -fsSL https://opencode.ai/install | bash
  export PATH="$HOME/.opencode/bin:$PATH"
  # Add to shell profile
  echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.bashrc
  echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.zshrc
else
  echo "[1] opencode already installed"
fi

# 2. Symlink opencode configs from repo to global ~/.config/opencode/
echo "[2] Symlinking opencode skills, agents, commands..."
mkdir -p ~/.config/opencode

# Backup existing global config if not a symlink
if [ -f ~/.config/opencode/opencode.json ] && [ ! -L ~/.config/opencode/opencode.json ]; then
  cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak
  echo "  -> backed up existing opencode.json"
fi

# Copy global config (generated inline, not symlinked)
cat > ~/.config/opencode/opencode.json << 'GLOBALCONFIG'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/deepseek-v4-flash-free",
  "plugin": ["@bybrawe/opencode-loop", "opencode-auto-resume", "@tarquinen/opencode-dcp"],
  "mcp": {
    "context7": {
      "type": "local",
      "command": ["npx", "-y", "@upstash/context7-mcp"]
    }
  },
  "agent": {
    "plan": {
      "description": "Deep reasoning for planning & architecture",
      "model": "opencode/deepseek-v4-flash-free"
    },
    "build": {
      "description": "Main coding with powerful fallback",
      "model": "opencode/deepseek-v4-flash-free"
    },
    "explore": {
      "description": "Lightweight codebase exploration",
      "mode": "subagent",
      "model": "opencode/deepseek-v4-flash-free"
    }
  }
}
GLOBALCONFIG

# Symlink skills, agents, commands, plugins
for dir in skills agents commands plugins; do
  if [ -d "$REPO_DIR/.devcontainer/opencode/$dir" ]; then
    rm -rf ~/.config/opencode/"$dir"
    ln -sf "$REPO_DIR/.devcontainer/opencode/$dir" ~/.config/opencode/"$dir"
    echo "  -> symlinked ~/.config/opencode/$dir"
  fi
done

# Symlink user agents (ask-* skills)
if [ -d "$REPO_DIR/.devcontainer/user-agents" ]; then
  mkdir -p ~/.agents
  rm -rf ~/.agents/skills
  ln -sf "$REPO_DIR/.devcontainer/user-agents" ~/.agents/skills
  echo "  -> symlinked ~/.agents/skills"
fi

# 3. Install opencode plugins
echo "[3] Installing opencode plugins..."
opencode plug "@bybrawe/opencode-loop" -g 2>/dev/null || true
opencode plug "opencode-auto-resume" -g 2>/dev/null || true
opencode plug "@tarquinen/opencode-dcp" -g 2>/dev/null || true

# 4. Setup Python virtual environment
echo "[4] Setting up Python venv..."
if [ ! -d "$REPO_DIR/.venv" ]; then
  python3 -m venv "$REPO_DIR/.venv"
  source "$REPO_DIR/.venv/bin/activate"
  pip install --upgrade pip
  pip install -r "$REPO_DIR/requirements.txt" 2>/dev/null || pip install fastapi uvicorn celery redis streamlit python-docx python-multipart aiofiles
  echo "  -> venv created & deps installed"
else
  echo "  -> venv already exists"
fi

# 5. Docker Compose services
echo "[5] Docker Compose services ready"
echo "  -> Start with: docker compose up -d"
echo "  -> (Redis + Celery worker auto-start via docker)"


# === Summary ===
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Set Codespaces secrets di GitHub (Settings > Secrets > Codespaces):"
echo "  OPENCODE_API_KEY    = (ambil dari https://opencode.ai/auth)"
echo "  GROQ_API_KEY        = gsk_..."
echo "  GEMINI_API_KEY      = AIzaSy..."
echo "  OPENROUTER_API_KEY  = (opsional)"
echo ""
echo "Lalu di terminal Codespaces:"
echo "  opencode auth login --provider opencode"
echo "  source .venv/bin/activate"
echo "  opencode"
