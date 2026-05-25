"""
Agente de auditoría
Valida el output de los scrapers antes de escribir en base de datos.
Genera audit.json con alertas y decisión de bloqueo.
"""

import json
import re
from datetime import datetime, date

UMBRAL_BLOQUEO   = 5   # nº de alertas GRAVES que bloquea la escritura

# Tipos de alerta que NO cuentan para el umbral de bloqueo (avisos informativos)
ALERTAS_NO_BLOQUEANTES = {"campo_vacio_fecha"}
MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def _parse_fecha(fecha_str):
    """Extrae la primera fecha de un string como '29 may al 27 jun' → date(2026,5,29)."""
    if not fecha_str:
        return None
    m = re.search(r"(\d{1,2})\s+(\w{3})", fecha_str.lower())
    if not m:
        return None
    try:
        dia = int(m.group(1))
        mes = MESES.get(m.group(2)[:3])
        if not mes:
            return None
        anyo = datetime.now().year
        return date(anyo, mes, dia)
    except Exception:
        return None


def audit(eventos, fuente="desconocida"):
    alertas = []
    hoy     = date.today()

    # 1. Completitud: ¿scraper devolvió algo?
    if len(eventos) == 0:
        alertas.append({
            "tipo":    "scraper_vacio",
            "evento":  None,
            "detalle": f"El scraper '{fuente}' devolvió 0 resultados. Posible cambio de estructura en la web."
        })

    titulos_vistos = {}
    for ev in eventos:
        titulo = ev.get("titulo", "").strip()
        fecha  = ev.get("fecha", "")
        sala   = ev.get("sala", "").strip()

        # 2. Campos obligatorios vacíos
        if not titulo:
            alertas.append({"tipo": "campo_vacio", "evento": titulo or "—", "detalle": "título vacío"})
        if not sala:
            alertas.append({"tipo": "campo_vacio", "evento": titulo, "detalle": "sala vacía"})
        if not fecha:
            # fecha vacía es aviso informativo (no todas las webs publican fechas en el listado)
            alertas.append({"tipo": "campo_vacio_fecha", "evento": titulo, "detalle": "fecha vacía (aviso)"})

        # 3. Fecha en el pasado
        fecha_dt = _parse_fecha(fecha)
        if fecha_dt and fecha_dt < hoy:
            alertas.append({
                "tipo":    "fecha_pasada",
                "evento":  titulo,
                "detalle": f"fecha_inicio detectada: {fecha_dt} (anterior a hoy {hoy})"
            })

        # 4. Duplicados dentro del mismo batch
        key = titulo.lower()
        if key in titulos_vistos:
            alertas.append({
                "tipo":    "duplicado",
                "evento":  titulo,
                "detalle": f"ya aparece en posición {titulos_vistos[key]}"
            })
        else:
            titulos_vistos[key] = eventos.index(ev)

        # 5. Título sospechosamente corto
        if titulo and len(titulo) < 4:
            alertas.append({"tipo": "titulo_sospechoso", "evento": titulo, "detalle": "título < 4 caracteres"})

    alertas_graves = [a for a in alertas if a["tipo"] not in ALERTAS_NO_BLOQUEANTES]
    bloqueado = len(alertas_graves) >= UMBRAL_BLOQUEO

    resultado = {
        "fecha_ejecucion":    datetime.now().isoformat(timespec="seconds"),
        "fuente":             fuente,
        "eventos_recibidos":  len(eventos),
        "eventos_validos":    len(eventos) - sum(1 for a in alertas if a["tipo"] == "campo_vacio"),
        "num_alertas":        len(alertas),
        "num_alertas_graves": len(alertas_graves),
        "alertas":            alertas,
        "bloqueado":          bloqueado,
    }

    if bloqueado:
        print(f"  ⚠️  BLOQUEADO ({len(alertas_graves)} alertas graves ≥ umbral {UMBRAL_BLOQUEO})")
    else:
        avisos = len(alertas) - len(alertas_graves)
        print(f"  ✓  OK — {len(eventos)} eventos, {len(alertas_graves)} alerta(s) grave(s), {avisos} aviso(s)")

    return resultado


def run_audit(todos_eventos):
    """Audita por fuente y genera un audit.json consolidado."""
    fuentes   = {}
    resultados = []

    for ev in todos_eventos:
        f = ev.get("fuente", "desconocida")
        fuentes.setdefault(f, []).append(ev)

    for fuente, eventos in fuentes.items():
        print(f"Auditando '{fuente}'...")
        res = audit(eventos, fuente)
        resultados.append(res)

    # Resumen global
    total_alertas = sum(r["num_alertas"] for r in resultados)
    bloqueado_global = any(r["bloqueado"] for r in resultados)

    consolidado = {
        "fecha_ejecucion": datetime.now().isoformat(timespec="seconds"),
        "fuentes_auditadas": len(resultados),
        "total_eventos": len(todos_eventos),
        "total_alertas": total_alertas,
        "bloqueado": bloqueado_global,
        "detalle_por_fuente": resultados,
    }

    with open("output/audit.json", "w", encoding="utf-8") as f:
        json.dump(consolidado, f, ensure_ascii=False, indent=2)

    print(f"\nAudit guardado en output/audit.json")
    print(f"Total: {len(todos_eventos)} eventos | {total_alertas} alertas | bloqueado: {bloqueado_global}")
    return consolidado


if __name__ == "__main__":
    # Test rápido con datos de ejemplo
    test = [
        {"titulo": "Jamming", "tipo": "show", "fecha": "29 may al 27 jun",
         "sala": "Teatro Maravillas", "fuente": "atrapalo"},
        {"titulo": "", "tipo": "show", "fecha": "",
         "sala": "", "fuente": "atrapalo"},
        {"titulo": "Jamming", "tipo": "show", "fecha": "29 may al 27 jun",
         "sala": "Teatro Maravillas", "fuente": "atrapalo"},  # duplicado
    ]
    import os; os.makedirs("output", exist_ok=True)
    run_audit(test)
