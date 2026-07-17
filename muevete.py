#!/usr/bin/env python3
"""Muévete — recordatorios locales para mover el cuerpo en Mac."""

import json
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EJERCICIOS_PATH = BASE_DIR / "ejercicios.json"
LOG_PATH = BASE_DIR / "logs" / "muevete.log"
HISTORIAL_PATH = BASE_DIR / "logs" / "historial.json"
ESTADO_PATH = BASE_DIR / "logs" / "estado.json"

APP_NAME = "Muévete"

SONIDOS = [
    "/System/Library/Sounds/Hero.aiff",
    "/System/Library/Sounds/Sosumi.aiff",
    "/System/Library/Sounds/Funk.aiff",
    "/System/Library/Sounds/Blow.aiff",
]


def log(mensaje: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n"
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(linea)


def cargar_json(path: Path, default):
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        log(f"Error cargando {path.name}: {exc}")
        return default


def guardar_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_estado() -> dict:
    estado = cargar_json(ESTADO_PATH, {})
    cambiado = False
    if "inicio_sesion" not in estado:
        estado["inicio_sesion"] = datetime.now().isoformat()
        cambiado = True
    estado.setdefault("pospuestos_seguidos", 0)
    estado.setdefault("racha_sin_posponer", 0)
    estado.setdefault("mejor_racha", 0)
    if cambiado:
        guardar_json(ESTADO_PATH, estado)
    return estado


def guardar_historial(
    ejercicio: dict,
    accion: str,
    tipo_pausa: str = "corto",
    intencion: str = None,
) -> None:
    historial = cargar_json(HISTORIAL_PATH, [])
    entrada = {
        "fecha": datetime.now().isoformat(),
        "ejercicio": ejercicio["nombre"],
        "accion": accion,
        "tipo_pausa": tipo_pausa,
    }
    if intencion:
        entrada["intencion"] = intencion
    historial.append(entrada)
    historial = historial[-300:]
    guardar_json(HISTORIAL_PATH, historial)


def applescript_string(texto: str) -> str:
    return json.dumps(texto, ensure_ascii=False)


def ejecutar_applescript(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-"],
        input=script,
        capture_output=True,
        text=True,
    )


def parse_iso(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def formatear_tiempo(segundos: int) -> str:
    minutos, segs = divmod(max(0, int(segundos)), 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas:d}:{minutos:02d}:{segs:02d}"
    return f"{minutos:02d}:{segs:02d}"


def formatear_hora(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def horas_sesion(estado: dict) -> float:
    inicio = parse_iso(estado.get("inicio_sesion"))
    if not inicio:
        return 0.0
    return max(0.0, (datetime.now() - inicio).total_seconds() / 3600)


def en_no_molestar(estado: dict):
    hasta = parse_iso(estado.get("no_molestar_hasta"))
    if not hasta:
        return False, None
    if datetime.now() >= hasta:
        return False, None
    return True, hasta


def dentro_horario_activo(config: dict) -> bool:
    if not config.get("horario_activo", False):
        return True
    ahora = datetime.now().time()
    try:
        inicio = datetime.strptime(config.get("horario_inicio", "09:00"), "%H:%M").time()
        fin = datetime.strptime(config.get("horario_fin", "20:00"), "%H:%M").time()
    except ValueError:
        return True
    if inicio <= fin:
        return inicio <= ahora <= fin
    # Cruza medianoche (ej. 22:00 - 06:00)
    return ahora >= inicio or ahora <= fin


def segundos_hasta_horario(config: dict) -> int:
    """Segundos hasta el proximo horario_inicio si estamos fuera."""
    if dentro_horario_activo(config):
        return 0
    ahora = datetime.now()
    try:
        h, m = map(int, config.get("horario_inicio", "09:00").split(":"))
    except ValueError:
        return 0
    siguiente = ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    if siguiente <= ahora:
        siguiente += timedelta(days=1)
    return int((siguiente - ahora).total_seconds())


def activar_no_molestar(minutos: int) -> dict:
    estado = cargar_estado()
    hasta = datetime.now() + timedelta(minutes=max(1, minutos))
    estado["no_molestar_hasta"] = hasta.isoformat()
    guardar_json(ESTADO_PATH, estado)
    log(f"No molestar hasta {hasta.isoformat()}")
    return estado


def desactivar_no_molestar() -> dict:
    estado = cargar_estado()
    estado.pop("no_molestar_hasta", None)
    guardar_json(ESTADO_PATH, estado)
    log("No molestar desactivado")
    return estado


def reproducir_sonido(config=None, momento: str = "inicio", insistente: bool = False) -> None:
    config = config or {}
    volumen = float(config.get("volumen", 2.5))
    repeticiones = int(config.get("sonido_repeticiones", 1))
    if insistente:
        volumen = max(volumen, float(config.get("volumen_insistente", volumen + 2)))
        repeticiones = max(repeticiones, int(config.get("sonido_repeticiones_insistente", 3)))

    sonido = (
        config.get(f"sonido_{momento}_archivo")
        or config.get("sonido_archivo")
        or random.choice(SONIDOS)
    )

    if not Path(sonido).exists():
        log(f"Sonido no encontrado: {sonido}")
        return

    for _ in range(max(1, repeticiones)):
        subprocess.run(
            ["afplay", "-v", str(volumen), sonido],
            check=False,
        )


def mostrar_notificacion(titulo: str, mensaje: str) -> None:
    script = (
        f"display notification {applescript_string(mensaje)} "
        f"with title {applescript_string(titulo)} sound name \"Glass\""
    )
    ejecutar_applescript(script)


def etiqueta_pausa(tipo_pausa: str, duracion: int) -> str:
    if tipo_pausa == "largo":
        return f"Descanso largo ({formatear_tiempo(duracion)})"
    return f"Micro-pausa ({formatear_tiempo(duracion)})"


def texto_ejercicio(ejercicio: dict, tipo_pausa: str, config: dict, estado: dict, insistente: bool) -> str:
    partes = [ejercicio["descripcion"]]
    beneficio = ejercicio.get("beneficio")
    if beneficio:
        partes.append(f"Por que hacerlo: {beneficio}")

    if tipo_pausa == "largo":
        partes.append("Este es tu descanso largo despues de varias horas de trabajo.")
    else:
        partes.append("Micro-pausa: corta, concreta y suficiente para despegarte un momento.")

    horas = horas_sesion(estado)
    if horas >= float(config.get("mensaje_contexto_desde_horas", 3)):
        partes.append(
            f"Llevas ~{horas:.1f} h en sesion. Este descanso importa mas que el ejercicio perfecto."
        )

    if insistente:
        pospuestos = int(estado.get("pospuestos_seguidos", 0))
        partes.append(
            f"Ya pospusiste {pospuestos} veces seguidas. Esta vez conviene moverte ahora."
        )

    racha = int(estado.get("racha_sin_posponer", 0))
    if racha > 0:
        partes.append(f"Racha actual: {racha} pausas seguidas sin posponer.")

    return "\n\n".join(partes)


def mostrar_dialogo_inicio(
    titulo: str, mensaje: str, duracion: int, tipo_pausa: str, insistente: bool
) -> str:
    boton_empezar = "Empezar pausa"
    boton_posponer = "Posponer 5 min"
    tipo_txt = "Descanso largo" if tipo_pausa == "largo" else "Micro-pausa"

    texto = (
        f"{mensaje}\n\n"
        f"Tipo: {tipo_txt}\n"
        f"Duracion: {formatear_tiempo(duracion)}\n"
        f"Veras un contador que se actualiza cada poco.\n"
        f"Al terminar escucharas un sonido distinto para volver."
    )
    icono = "caution" if insistente else "note"
    script = (
        f"display dialog {applescript_string(texto)} "
        f"buttons {{{applescript_string(boton_posponer)}, {applescript_string(boton_empezar)}}} "
        f"default button {applescript_string(boton_empezar)} "
        f"with title {applescript_string(titulo)} "
        f"with icon {icono}"
    )

    resultado = ejecutar_applescript(script)
    if resultado.returncode != 0:
        log(f"Dialogo cerrado: {resultado.stderr.strip() or 'cancelado'}")
        return "cancelado"

    salida = resultado.stdout.strip()
    if boton_posponer in salida:
        return "posponer"
    if boton_empezar in salida:
        return "empezar"
    return "cancelado"


def mostrar_dialogo_fin(ejercicio: dict, config: dict, estado: dict) -> str:
    titulo = f"{APP_NAME} — Pausa completada"
    racha = int(estado.get("racha_sin_posponer", 0))
    mejor = int(estado.get("mejor_racha", 0))
    mensaje = (
        f"Listo. Completaste: {ejercicio['nombre']}\n\n"
        f"Racha actual: {racha}  |  Mejor racha: {mejor}\n\n"
        f"Una frase para cerrar la pausa (opcional):\n"
        f"¿Que vas a hacer ahora al volver?"
    )
    boton_volver = "Volver al PC"
    boton_informe = "Ver informe"
    script = (
        f"set dialogResult to display dialog {applescript_string(mensaje)} "
        f"default answer \"\" "
        f"buttons {{{applescript_string(boton_informe)}, {applescript_string(boton_volver)}}} "
        f"default button {applescript_string(boton_volver)} "
        f"with title {applescript_string(titulo)} "
        f"with icon note\n"
        f"return (button returned of dialogResult) & \"\\n\" & (text returned of dialogResult)"
    )
    resultado = ejecutar_applescript(script)
    salida = (resultado.stdout or "").split("\n", 1)
    boton = salida[0].strip() if salida else ""
    intencion = salida[1].strip() if len(salida) > 1 else ""

    if intencion:
        estado["ultima_intencion"] = intencion
        guardar_json(ESTADO_PATH, estado)
        log(f"Intencion al volver: {intencion}")

    ver_informe = boton == boton_informe
    return intencion, ver_informe

def esperar_pausa(ejercicio: dict, segundos: int, config: dict) -> bool:
    """
    Modal de cuenta regresiva que se actualiza cada N segundos
    (no cada segundo, para evitar parpadeo).
    """
    total = max(1, int(segundos))
    paso = int(config.get("contador_actualizar_segundos", 30))
    paso = max(5, paso)

    log(
        f"Esperando pausa de {formatear_tiempo(total)} "
        f"(actualiza cada {paso}s): {ejercicio['nombre']}"
    )
    if config.get("notificacion", True):
        mostrar_notificacion(
            f"{APP_NAME}: pausa en curso",
            f"{ejercicio['nombre']} — {formatear_tiempo(total)}. Te avisaremos al terminar.",
        )

    titulo = f"{APP_NAME} — {ejercicio['nombre']}"
    descripcion = ejercicio["descripcion"]
    boton_saltar = "Saltar pausa"

    script = f"""
set totalSeconds to {total}
set stepSeconds to {paso}
set exerciseDesc to {applescript_string(descripcion)}
set dialogTitle to {applescript_string(titulo)}
set skipButton to {applescript_string(boton_saltar)}
set remaining to totalSeconds

repeat while remaining > 0
    set waitFor to stepSeconds
    if waitFor > remaining then
        set waitFor to remaining
    end if

    set mins to remaining div 60
    set secs to remaining mod 60
    set minsText to text -2 thru -1 of ("0" & mins)
    set secsText to text -2 thru -1 of ("0" & secs)
    set timeText to minsText & ":" & secsText

    set dialogText to exerciseDesc & return & return & "Tiempo para volver al PC" & return & timeText & return & return & "Sigue con el ejercicio. Esta ventana se actualiza cada poco para que veas el avance."

    try
        set dialogResult to display dialog dialogText buttons {{skipButton}} default button 1 with title dialogTitle with icon note giving up after waitFor
        if gave up of dialogResult is false then
            return "saltado"
        end if
    on error
        return "cancelado"
    end try

    set remaining to remaining - waitFor
end repeat

return "completado"
"""
    resultado = ejecutar_applescript(script)
    salida = (resultado.stdout or "").strip()

    if salida == "completado":
        if config.get("sonido", True):
            reproducir_sonido(config, "fin")
        return True

    log(f"Pausa no completada: {salida or resultado.stderr.strip() or 'error'}")
    return False


def filtrar_ejercicios(ejercicios: list, tipo: str) -> list:
    filtrados = [e for e in ejercicios if e.get("tipo", "corto") == tipo]
    return filtrados or ejercicios


def elegir_ejercicio(ejercicios: list, tipo: str = "corto", estado: dict = None) -> dict:
    candidatos = filtrar_ejercicios(ejercicios, tipo)
    estado = estado or {}
    ultimo = estado.get("ultimo_ejercicio")
    if ultimo and len(candidatos) > 1:
        sin_repetir = [e for e in candidatos if e["nombre"] != ultimo]
        if sin_repetir:
            candidatos = sin_repetir
    return random.choice(candidatos)


def debe_forzar_descanso_largo(config: dict, estado: dict) -> bool:
    if not config.get("descanso_largo_activado", True):
        return False
    if config.get("forzar_descanso_largo"):
        return True

    horas = float(config.get("descanso_largo_cada_horas", 2.5))
    if horas <= 0:
        return False

    referencia = estado.get("ultima_pausa_larga") or estado.get("inicio_sesion")
    desde = parse_iso(referencia)
    if not desde:
        return True

    return (datetime.now() - desde).total_seconds() >= horas * 3600


def marcar_pausa_larga_completada(estado: dict) -> None:
    estado["ultima_pausa_larga"] = datetime.now().isoformat()
    guardar_json(ESTADO_PATH, estado)


def calcular_espera(config: dict) -> int:
    if config.get("intervalo_aleatorio", True):
        minutos = random.randint(
            config.get("intervalo_min", 20),
            config.get("intervalo_max", 30),
        )
    else:
        minutos = config.get("intervalo_minutos", 25)
    return minutos * 60


def duracion_ejercicio(ejercicio: dict, config: dict, tipo_pausa: str = "corto") -> int:
    if config.get("duracion_prueba"):
        return int(config["duracion_prueba"])
    if tipo_pausa == "largo":
        return int(config.get("descanso_largo_minutos", 10)) * 60
    return int(ejercicio.get("duracion_segundos", 60))


def items_hoy(historial: list) -> list:
    hoy = datetime.now().date()
    items = []
    for item in historial:
        try:
            fecha = datetime.fromisoformat(item["fecha"]).date()
        except (KeyError, ValueError, TypeError):
            continue
        if fecha == hoy:
            items.append(item)
    return items


def descansos_completados_hoy() -> int:
    return sum(1 for i in items_hoy(cargar_json(HISTORIAL_PATH, [])) if i.get("accion") == "hecho")


def actualizar_racha(estado: dict, accion: str) -> dict:
    if accion == "hecho":
        estado["pospuestos_seguidos"] = 0
        estado["racha_sin_posponer"] = int(estado.get("racha_sin_posponer", 0)) + 1
        estado["mejor_racha"] = max(
            int(estado.get("mejor_racha", 0)),
            int(estado["racha_sin_posponer"]),
        )
    elif accion == "posponer":
        estado["pospuestos_seguidos"] = int(estado.get("pospuestos_seguidos", 0)) + 1
        estado["racha_sin_posponer"] = 0
    guardar_json(ESTADO_PATH, estado)
    return estado


def es_insistente(config: dict, estado: dict) -> bool:
    limite = int(config.get("posponer_max_antes_insistente", 2))
    return int(estado.get("pospuestos_seguidos", 0)) >= limite


def mostrar_recordatorio_agua(config: dict, descansos: int) -> None:
    titulo = f"{APP_NAME} — Agua"
    mensaje = (
        f"Llevas {descansos} descansos completados hoy.\n\n"
        "¿Ya tomaste agua? Mantenerte hidratado ayuda a la concentración, "
        "la energía y evita dolores de cabeza."
    )
    boton = "Tomar agua"
    script = (
        f"display dialog {applescript_string(mensaje)} "
        f"buttons {{{applescript_string(boton)}}} "
        f"default button {applescript_string(boton)} "
        f"with title {applescript_string(titulo)} "
        f"with icon note"
    )
    if config.get("sonido", True):
        reproducir_sonido(config, "agua")
    ejecutar_applescript(script)


def alertar(config: dict, ejercicio: dict, tipo_pausa: str = "corto", estado: dict = None):
    """Devuelve (accion, intencion, ver_informe)."""
    estado = estado if estado is not None else cargar_estado()
    insistente = es_insistente(config, estado)
    duracion = duracion_ejercicio(ejercicio, config, tipo_pausa)
    etiqueta = etiqueta_pausa(tipo_pausa, duracion)
    titulo = f"{etiqueta}: {ejercicio['nombre']}"
    if insistente:
        titulo = f"IMPORTANTE — {titulo}"

    mensaje = texto_ejercicio(ejercicio, tipo_pausa, config, estado, insistente)

    if config.get("sonido", True):
        reproducir_sonido(config, "inicio", insistente=insistente)

    if config.get("notificacion", True):
        mostrar_notificacion(titulo, ejercicio["descripcion"])

    if not config.get("dialogo_modal", True):
        return "notificado", None, False

    accion = mostrar_dialogo_inicio(titulo, mensaje, duracion, tipo_pausa, insistente)
    if accion != "empezar":
        return accion, None, False

    log(f"Pausa {tipo_pausa} iniciada ({duracion}s): {ejercicio['nombre']}")
    completado = esperar_pausa(ejercicio, duracion, config)

    if completado:
        estado["ultimo_ejercicio"] = ejercicio["nombre"]
        estado = actualizar_racha(estado, "hecho")
        intencion, ver_informe = mostrar_dialogo_fin(ejercicio, config, estado)
        return "hecho", intencion, ver_informe

    return "interrumpido", None, False


def dormir_con_log(segundos: int, motivo: str, estado: dict = None) -> None:
    segundos = max(1, int(segundos))
    minutos = segundos / 60
    if estado is not None:
        estado["proxima_alerta"] = (datetime.now() + timedelta(seconds=segundos)).isoformat()
        guardar_json(ESTADO_PATH, estado)
    log(f"Esperando {minutos:.1f} min — {motivo}")
    time.sleep(segundos)


def esperar_si_hace_falta(config: dict, estado: dict) -> dict:
    """Respeta no molestar y horario activo opcional."""
    while True:
        estado = cargar_estado()
        activo_dnd, hasta = en_no_molestar(estado)
        if activo_dnd and hasta:
            restantes = int((hasta - datetime.now()).total_seconds())
            if restantes > 0:
                dormir_con_log(restantes, "no molestar", estado)
                continue

        if not dentro_horario_activo(config):
            restantes = segundos_hasta_horario(config)
            if restantes > 0:
                dormir_con_log(restantes, "fuera de horario activo", estado)
                config = cargar_json(CONFIG_PATH, {})
                continue

        return cargar_estado()


def html_escape(texto: str) -> str:
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def items_ultimos_dias(historial: list, dias: int = 7) -> list:
    limite = datetime.now().date() - timedelta(days=dias - 1)
    items = []
    for item in historial:
        fecha = parse_iso(item.get("fecha"))
        if not fecha:
            continue
        if fecha.date() >= limite:
            items.append(item)
    return items


def estadisticas(historial: list = None, estado: dict = None) -> dict:
    historial = historial if historial is not None else cargar_json(HISTORIAL_PATH, [])
    estado = estado if estado is not None else cargar_estado()
    hoy = items_hoy(historial)
    semana = items_ultimos_dias(historial, 7)
    hechos_hoy = [i for i in hoy if i.get("accion") == "hecho"]
    pospuestos_hoy = [i for i in hoy if i.get("accion") == "posponer"]
    hechos_semana = [i for i in semana if i.get("accion") == "hecho"]
    con_intencion = [i for i in hechos_hoy if i.get("intencion")]
    return {
        "estado": estado,
        "hoy": hoy,
        "hechos_hoy": hechos_hoy,
        "pospuestos_hoy": pospuestos_hoy,
        "largos_hoy": [i for i in hechos_hoy if i.get("tipo_pausa") == "largo"],
        "cortos_hoy": [i for i in hechos_hoy if i.get("tipo_pausa") != "largo"],
        "hechos_semana": hechos_semana,
        "con_intencion": con_intencion,
        "historial": historial,
    }


def imprimir_estado() -> None:
    config = cargar_json(CONFIG_PATH, {})
    estado = cargar_estado()
    dnd, hasta = en_no_molestar(estado)
    proxima = parse_iso(estado.get("proxima_alerta"))
    print(f"{APP_NAME} — estado")
    print(f"  Sesion desde:     {estado.get('inicio_sesion', '—')}")
    print(f"  Horas de sesion:  {horas_sesion(estado):.1f} h")
    print(f"  Ultimo ejercicio: {estado.get('ultimo_ejercicio', '—')}")
    print(f"  Racha actual:     {estado.get('racha_sin_posponer', 0)}")
    print(f"  Mejor racha:      {estado.get('mejor_racha', 0)}")
    print(f"  Pospuestos seg.:  {estado.get('pospuestos_seguidos', 0)}")
    if estado.get("ultima_intencion"):
        print(f"  Ultima intencion: {estado['ultima_intencion']}")
    if dnd and hasta:
        print(f"  No molestar:      SI hasta {formatear_hora(hasta)}")
    else:
        print("  No molestar:      no")
    if config.get("horario_activo", False):
        print(
            f"  Horario activo:   {config.get('horario_inicio', '09:00')}–"
            f"{config.get('horario_fin', '20:00')} "
            f"({'dentro' if dentro_horario_activo(config) else 'fuera'})"
        )
    else:
        print("  Horario activo:   desactivado")
    if proxima and proxima > datetime.now():
        print(f"  Proxima alerta:   ~{formatear_hora(proxima)}")
    else:
        print("  Proxima alerta:   pendiente / en pausa")
    print("  Tip: usa ./informe.sh para ver estadisticas e intenciones en el navegador.")


def imprimir_resumen() -> None:
    stats = estadisticas()
    estado = stats["estado"]
    hechos = stats["hechos_hoy"]
    pospuestos = stats["pospuestos_hoy"]

    print(f"{APP_NAME} — resumen de hoy ({datetime.now().strftime('%Y-%m-%d')})")
    print(
        f"  Pausas completadas: {len(hechos)} "
        f"({len(stats['cortos_hoy'])} cortas, {len(stats['largos_hoy'])} largas)"
    )
    print(f"  Pospuestas:         {len(pospuestos)}")
    print(f"  Esta semana:        {len(stats['hechos_semana'])} pausas hechas")
    print(f"  Racha actual:       {estado.get('racha_sin_posponer', 0)}")
    print(f"  Mejor racha:        {estado.get('mejor_racha', 0)}")
    print(f"  Horas de sesion:    {horas_sesion(estado):.1f} h")
    if estado.get("ultima_intencion"):
        print(f"  Ultima intencion:   {estado['ultima_intencion']}")
    if hechos:
        print("  Pausas de hoy:")
        for item in hechos[-10:]:
            hora = parse_iso(item.get("fecha"))
            marca = formatear_hora(hora) if hora else "—"
            linea = f"    - {marca} {item.get('ejercicio')} ({item.get('tipo_pausa', 'corto')})"
            if item.get("intencion"):
                linea += f" → {item['intencion']}"
            print(linea)
    print("  Tip: ./informe.sh abre el informe visual completo.")


def generar_informe(abrir: bool = True) -> Path:
    stats = estadisticas()
    estado = stats["estado"]
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    filas = []
    for item in reversed(stats["historial"][-40:]):
        fecha = parse_iso(item.get("fecha"))
        cuando = fecha.strftime("%Y-%m-%d %H:%M") if fecha else "—"
        intencion = item.get("intencion") or "—"
        filas.append(
            "<tr>"
            f"<td>{html_escape(cuando)}</td>"
            f"<td>{html_escape(item.get('ejercicio', '—'))}</td>"
            f"<td>{html_escape(item.get('tipo_pausa', 'corto'))}</td>"
            f"<td>{html_escape(item.get('accion', '—'))}</td>"
            f"<td>{html_escape(intencion)}</td>"
            "</tr>"
        )

    if not filas:
        filas.append(
            '<tr><td colspan="5">Aun no hay pausas registradas. '
            "Completa una y vuelve a abrir el informe.</td></tr>"
        )

    intenciones_hoy = []
    for item in reversed(stats["con_intencion"]):
        fecha = parse_iso(item.get("fecha"))
        marca = formatear_hora(fecha) if fecha else "—"
        intenciones_hoy.append(
            f"<li><strong>{html_escape(marca)}</strong> "
            f"{html_escape(item.get('ejercicio', ''))}: "
            f"{html_escape(item.get('intencion', ''))}</li>"
        )
    bloque_intenciones = (
        "<ul>" + "".join(intenciones_hoy) + "</ul>"
        if intenciones_hoy
        else "<p class='muted'>Todavia no escribiste intenciones hoy.</p>"
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Muévete — Informe</title>
  <style>
    :root {{
      --bg: #f4f7f4;
      --card: #ffffff;
      --ink: #1c2b1c;
      --muted: #5f735f;
      --accent: #2f6b4f;
      --line: #d7e2d7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, #e7f2ea, transparent 40%),
        linear-gradient(180deg, #eef4ee, var(--bg));
      color: var(--ink);
      padding: 32px 20px 48px;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 2rem;
      margin: 0 0 6px;
      letter-spacing: -0.03em;
    }}
    .sub {{
      color: var(--muted);
      margin-bottom: 28px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 14px;
      margin-bottom: 28px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(28, 43, 28, 0.04);
    }}
    .card .label {{
      color: var(--muted);
      font-size: 0.85rem;
      margin-bottom: 8px;
    }}
    .card .value {{
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--accent);
    }}
    h2 {{
      margin: 28px 0 12px;
      font-size: 1.2rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
      font-size: 0.95rem;
    }}
    th {{
      background: #edf5ef;
      color: var(--muted);
      font-weight: 600;
    }}
    tr:last-child td {{ border-bottom: none; }}
    .muted {{ color: var(--muted); }}
    ul {{ padding-left: 18px; }}
    li {{ margin: 8px 0; }}
  </style>
</head>
<body>
  <main>
    <h1>Muévete</h1>
    <p class="sub">Informe generado el {html_escape(ahora)}</p>

    <div class="grid">
      <div class="card"><div class="label">Racha actual</div><div class="value">{estado.get('racha_sin_posponer', 0)}</div></div>
      <div class="card"><div class="label">Mejor racha</div><div class="value">{estado.get('mejor_racha', 0)}</div></div>
      <div class="card"><div class="label">Pausas hoy</div><div class="value">{len(stats['hechos_hoy'])}</div></div>
      <div class="card"><div class="label">Pospuestas hoy</div><div class="value">{len(stats['pospuestos_hoy'])}</div></div>
      <div class="card"><div class="label">Largas hoy</div><div class="value">{len(stats['largos_hoy'])}</div></div>
      <div class="card"><div class="label">Semana</div><div class="value">{len(stats['hechos_semana'])}</div></div>
    </div>

    <div class="card">
      <div class="label">Ultima intencion al volver</div>
      <div style="font-size:1.15rem;font-weight:600;">
        {html_escape(estado.get('ultima_intencion') or 'Sin registrar todavía')}
      </div>
      <p class="muted" style="margin:10px 0 0;">
        Ultimo ejercicio: {html_escape(estado.get('ultimo_ejercicio') or '—')} ·
        Sesion: {horas_sesion(estado):.1f} h
      </p>
    </div>

    <h2>Intenciones de hoy</h2>
    <div class="card">{bloque_intenciones}</div>

    <h2>Historial reciente</h2>
    <table>
      <thead>
        <tr>
          <th>Cuando</th>
          <th>Ejercicio</th>
          <th>Tipo</th>
          <th>Accion</th>
          <th>Que hare despues</th>
        </tr>
      </thead>
      <tbody>
        {''.join(filas)}
      </tbody>
    </table>
  </main>
</body>
</html>
"""
    ruta = BASE_DIR / "logs" / "informe.html"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(html, encoding="utf-8")
    if abrir:
        subprocess.run(["open", str(ruta)], check=False)
    return ruta


def comando_ahora(args: list) -> None:
    config = dict(cargar_json(CONFIG_PATH, {}))
    estado = cargar_estado()
    if "--rapido" in args:
        config["duracion_prueba"] = 10
    if "--largo" in args:
        config["forzar_descanso_largo"] = True

    ejercicios = cargar_json(EJERCICIOS_PATH, [])
    if not ejercicios:
        print("No hay ejercicios en ejercicios.json")
        sys.exit(1)

    tipo_pausa = "largo" if debe_forzar_descanso_largo(config, estado) else "corto"
    ejercicio = elegir_ejercicio(ejercicios, tipo_pausa, estado)
    print(f"Alerta ahora ({tipo_pausa}): {ejercicio['nombre']}")
    accion, intencion, ver_informe = alertar(config, ejercicio, tipo_pausa, estado)
    estado = cargar_estado()
    if accion != "hecho":
        estado = actualizar_racha(estado, accion)
    else:
        estado = cargar_estado()
        if tipo_pausa == "largo":
            marcar_pausa_larga_completada(estado)
    guardar_historial(ejercicio, accion, tipo_pausa, intencion)
    print(f"Respuesta: {accion}")
    if intencion:
        print(f"Intencion: {intencion}")
    if ver_informe:
        generar_informe(abrir=True)


def main() -> None:
    log(f"{APP_NAME} iniciado")
    ejercicios = cargar_json(EJERCICIOS_PATH, [])
    if not ejercicios:
        log("No hay ejercicios configurados. Revisa ejercicios.json")
        sys.exit(1)

    estado = cargar_estado()

    while True:
        config = cargar_json(CONFIG_PATH, {})
        estado = esperar_si_hace_falta(config, estado)

        espera = calcular_espera(config)
        dormir_con_log(espera, "proxima alerta", estado)

        config = cargar_json(CONFIG_PATH, {})
        estado = esperar_si_hace_falta(config, estado)

        tipo_pausa = "largo" if debe_forzar_descanso_largo(config, estado) else "corto"
        ejercicio = elegir_ejercicio(ejercicios, tipo_pausa, estado)
        log(f"Alerta ({tipo_pausa}): {ejercicio['nombre']}")

        accion, intencion, ver_informe = alertar(config, ejercicio, tipo_pausa, estado)
        estado = cargar_estado()

        if accion == "hecho":
            if tipo_pausa == "largo":
                marcar_pausa_larga_completada(estado)
                estado = cargar_estado()
            guardar_historial(ejercicio, accion, tipo_pausa, intencion)

            if ver_informe:
                generar_informe(abrir=True)

            cada = int(config.get("recordatorio_agua_cada_descansos", 3))
            completados = descansos_completados_hoy()
            if cada > 0 and completados % cada == 0:
                mostrar_recordatorio_agua(config, completados)
        else:
            estado = actualizar_racha(estado, accion)
            guardar_historial(ejercicio, accion, tipo_pausa)

        log(f"Respuesta: {accion}")

        if accion == "posponer":
            snooze = config.get("snooze_minutos", 5) * 60
            dormir_con_log(snooze, "pospuesto por el usuario", estado)


def usage() -> None:
    print(
        f"""{APP_NAME}

Uso:
  python3 muevete.py                  # daemon (launchd)
  python3 muevete.py --estado
  python3 muevete.py --resumen
  python3 muevete.py --informe
  python3 muevete.py --ahora [--rapido] [--largo]
  python3 muevete.py --pausar [minutos]
  python3 muevete.py --reanudar
  python3 muevete.py --test [--rapido] [--largo]
"""
    )


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        try:
            main()
        except KeyboardInterrupt:
            log("Detenido manualmente")
            sys.exit(0)

    if "--help" in args or "-h" in args:
        usage()
        sys.exit(0)

    if "--estado" in args:
        imprimir_estado()
        sys.exit(0)

    if "--resumen" in args:
        imprimir_resumen()
        sys.exit(0)

    if "--informe" in args:
        ruta = generar_informe(abrir=True)
        print(f"Informe abierto: {ruta}")
        sys.exit(0)

    if "--reanudar" in args:
        desactivar_no_molestar()
        print("No molestar desactivado. Las alertas siguen el intervalo normal.")
        sys.exit(0)

    if "--pausar" in args:
        idx = args.index("--pausar")
        minutos = 45
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            minutos = int(args[idx + 1])
        else:
            minutos = int(cargar_json(CONFIG_PATH, {}).get("no_molestar_minutos", 45))
        estado = activar_no_molestar(minutos)
        hasta = parse_iso(estado.get("no_molestar_hasta"))
        print(f"No molestar activado por {minutos} min (hasta {formatear_hora(hasta)}).")
        sys.exit(0)

    if "--ahora" in args:
        comando_ahora(args)
        sys.exit(0)

    if "--test" in args or "--test-rapido" in args or "--test-largo" in args:
        # Compatibilidad con test-alerta.sh
        fake = ["--ahora"]
        if "--test-rapido" in args or "--rapido" in args:
            fake.append("--rapido")
        if "--test-largo" in args or "--largo" in args:
            fake.append("--largo")
        comando_ahora(fake)
        sys.exit(0)

    usage()
    sys.exit(1)
