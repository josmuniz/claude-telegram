# claude-telegram

Bot de Telegram con Claude AI para monitorear proyectos de desarrollo desde el móvil.

**Características:**
- Comandos rápidos sin costo API: `/status`, `/git`, `/branch`, `/diff`, `/tests`, `/help`
- Lenguaje natural con Claude Haiku: *"¿cuántos archivos py tiene el proyecto?"*
- Se instala como daemon macOS (LaunchAgent) — arranca solo con el Mac

---

## Instalación paso a paso

### Paso 1 — Crear el bot en Telegram (en la app Telegram)

1. Abre Telegram → busca **@BotFather**
2. Envía `/newbot`
3. Ponle nombre y username (debe terminar en `bot`)
4. Copia el **TOKEN** que te da (ej: `1234567890:AAGya5MPV...`)

---

### Paso 2 — Obtener tu Chat ID (en el browser)

> ⚠️ El Chat ID es un **número**, NO el @username del bot

1. Abre el chat con tu bot nuevo en Telegram y envíale cualquier mensaje (ej: "hola")
2. Abre esto en el browser (reemplaza `<TOKEN>` con el tuyo):
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
3. Busca en el JSON:
```json
"from": {
  "id": 6799432135,
  ...
}
```
Ese número (`6799432135`) es tu **Chat ID**.

> Si `"result":[]` sale vacío → regresa a Telegram y envía otro mensaje al bot, luego recarga el browser.

---

### Paso 3 — Instalar (en la terminal)

```bash
git clone https://github.com/josmuniz/claude-telegram.git
cd claude-telegram
bash install.sh <TOKEN> <CHAT_ID> /ruta/absoluta/al/proyecto
```

**Ejemplos:**
```bash
# Si el proyecto está en ~/mi_proyecto:
bash install.sh 1234567890:AAGya5MPV... 6799432135 /Users/tuusuario/mi_proyecto

# Si ya estás dentro del directorio del proyecto:
bash install.sh 1234567890:AAGya5MPV... 6799432135 $(pwd)
```

> ⚠️ La ruta del proyecto debe ser **absoluta** (empezar con `/`), no relativa.

---

### Paso 4 — Verificar

```bash
cat /tmp/mforensic-bot.log
# Debe mostrar:
# [bot] Iniciado con Claude claude-haiku-4-5-20251001. Proyecto: /tu/proyecto
# [bot] Red disponible.
```

Envía `/help` al bot en Telegram para confirmar que responde.

---

## Gestión del daemon

```bash
# Ver logs en vivo
tail -f /tmp/mforensic-bot.log

# Reiniciar
launchctl unload ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist
launchctl load   ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist

# Parar permanentemente
launchctl unload ~/Library/LaunchAgents/com.mforensic.telegram-bot.plist
pkill -f telegram-bot-daemon.py
```

---

## Requisitos
- macOS 12+
- Python 3.9+ (Anaconda o sistema)
- `curl` (incluido en macOS)
- API key de Anthropic — [console.anthropic.com](https://console.anthropic.com)

---

## Notas técnicas
- Usa `curl --http1.1 --data-binary @tmpfile` (fix para bug de fragmentación TCP en launchd)
- Una sola llamada Claude por mensaje (sin tool_use loop)
- Contexto del proyecto pre-recopilado y compacto (< 280 chars)
