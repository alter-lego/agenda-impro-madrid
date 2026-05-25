"""
Capa 1 — El Club de la Impro (Playwright)
La página de reservas es JS-rendered.
URL: https://www.elclubdelaimpro.com/reservas
"""

import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL  = "https://www.elclubdelaimpro.com/reservas"
BASE = "https://www.elclubdelaimpro.com"

KEYWORDS = [
    "impro", "improvisaci", "muestra", "taller", "workshop",
    "torneo", "artylogico", "artylógico", "banco", "match",
]


def _classify(titulo):
    t = titulo.lower()
    if any(w in t for w in ["taller", "workshop"]):  return "taller"
    if "muestra" in t:                                return "muestra"
    if re.search(r'\bjam\b', t):                      return "taller"
    return "show"


def scrape():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            page.goto(URL, timeout=25000)
            page.wait_for_timeout(3000)
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"  ⚠️  scraper_club_impro: error Playwright — {e}")
        return []

    soup   = BeautifulSoup(html, "html.parser")
    events = []
    seen   = set()

    # ── Patrón 1: article o div con clase "event / show / espectaculo / card"
    candidates = soup.find_all("article") + soup.find_all(
        "div",
        class_=lambda c: c and any(
            w in c.lower() for w in ["event", "show", "espectaculo", "card", "item", "producto"]
        ),
    )
    for card in candidates:
        title_tag = card.find(["h1", "h2", "h3", "h4"])
        if not title_tag:
            continue
        titulo = title_tag.get_text(strip=True)
        if not titulo or len(titulo) < 4 or titulo.lower() in seen:
            continue

        # Fecha (span / p / time dentro de la card)
        fecha = ""
        for tag in card.find_all(["span", "p", "div", "time"]):
            text = tag.get_text(strip=True)
            if re.search(r"\d{1,2}[/\-]\d{1,2}|\d+\s+de\s+\w+|mayo|junio|julio|agosto", text, re.I):
                fecha = text[:60]
                break

        a            = card.find("a", href=True)
        href         = a["href"] if a else URL
        url_completa = href if href.startswith("http") else BASE + href

        seen.add(titulo.lower())
        events.append({
            "titulo":       titulo.title(),
            "tipo":         _classify(titulo),
            "fecha":        fecha,
            "sala":         "El Club de la Impro",
            "direccion":    "C/ Santa Ana, 6, Madrid",
            "precio":       None,
            "url_entradas": url_completa,
            "url_info":     url_completa,
            "fuente":       "club_impro",
        })

    # ── Patrón 2 (fallback): links cuyo texto contiene keywords de impro
    if not events:
        for a in soup.find_all("a", href=True):
            titulo = a.get_text(strip=True)
            if not titulo or len(titulo) < 4:
                continue
            if not any(kw in titulo.lower() for kw in KEYWORDS):
                continue
            if titulo.lower() in seen:
                continue
            seen.add(titulo.lower())
            href         = a["href"]
            url_completa = href if href.startswith("http") else BASE + href
            events.append({
                "titulo":       titulo.title(),
                "tipo":         _classify(titulo),
                "fecha":        "",
                "sala":         "El Club de la Impro",
                "direccion":    "C/ Santa Ana, 6, Madrid",
                "precio":       None,
                "url_entradas": url_completa,
                "url_info":     url_completa,
                "fuente":       "club_impro",
            })

    return events


if __name__ == "__main__":
    eventos = scrape()
    print(f"El Club de la Impro → {len(eventos)} eventos")
    for e in eventos:
        print(f"  · [{e['tipo']}] {e['titulo'][:40]:40} | {e['fecha']}")
