#!/bin/bash
# ─────────────────────────────────────────────────────────────
# claude-telegram — Quick installer
# Usage: bash install.sh <TOKEN> <CHAT_ID> <PROJECT_DIR>
#
# TOKEN      : Telegram bot token de @BotFather
# CHAT_ID    : Número de chat (solo dígitos, ej: 6799432135)
# PROJECT_DIR: Ruta ABSOLUTA al proyecto (ej: /Users/tu/proyecto)
# ─────────────────────────────────────────────────────────────
set -e

TOKEN="${1}"
CHAT_ID="${2}"
PROJECT_DIR="${3}"
HOOKS_DIR="$HOME/.claude/hooks"
PLIST="$HOME/Library/LaunchAgents/com.mforensic.telegram-bot.plist"

# ── Validaciones ──────────────────────────────────────────────
if [[ -z "$TOKEN" || -z "$CHAT_ID" || -z "$PROJECT_DIR" ]]; then
  echo "❌ Uso: bash install.sh <TOKEN> <CHAT_ID> <PROJECT_DIR>"
  echo "   TOKEN      → token de @BotFather (ej: 1234567890:AAGya5M...)"
  echo "   CHAT_ID    → número de chat del getUpdates (ej: 6799432135)"
  echo "   PROJECT_DIR→ ruta absoluta al proyecto (ej: /Users/tu/proyecto)"
  exit 1
fi

# CHAT_ID debe ser numérico (no el username del bot)
if ! [[ "$CHAT_ID" =~ ^-?[0-9]+$ ]]; then
  echo "❌ CHAT_ID incorrecto: '${CHAT_ID}'"
  echo ""
  echo "   El CHAT_ID es un NÚMERO, no el username del bot."
  echo "   Para obtenerlo:"
  echo "   1. Envía un mensaje a tu bot en Telegram"
  echo "   2. Abre en el browser:"
  echo "      https://api.telegram.org/bot${TOKEN}/getUpdates"
  echo "   3. Busca: \"chat\":{\"id\": XXXXXXXX}"
  echo "      Ese número es tu CHAT_ID"
  exit 1
fi

# PROJECT_DIR debe ser ruta absoluta
if [[ "${PROJECT_DIR}" != /* ]]; then
  echo "❌ PROJECT_DIR debe ser una ruta absoluta, no relativa."
  echo "   Usaste: '${PROJECT_DIR}'"
  echo "   Correcto: $(cd "${PROJECT_DIR}" 2>/dev/null && pwd || echo '/ruta/absoluta/al/proyecto')"
  echo ""
  echo "   Tip: usa \$(pwd) si estás en el directorio del proyecto:"
  echo "   bash install.sh <TOKEN> <CHAT_ID> \$(pwd)"
  exit 1
fi

# PROJECT_DIR debe existir
if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "❌ El directorio no existe: '${PROJECT_DIR}'"
  exit 1
fi

echo "📦 Instalando claude-telegram..."
echo "   Bot token : ${TOKEN:0:20}..."
echo "   Chat ID   : ${CHAT_ID}"
echo "   Proyecto  : ${PROJECT_DIR}"
echo ""

# ── Instalar scripts ──────────────────────────────────────────
mkdir -p "$HOOKS_DIR"
cp hooks/telegram-bot-daemon.py "$HOOKS_DIR/"
cp hooks/start-telegram-bot.sh  "$HOOKS_DIR/"
chmod +x "$HOOKS_DIR/start-telegram-bot.sh"

# Ajustar PROJECT_DIR en el daemon (reemplaza el placeholder)
sed -i '' "s|PROJECT_DIR    = \"/Users/josemuniz/mining_forensic\"|PROJECT_DIR    = \"${PROJECT_DIR}\"|" \
  "$HOOKS_DIR/telegram-bot-daemon.py"

# ── Anthropic API Key ─────────────────────────────────────────
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-$(grep -E 'export ANTHROPIC_API_KEY' ~/.zshrc 2>/dev/null | tail -1 | sed 's/.*="\(.*\)"/\1/')}"
if [[ -z "$ANTHROPIC_KEY" ]]; then
  echo "⚠️  ANTHROPIC_API_KEY no encontrada en entorno ni ~/.zshrc"
  echo "   El lenguaje natural no funcionará. Agrégala en:"
  echo "   ${PLIST}"
  ANTHROPIC_KEY="PENDIENTE_AGREGAR"
fi

# ── Crear LaunchAgent plist ───────────────────────────────────
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
        <string>${HOOKS_DIR}/start-telegram-bot.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>${TOKEN}</string>
        <key>TELEGRAM_CHAT_ID</key>
        <string>${CHAT_ID}</string>
        <key>ANTHROPIC_API_KEY</key>
        <string>${ANTHROPIC_KEY}</string>
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

# ── Arrancar el bot ───────────────────────────────────────────
launchctl unload "$PLIST" 2>/dev/null || true
truncate -s 0 /tmp/mforensic-bot.log /tmp/mforensic-bot-error.log 2>/dev/null || true
launchctl load "$PLIST"

echo "⏳ Esperando arranque (8s)..."
sleep 8

if grep -q "Red disponible" /tmp/mforensic-bot.log 2>/dev/null; then
  echo "✅ Bot corriendo."
  echo ""
  echo "   Envía /help a tu bot en Telegram para confirmar."
  echo ""
  echo "   Logs:"
  echo "   tail -f /tmp/mforensic-bot.log"
else
  echo "❌ Algo falló. Revisa los logs:"
  echo "   cat /tmp/mforensic-bot.log"
  echo "   cat /tmp/mforensic-bot-error.log"
fi
