# claude-telegram

Bot de Telegram con Claude AI para monitorear proyectos de desarrollo desde el móvil.

**Características:**
- Comandos rápidos sin costo API: `/status`, `/git`, `/branch`, `/diff`, `/tests`, `/help`
- Lenguaje natural con Claude Haiku: *"¿cuántos archivos py tiene el proyecto?"*
- Se instala como daemon macOS (LaunchAgent) — arranca solo con el Mac
- Claude Code skill incluido: `/install-telegram-bot`

---

## Instalación rápida (con Claude Code)

En cualquier Mac con Claude Code instalado:

```
claude
/install-telegram-bot
```

Claude te pedirá el token, chat ID y ruta del proyecto, y configura todo solo.

---

## Instalación manual

### 1. Crear bot en Telegram
- Habla con **@BotFather** → `/newbot` → copia el **TOKEN**
- Envía un mensaje al bot → abre `https://api.telegram.org/bot<TOKEN>/getUpdates` → copia el **chat id**

### 2. Clonar e instalar
```bash
git clone https://github.com/josmuniz/claude-telegram.git
cd claude-telegram
bash install.sh <TOKEN> <CHAT_ID> /ruta/a/tu/proyecto
```

### 3. Verificar
```bash
cat /tmp/mforensic-bot.log
# Debe mostrar: [bot] Red disponible.
```

Envía `/help` al bot en Telegram para confirmar.

---

## Gestión del daemon

```bash
# Ver logs en vivo
tail -f /tmp/mforensic-bot.log

# Reiniciar
launchctl unload ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist
launchctl load   ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist

# Parar
launchctl unload ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist
pkill -f telegram-bot-daemon.py
```

---

## Requisitos
- macOS 12+
- Python 3.9+ (Anaconda o sistema)
- `curl` (incluido en macOS)
- API key de Anthropic ([console.anthropic.com](https://console.anthropic.com))

---

## Notas técnicas
- Usa `curl --http1.1 --data-binary @tmpfile` (fix para bug de fragmentación TCP en launchd)
- Una sola llamada Claude por mensaje (sin tool_use loop) para evitar connection reset
- Contexto del proyecto pre-recopilado y compacto (< 280 chars)
