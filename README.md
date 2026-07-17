# Muévete

Recordatorios locales en macOS para levantarte, moverte y tomar agua durante el día.

Alerta → micro-pausa o descanso largo → contador que se actualiza cada 30 s → sonido de fin → cierras con una intención al volver.

## Requisitos

- macOS
- Python 3 (incluido en macOS)

## Instalación

```bash
git clone https://github.com/SalimIsrael/muevete.git
cd muevete
chmod +x *.sh muevete.py
./install.sh
```

Queda corriendo en segundo plano y arranca al iniciar sesión.

## Cómo funciona

1. Cada 20–30 min llega una **micro-pausa** con ejercicio, beneficio y duración.
2. Eliges **Empezar pausa** o **Posponer 5 min**.
3. Ves un **contador** que se actualiza cada 20–30 s (sin parpadear cada segundo).
4. Al terminar suena otro aviso y puedes escribir qué vas a hacer al volver.
5. Cada cierto número de descansos: recordatorio de agua.
6. Cada 2.5 h (configurable): **descanso largo** de 10 min.
7. Si pospones varias veces seguidas, la siguiente alerta es más insistente.
8. No repite el mismo ejercicio dos veces seguidas.
9. Lleva racha de pausas sin posponer.
10. Guarda qué harás al volver y lo puedes ver en `./informe.sh`.

### Mac bloqueada

Si la Mac está bloqueada, el diálogo normalmente **no se ve** hasta que desbloquees. El proceso sigue vivo y la alerta aparece al volver. Por eso el horario activo viene **desactivado** por defecto (útil si trabajas a cualquier hora).

## Comandos rápidos

```bash
./estado.sh                 # estado actual / racha / no molestar
./resumen.sh                # resumen del día en terminal
./informe.sh                # estadísticas e intenciones en el navegador
./ahora.sh                  # forzar una pausa ahora
./ahora.sh --rapido         # pausa de prueba (10s)
./ahora.sh --largo          # forzar descanso largo
./pausar.sh                 # no molestar 45 min (default)
./pausar.sh 60              # no molestar 60 min
./reanudar.sh               # quitar no molestar
./test-alerta.sh --rapido   # alias de prueba
```

## Configuración

Edita `config.json`. Los cambios se aplican en la siguiente alerta.

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `intervalo_aleatorio` | boolean | `true` | Intervalo aleatorio entre `intervalo_min` y `intervalo_max`. Si `false`, usa `intervalo_minutos`. |
| `intervalo_min` | número | `20` | Mínimo de minutos entre alertas. |
| `intervalo_max` | número | `30` | Máximo de minutos entre alertas. |
| `intervalo_minutos` | número | `25` | Intervalo fijo si no es aleatorio. |
| `snooze_minutos` | número | `5` | Minutos al posponer. |
| `sonido` | boolean | `true` | Activa/desactiva sonidos. |
| `volumen` | número | `2.5` | Volumen normal. |
| `sonido_repeticiones` | número | `1` | Repeticiones del sonido normal. |
| `volumen_insistente` | número | `7` | Volumen tras varios pospuestos seguidos. |
| `sonido_repeticiones_insistente` | número | `3` | Repeticiones en modo insistente. |
| `sonido_inicio_archivo` | texto | `Hero.aiff` | Sonido al empezar. |
| `sonido_fin_archivo` | texto | `Glass.aiff` | Sonido al terminar. |
| `sonido_agua_archivo` | texto | `Bottle.aiff` | Sonido del recordatorio de agua. |
| `dialogo_modal` | boolean | `true` | Mostrar diálogos. |
| `notificacion` | boolean | `true` | Notificaciones de macOS. |
| `recordatorio_agua_cada_descansos` | número | `3` | Cada cuántos descansos recordar agua (`0` = off). |
| `descanso_largo_activado` | boolean | `true` | Activa descansos largos. |
| `descanso_largo_cada_horas` | número | `2.5` | Cada cuántas horas forzar descanso largo. |
| `descanso_largo_minutos` | número | `10` | Duración del descanso largo. |
| `posponer_max_antes_insistente` | número | `2` | Tras N pospuestos seguidos, la alerta se vuelve insistente. |
| `mensaje_contexto_desde_horas` | número | `3` | Desde cuántas horas de sesión mostrar mensaje de contexto. |
| `no_molestar_minutos` | número | `45` | Default de `./pausar.sh` sin argumentos. |
| `horario_activo` | boolean | `false` | Si `true`, solo alerta entre `horario_inicio` y `horario_fin`. |
| `horario_inicio` | texto | `09:00` | Inicio del horario (solo si `horario_activo`). |
| `horario_fin` | texto | `20:00` | Fin del horario (solo si `horario_activo`). |
| `contador_actualizar_segundos` | número | `30` | Cada cuántos segundos se actualiza el modal del contador (ej. `20` o `30`). |

### Ejercicios

En `ejercicios.json`:

| Campo | Descripción |
|-------|-------------|
| `nombre` | Título |
| `descripcion` | Qué hacer |
| `beneficio` | Por qué ayuda |
| `duracion_segundos` | Duración de micro-pausas |
| `tipo` | `corto` o `largo` |

## Desinstalar

```bash
./uninstall.sh
```

## Notas

- Notificaciones: **Ajustes del Sistema → Notificaciones**.
- Logs en `logs/` (no se suben al repo).
