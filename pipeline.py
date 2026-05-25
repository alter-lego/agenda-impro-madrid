"""
Pipeline principal — Agenda Impro Madrid
Ejecuta scrapers → audita → deduplica → genera JSON + HTML
"""

import json
import os
import unicodedata
from datetime import datetime

from scrapers.scraper_atrapalo import scrape as scrape_atrapalo
from scrapers.scraper_capa1    import scrape as scrape_capa1
from scrapers.auditor          import run_audit

os.makedirs("output", exist_ok=True)


# ── Deduplicación ─────────────────────────────────────────────────────────────

def _norm(s):
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def deduplicate(eventos):
    seen, result = {}, []
    for ev in eventos:
        key = _norm(ev["titulo"])
        if key not in seen:
            seen[key] = len(result)
            result.append(ev)
        else:
            # Enriquecer con precio si el duplicado lo tiene
            idx = seen[key]
            if ev.get("precio") and not result[idx].get("precio"):
                result[idx]["precio"] = ev["precio"]
            if ev.get("fecha") and not result[idx].get("fecha"):
                result[idx]["fecha"] = ev["fecha"]
    return result


# ── HTML ──────────────────────────────────────────────────────────────────────

TIPO_EMOJI = {"show": "🎭", "taller": "🎓", "muestra": "🌟", "workshop": "🎓"}
TIPO_LABEL = {"show": "Show", "taller": "Taller", "muestra": "Muestra", "workshop": "Workshop"}

