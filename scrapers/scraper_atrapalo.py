"""
Capa 2 — Atrápalo (Playwright)
Extrae todos los eventos de impro en Madrid ciudad.
Requiere: pip install playwright beautifulsoup4 && playwright install chromium
"""

import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL  = "https://www.atrapalo.com/entradas/madrid/madrid/teatro-y-danza/impro/"
BASE = "https://www.atrapalo.com"


def _classify(titulo):
    t = titulo.lower()
    if any(w in t for w in ["taller", "workshop"]):  return "taller"
    if "muestra" in t:                                return "muestra"
    if re.search(r'\bjam\b', t):                      return "taller"
    return "show"


def scrape():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, timeout=25000)
        page.wait_for_timeout(4000)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    events = []

    # container-event-data = outer card (43 eventos, sin duplicados)
    for card in soup.find_all("div", class_=lambda c: c and "container-event-data" in c):
        inner = card.find("div", class_=lambda c: c and "item-data" in c)
        if not inner:
            continue

        h2 = inner.find("h2", class_="nombre")
        if not h2:
            continue
        a = h2.find("a")
        if not a:
            continue

        titulo = a.get_text(strip=True)
        href   = a.get("href", "")
        if not titulo or not href:
            continue

        # Sala
        sala_tag = inner.find("a", class_=lambda c: c and "locality" in c)
        sala = sala_tag.get_text(strip=True) if sala_tag else "Madrid"

        # Fecha (dentro de event-info-container)
        fecha = ""
        info = inner.find("div", class_="event-info-container")
        if info:
            span = info.find("span")
            if span:
                fecha = span.get_text(strip=True)

        # Precio: span.value en el padre del card
        parent = card.parent
        precio = None
        if parent:
            price_span = parent.find("span", class_="value")
            if price_span:
                raw = price_span.get_text(strip=True).replace("€", "").replace(",", ".").strip()
                try:
                    precio = f"{float(raw):.0f}€"
                except ValueError:
                    pass

        url_completa = BASE + href if href.startswith("/") else href

        events.append({
            "titulo":       titulo,
            "tipo":         _classify(titulo),
            "fecha":        fecha,
            "sala":         sala,
            "direccion":    "Madrid",
            "precio":       precio,
            "url_entradas": url_completa,
            "url_info":     url_completa,
            "fuente":       "atrapalo",
        })

    return events


if __name__ == "__main__":
    eventos = scrape()
    print(f"Atrápalo → {len(eventos)} eventos")
    for e in eventos[:8]:
        print(f"  · [{e['tipo']}] {e['titulo'][:35]:35} | {e['fecha']:20} | {e['sala'][:25]:25} | {e['precio']}")
