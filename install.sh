#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.muevete.app.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"
chmod +x "$SCRIPT_DIR/muevete.py"
chmod +x "$SCRIPT_DIR"/*.sh

# Sustituir ruta del proyecto en el plist
sed "s|__SCRIPT_DIR__|$SCRIPT_DIR|g" "$PLIST_SRC" > "$PLIST_DST"

LABEL="${PLIST_NAME%.plist}"
UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST_DST"
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart -k "$DOMAIN/$LABEL" 2>/dev/null || true

echo ""
echo "Muévete instalado y en ejecución."
echo ""
echo "   Config:     $SCRIPT_DIR/config.json"
echo "   Ejercicios: $SCRIPT_DIR/ejercicios.json"
echo "   Logs:       $LOG_DIR/"
echo ""
echo "Comandos utiles:"
echo "   \"$SCRIPT_DIR/estado.sh\""
echo "   \"$SCRIPT_DIR/resumen.sh\""
echo "   \"$SCRIPT_DIR/informe.sh\""
echo "   \"$SCRIPT_DIR/ahora.sh --rapido\""
echo "   \"$SCRIPT_DIR/pausar.sh 45\""
echo "   \"$SCRIPT_DIR/reanudar.sh\""
echo ""
echo "Para desinstalar:"
echo "   \"$SCRIPT_DIR/uninstall.sh\""
echo ""