def render_html(eventos):
    filas = ""
    for ev in eventos:
        tipo   = ev.get("tipo", "show")
        emoji  = TIPO_EMOJI.get(tipo, "🎭")
        label  = TIPO_LABEL.get(tipo, tipo.title())
        titulo = ev.get("titulo", "—")
        fecha  = ev.get("fecha") or "—"
        sala   = ev.get("sala") or "—"
        precio = ev.get("precio") or "—"
        url    = ev.get("url_entradas") or ev.get("url_info") or "#"
        fuente = ev.get("fuente", "")
        badge_cls = {"atrapalo": "at", "escalera_jacob": "ej", "teatro_asura": "ta"}.get(fuente, "ot")
        badge_txt = {"atrapalo": "Atrápalo", "escalera_jacob": "Escalera Jacob",
                     "teatro_asura": "Teatro Asura"}.get(fuente, fuente.replace("_", " ").title())

        filas += f"""
      <tr>
        <td><span class="emoji">{emoji}</span> <a href="{url}" target="_blank" rel="noopener">{titulo}</a>
            <span class="badge {badge_cls}">{badge_txt}</span></td>
        <td><span class="tag tag-{tipo}">{label}</span></td>
        <td>{fecha}</td>
        <td>{sala}</td>
        <td>{precio}</td>
      </tr>"""

    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    n     = len(eventos)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Agenda Impro Madrid</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f5f5f7; color: #1d1d1f; min-height: 100vh;
    }}
    header {{
      background: #1a1a2e; color: #fff; padding: 2rem 1.5rem 1.5rem;
    }}
    header h1 {{ font-size: 1.8rem; font-weight: 700; }}
    header p  {{ margin-top: .4rem; color: #a0a0c0; font-size: .9rem; }}
    .container {{ max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }}
    .filters  {{ display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1.2rem; }}
    .filters button {{
      border: 1px solid #ccc; background: #fff; border-radius: 20px;
      padding: .3rem .9rem; font-size: .85rem; cursor: pointer; transition: all .15s;
    }}
    .filters button:hover, .filters button.active {{
      background: #1a1a2e; color: #fff; border-color: #1a1a2e;
    }}
    .card {{
      background: #fff; border-radius: 12px; overflow: hidden;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
    thead tr {{ background: #f0f0f5; }}
    th {{ padding: .7rem 1rem; text-align: left; font-weight: 600;
          color: #444; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }}
    td {{ padding: .65rem 1rem; border-bottom: 1px solid #f0f0f5; vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #fafafa; }}
    a {{ color: #1a1a2e; text-decoration: none; font-weight: 500; }}
    a:hover {{ text-decoration: underline; }}
    .emoji {{ margin-right: .3rem; }}
    .badge {{
      display: inline-block; font-size: .68rem; padding: .1rem .45rem;
      border-radius: 4px; margin-left: .4rem; font-weight: 600; vertical-align: middle;
    }}
    .badge.at {{ background: #fff3e0; color: #e65100; }}
    .badge.ej {{ background: #e8f5e9; color: #2e7d32; }}
    .badge.ta {{ background: #e3f2fd; color: #1565c0; }}
    .badge.ot {{ background: #f3e5f5; color: #6a1b9a; }}
    .tag {{
      display: inline-block; font-size: .72rem; padding: .15rem .5rem;
      border-radius: 20px; font-weight: 600;
    }}
    .tag-show    {{ background: #e8eaf6; color: #3949ab; }}
    .tag-taller  {{ background: #e8f5e9; color: #388e3c; }}
    .tag-muestra {{ background: #fff8e1; color: #f57f17; }}
    .footer {{ text-align: center; color: #999; font-size: .8rem; margin: 2rem 0; }}
    .footer a {{ color: #999; }}
    tr.hidden {{ display: none; }}
  </style>
</head>
<body>
  <header>
    <h1>🎭 Agenda Impro Madrid</h1>
    <p>Actualizado: {ahora} · {n} eventos · Fuentes: Atrápalo, La Escalera de Jacob, Teatro Asura</p>
  </header>

  <div class="container">
    <div class="filters">
      <button class="active" onclick="filtrar('todos', this)">Todos ({n})</button>
      <button onclick="filtrar('show', this)">Shows</button>
      <button onclick="filtrar('taller', this)">Talleres</button>
      <button onclick="filtrar('muestra', this)">Muestras</button>
    </div>

    <div class="card">
      <table id="tabla">
        <thead>
          <tr>
            <th>Espectáculo</th>
            <th>Tipo</th>
            <th>Fechas</th>
            <th>Sala</th>
            <th>Precio</th>
          </tr>
        </thead>
        <tbody>{filas}
        </tbody>
      </table>
    </div>

    <p class="footer">
      Datos extraídos automáticamente · <a href="agenda_impro_madrid.json">Descargar JSON</a> ·
      <a href="https://github.com/alter-lego/agenda-impro-madrid">GitHub</a>
    </p>
  </div>

  <script>
    function filtrar(tipo, btn) {{
      document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('#tabla tbody tr').forEach(tr => {{
        if (tipo === 'todos') {{ tr.classList.remove('hidden'); return; }}
        const tag = tr.querySelector('.tag');
        tr.classList.toggle('hidden', !tag || !tag.classList.contains('tag-' + tipo));
      }});
    }}
  </script>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Pipeline Agenda Impro Madrid ===\n")

    print("[ 1/4 ] Scraping Capa 1 (salas)...")
    ev_capa1 = scrape_capa1()
    print(f"        → {len(ev_capa1)} eventos\n")

    print("[ 2/4 ] Scraping Capa 2 (Atrápalo)...")
    ev_capa2 = scrape_atrapalo()
    print(f"        → {len(ev_capa2)} eventos\n")

    todos = ev_capa1 + ev_capa2

    print("[ 3/4 ] Auditoría...")
    audit = run_audit(todos)
    if audit["bloqueado"]:
        print("        ⛔ Pipeline bloqueado por el auditor. Revisa output/audit.json")
        exit(1)
    print()

    print("[ 4/4 ] Deduplicando y generando output...")
    deduped = deduplicate(todos)
    print(f"        {len(todos)} → {len(deduped)} eventos tras deduplicación\n")

    # JSON
    with open("output/agenda_impro_madrid.json", "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    # HTML
    with open("output/index.html", "w", encoding="utf-8") as f:
        f.write(render_html(deduped))

    print(f"✅ output/index.html        ({len(deduped)} eventos)")
    print(f"✅ output/agenda_impro_madrid.json")
    print(f"✅ output/audit.json")
