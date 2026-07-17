#!/bin/bash
# Prueba inmediata.
#   ./test-alerta.sh
#   ./test-alerta.sh --rapido
#   ./test-alerta.sh --largo
#   ./test-alerta.sh --largo --rapido

cd "$(dirname "$0")"

args=(--ahora)
for arg in "$@"; do
  case "$arg" in
    --rapido|--largo) args+=("$arg") ;;
  esac
done

python3 muevete.py "${args[@]}"
