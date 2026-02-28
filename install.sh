#!/bin/bash
# ─────────────────────────────────────────────────────────────
# claude-telegram — Quick installer
# Usage: bash install.sh <TOKEN> <CHAT_ID> <PROJECT_DIR>
# ─────────────────────────────────────────────────────────────
set -e

TOKEN="${1}"
CHAT_ID="${2}"
PROJECT_DIR="${3:-$HOME/mining_forensic}"
HOOKS_DIR="$HOME/.claude/hooks"
PLIST="$HOME/Library/LaunchAgents/com.mforensic.telegram-bot.plist"
USER=$(whoami)

if [[ -z "$TOKEN" || -z "$CHAT_ID" ]]; then
  echo "Usage: bash install.sh <TELEGRAM_TOKEN> <CHAT_ID> [PROJECT_DIR]"
  exit 1
fi

echo "📦 Instalando claude-telegram..."

# 1. Copiar scripts
mkdir -p "$HOOKS_DIR"
cp hooks/telegram-bot-daemon.py "$HOOKS_DIR/"
cp hooks/start-telegram-bot.sh  "$HOOKS_DIR/"
chmod +x "$HOOKS_DIR/start-telegram-bot.sh"

# Ajustar PROJECT_DIR en el daemon
sed -i '' "s|/Users/josemuniz/mining_forensic|$PROJECT_DIR|g" \
  "$HOOKS_DIR/telegram-bot-daemon.py"

# 2. Leer ANTHROPIC_API_KEY del entorno o ~/.zshrc
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-$(grep ANTHROPIC_API_KEY ~/.zshrc 2>/dev/null | tail -1 | cut -d'"' -f2)}"
if [[ -z "$ANTHROPIC_KEY" ]]; then
  echo "⚠️  ANTHROPIC_API_KEY no encontrada. Edita el plist manualmente después."
  ANTHROPIC_KEY="PENDIENTE"
fi

# 3. Crear LaunchAgent plist
cat > "$PLIST" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mforensic.telegram-bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$HOOKS_DIR/start-telegram-bot.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>$TOKEN</string>
        <key>TELEGRAM_CHAT_ID</key>
        <string>$CHAT_ID</string>
        <key>ANTHROPIC_API_KEY</key>
        <string>$ANTHROPIC_KEY</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>/tmp/mforensic-bot.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mforensic-bot-error.log</string>
</dict>
</plist>
PLISTEOF

# 4. Arrancar el bot
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "⏳ Esperando arranque..."
sleep 6

if grep -q "Red disponible" /tmp/mforensic-bot.log 2>/dev/null; then
  echo "✅ Bot corriendo. Revisa Telegram para confirmar."
else
  echo "❌ Algo falló. Revisa: cat /tmp/mforensic-bot.log && cat /tmp/mforensic-bot-error.log"
fi
