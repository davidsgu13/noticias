#!/usr/bin/env python3
"""
Recolecta noticias sobre el mercado financiero colombiano desde varias
fuentes (RSS directos + búsquedas en Google News) y las consolida en
data/news.json, que es lo que consume index.html.

Diseñado para tolerar fallos: si una fuente cae o cambia de URL, el
script sigue funcionando con las demás en lugar de romperse.
"""

import json
import re
import sys
import time
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Feeds RSS directos de medios colombianos. Si alguno deja de existir o
# cambia de URL, simplemente se ignora (ver fetch_feed).
DIRECT_FEEDS = [
    {"name": "Valora Analitik", "url": "https://www.valoraanalitik.com/feed/"},
    {"name": "El Tiempo - Economía", "url": "https://www.eltiempo.com/rss/economia.xml"},
    {"name": "Portafolio", "url": "https://www.portafolio.co/rss"},
    {"name": "La República", "url": "https://www.larepublica.co/rss"},
    {"name": "Bloomberg Línea", "url": "https://www.bloomberglinea.com/arc/outboundfeeds/rss/"},
]

# Búsquedas en Google News (agregan automáticamente decenas de medios
# colombianos: Portafolio, La República, Valora Analitik, Dinero, RCN,
# Bloomberg Línea, etc.) — es la fuente más confiable porque no depende
# de que un medio puntual mantenga su RSS vivo.
GOOGLE_NEWS_QUERIES = [
    {"name": "Mercado y bolsa (BVC)", "q": "BVC OR \"bolsa de valores de Colombia\" OR acciones Colombia"},
    {"name": "Dólar y TRM", "q": "TRM dólar peso colombiano"},
    {"name": "Banco de la República", "q": "Banco de la República tasa de interés Colombia"},
    {"name": "Economía Colombia", "q": "economía Colombia PIB inflación DANE"},
    {"name": "Finanzas y empresas", "q": "finanzas Colombia empresas resultados financieros"},
    {"name": "Deuda y renta fija", "q": "deuda pública Colombia TES renta fija"},
]

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=CO&ceid=CO:es-419"

MAX_ITEMS = 60          # tope de noticias que se guardan en el JSON final
MAX_AGE_DAYS = 4         # se descarta lo más viejo que esto
REQUEST_TIMEOUT = 12      # segundos por feed
OUTPUT_PATH = "data/news.json"

feedparser.USER_AGENT = (
    "Mozilla/5.0 (compatible; RadarCO-NewsBot/1.0; "
    "+https://github.com/) feedparser"
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def clean_html(text: str) -> str:
    """Quita etiquetas HTML simples que a veces vienen en el summary del RSS."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(entry) -> datetime:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None) or entry.get(key)
        if val:
            try:
                return datetime.fromtimestamp(time.mktime(val), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return datetime.now(timezone.utc)


def make_id(link: str, title: str) -> str:
    return hashlib.sha1(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def guess_source(entry, fallback: str) -> str:
    """Para Google News, el nombre real del medio suele venir en el título
    como 'Titular - Medio' o en entry.source.title."""
    src = getattr(entry, "source", None)
    if src and getattr(src, "title", None):
        return src.title
    title = entry.get("title", "")
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return fallback


def strip_source_suffix(title: str, source: str) -> str:
    suffix = f" - {source}"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title.strip()


# ---------------------------------------------------------------------------
# Recolección
# ---------------------------------------------------------------------------

def fetch_feed(url: str, fallback_name: str, category: str):
    """Descarga y parsea un feed. Nunca lanza excepción hacia afuera:
    si algo sale mal, devuelve una lista vacía y sigue el proceso."""
    items = []
    try:
        parsed = feedparser.parse(url, request_headers={"User-Agent": feedparser.USER_AGENT})
    except Exception as exc:  # pragma: no cover - defensivo
        print(f"  [aviso] no se pudo leer {fallback_name}: {exc}", file=sys.stderr)
        return items

    if getattr(parsed, "bozo", False) and not parsed.entries:
        print(f"  [aviso] feed vacío o mal formado: {fallback_name}", file=sys.stderr)
        return items

    for entry in parsed.entries:
        link = entry.get("link", "").strip()
        raw_title = entry.get("title", "").strip()
        if not link or not raw_title:
            continue

        source = guess_source(entry, fallback_name)
        title = strip_source_suffix(raw_title, source)
        published = parse_date(entry)
        summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
        if len(summary) > 240:
            summary = summary[:237].rstrip() + "..."

        items.append(
            {
                "id": make_id(link, raw_title),
                "title": title,
                "link": link,
                "source": source,
                "category": category,
                "summary": summary,
                "published": published.isoformat(),
                "published_ts": published.timestamp(),
            }
        )
    return items


def collect_all():
    all_items = []

    print("Descargando feeds directos de medios...")
    for feed in DIRECT_FEEDS:
        found = fetch_feed(feed["url"], feed["name"], category="fuente directa")
        print(f"  - {feed['name']}: {len(found)} noticias")
        all_items.extend(found)

    print("Descargando búsquedas de Google News...")
    for q in GOOGLE_NEWS_QUERIES:
        url = GOOGLE_NEWS_BASE.format(q=quote(q["q"]))
        found = fetch_feed(url, "Google News", category=q["name"])
        print(f"  - {q['name']}: {len(found)} noticias")
        all_items.extend(found)

    return all_items


def dedupe_and_filter(items):
    seen_links = set()
    seen_titles = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    deduped = []

    # más nuevo primero, para que al deduplicar por título nos quedemos
    # con la versión más reciente
    items.sort(key=lambda x: x["published_ts"], reverse=True)

    for item in items:
        link_key = item["link"].split("?")[0].rstrip("/")
        title_key = re.sub(r"\W+", "", item["title"].lower())[:80]

        if link_key in seen_links or title_key in seen_titles:
            continue
        if item["published_ts"] < cutoff.timestamp():
            continue

        seen_links.add(link_key)
        seen_titles.add(title_key)
        deduped.append(item)

    return deduped[:MAX_ITEMS]


def main():
    raw_items = collect_all()
    print(f"Total bruto recolectado: {len(raw_items)}")

    final_items = dedupe_and_filter(raw_items)
    print(f"Total final tras deduplicar y filtrar: {len(final_items)}")

    for item in final_items:
        item.pop("published_ts", None)

    now = datetime.now(timezone.utc)
    payload = {
        "last_updated_utc": now.isoformat(),
        "count": len(final_items),
        "items": final_items,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Guardado en {OUTPUT_PATH}")

    if not final_items:
        print("[aviso] no se recolectó ninguna noticia; se conserva el JSON anterior si existía.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
