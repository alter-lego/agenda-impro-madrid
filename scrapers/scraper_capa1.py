"""
Capa 1 — Salas con HTML estático
  · La Escalera de Jacob — /cartelera/buscador/improvisacion/
  · Teatro Asura         — /espectaculos-asura/ filtrado por keyword
Requiere: pip install requests beautifulsoup4
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
KEYWORDS = ["impro", "improvisaci", "muestra", "taller", "workshop"]


def _classify(titulo):
    t = titulo.lower()
    if any(w in t for w in ["taller", "workshop"]):  return "taller"
    if "muestra" in t:                                return "muestra"
    if re.search(r'\bjam\b', t):                      return "taller"
    return "show"


# ── La Escalera de Jacob ─────────────────────────────────────────────────────

def scrape_escalera():
    url  = "https://www.laescaleradejacob.es/cartelera/buscador/improvisacion/"
    base = "https://www.laescaleradejacob.es"
    r    = requests.get(url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    events = []
    # Solo tarjetas reales: links que contienen div.contentInfoCarte
    for info_div in soup.select("a[href*='/cartelera/'] div.contentInfoCarte"):
        card = info_div.parent  # el <a>
        href = card.get("href", "")

        # Título
        titulo_tag = card.select_one("div.titularGrid span")
        if not titulo_tag:
            continue
        titulo = titulo_tag.get_text(strip=True).title()

        # Fecha (último span de contentDates)
        fecha_spans = card.select("div.contentDates span")
        fecha = fecha_spans[-1].get_text(strip=True) if fecha_spans else ""

        events.append({
            "titulo":       titulo,
            "tipo":         _classify(titulo),
            "fecha":        fecha,
            "sala":         "La Escalera de Jacob",
            "direccion":    "C/ Lavapiés 9, Madrid",
            "precio":       None,
            "url_entradas": base + href,
            "url_info":     base + href,
            "fuente":       "escalera_jacob",
        })
    return events


# ── Teatro Asura ─────────────────────────────────────────────────────────────

def scrape_asura():
    url  = "https://teatroasura.com/espectaculos-asura/"
    base = "https://teatroasura.com"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")

    seen, events = set(), []
    for a in soup.find_all("a", href=True):
        titulo = a.get_text(strip=True)
        href   = a["href"]
        if not titulo or len(titulo) < 4:
            continue
        if "/espectaculo/" not in href:
            continue
        if not any(kw in titulo.lower() for kw in KEYWORDS):
            continue
        if titulo in seen:
            continue
        seen.add(titulo)
        url_completa = href if href.startswith("http") else base + href
        events.append({
            "titulo":       titulo.title(),
            "tipo":         _classify(titulo),
            "fecha":        "",
            "sala":         "Teatro Asura",
            "direccion":    "C/ de Abel 1, Madrid",
            "precio":       None,
            "url_entradas": url_completa,
            "url_info":     url_completa,
            "fuente":       "teatro_asura",
        })
    return events


# ── Global Impro (La Casa de los Jacintos) ───────────────────────────────────

def scrape_global_impro():
    """Global Impro — shows en La Casa de los Jacintos vía billetweb."""
    url = "https://www.billetweb.fr/global-impro-shows"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
    except Exception:
        return []
    soup = BeautifulSoup(r.text, "html.parser")

    fecha_re = re.compile(
        r"\d{1,2}\s+de\s+"
        r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
        re.IGNORECASE,
    )
    events = []
    seen   = set()

    for strong in soup.find_all("strong"):
        titulo = strong.get_text(strip=True)
        # Ignorar: vacío, etiquetas [ESTRENO...], textos de UI, fechas puras
        if not titulo or len(titulo) < 4:
            continue
        if titulo.startswith("["):
            continue
        if fecha_re.fullmatch(titulo):
            continue
        if any(w in titulo.lower() for w in ["billetweb", "book", "ticket", "read", "organizer", "contact"]):
            continue

        # El párrafo padre debe contener una fecha
        parent_text = strong.parent.get_text()
        m = fecha_re.search(parent_text)
        if not m:
            continue

        key = titulo.lower()
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "titulo":       titulo.title(),
            "tipo":         _classify(titulo),
            "fecha":        m.group(0),
            "sala":         "La Casa de los Jacintos",
            "direccion":    "C/ de La Arganzuela, 11, Madrid",
            "precio":       "10€",
            "url_entradas": url,
            "url_info":     url,
            "fuente":       "global_impro",
        })

    return events


# ── Main ─────────────────────────────────────────────────────────────────────

def scrape():
    return scrape_escalera() + scrape_asura() + scrape_global_impro()


if __name__ == "__main__":
    ev_e = scrape_escalera()
    print(f"La Escalera de Jacob → {len(ev_e)} eventos")
    for e in ev_e:
        print(f"  · [{e['tipo']}] {e['titulo'][:40]:40} | {e['fecha']}")

    print()
    ev_a = scrape_asura()
    print(f"Teatro Asura → {len(ev_a)} eventos")
    for e in ev_a:
        print(f"  · [{e['tipo']}] {e['titulo'][:40]:40} | {e['fecha']}")

    print()
    ev_g = scrape_global_impro()
    print(f"Global Impro (La Casa de los Jacintos) → {len(ev_g)} eventos")
    for e in ev_g:
        print(f"  · [{e['tipo']}] {e['titulo'][:40]:40} | {e['fecha']}")
