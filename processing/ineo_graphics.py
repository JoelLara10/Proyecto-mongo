import html
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from statistics import mean, median

try:
    from bson.decimal128 import Decimal128
except ImportError:
    Decimal128 = None


MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
RESULTS_DIR = Path(__file__).resolve().parent / "results"
CACHE_FILE = RESULTS_DIR / "ineo_graphics_cache.json"
CACHE_TTL_SECONDS = 30 * 60
CACHE_VERSION = 3
MAX_SAMPLE = 700

OCULAR_KEYWORDS = (
    "OJO",
    "OCULAR",
    "OFTALMO",
    "OPTICO",
    "OPTICA",
    "RETINA",
    "MACULA",
    "OCT",
    "FONDO",
    "GLAUCOMA",
    "TONOMETRIA",
    "CAMPIMETRIA",
    "CORNEA",
    "PAQUIMETRIA",
    "TOPOGRAFIA",
    "ANGIOGRAFIA",
    "CATARATA",
    "CRISTALINO",
    "REFRACCION",
    "AGUDEZA",
    "BIOMETRIA",
)

# Paleta clínica "Iris" — inspirada en la exploración ocular (azul iris,
# verde-teal de fondo de ojo, ámbar de alerta pupilar). Pensada para personal
# clínico y administrativo: alto contraste sobre fondo claro, tonos que no se
# confunden entre sí y una identidad propia (no el degradado violeta genérico
# de plantilla).
CHART_COLORS = ["#1E5F8C", "#0F766E", "#B45309", "#6D28D9", "#B91C1C", "#0891B2", "#4D7C0F"]
COLOR_PRIMARY = "#1E5F8C"        # Azul iris — indicador principal
COLOR_PRIMARY_LIGHT = "#A9CBE6"  # Azul iris claro — series secundarias
COLOR_PRIMARY_DARK = "#123A57"   # Azul iris oscuro — acentos y texto sobre color
COLOR_SUCCESS = "#0F766E"        # Verde-teal — valores dentro de rango / positivos
COLOR_WARNING = "#B45309"        # Ámbar — atención media
COLOR_DANGER = "#B91C1C"         # Rojo clínico — fuera de rango / alerta
COLOR_PURPLE = "#6D28D9"         # Violeta — categoría distintiva
COLOR_TEAL = "#0891B2"           # Cian — categoría distintiva
COLOR_GRID = "#DDE6F0"
COLOR_AXIS = "#5B6B85"
COLOR_TEXT = "#16233B"
COLOR_MUTED = "#64748B"
COLOR_CARD_BG = "#FDFEFF"
FONT_STACK = "'Inter','Segoe UI',Helvetica,Arial,sans-serif"

FILTER_KEYS = {
    "trend_months", "trend_type", "area_type", "area_top",
    "exam_top", "exam_order", "exam_type", "profile_top",
    "profile_order", "amount_top", "amount_order",
    "sign_variable", "revenue_top",
}


def empty_context(error=None):
    return {
        "cache_version": CACHE_VERSION,
        "fecha_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "desde_cache": False,
        "metricas": [],
        "graficas": [],
        "hallazgos": [],
        "presentacion": [],
        "estadistica": {},
        "filter_values": {},
        "error": error,
    }


def _normalize_text(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    return text.encode("ascii", "ignore").decode("ascii").upper().strip()


def _safe_label(value, fallback="Sin dato", max_len=36):
    text = str(value or fallback).strip()
    if len(text) > max_len:
        return f"{text[: max_len - 3]}..."
    return text


def _to_float(value, default=0.0):
    if value is None:
        return default
    if Decimal128 is not None and isinstance(value, Decimal128):
        value = value.to_decimal()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return default if isinstance(value, float) and math.isnan(value) else float(value)
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        cleaned = value.strip().replace("Z", "")
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(cleaned.split(".")[0], fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(cleaned)
        except ValueError:
            return None
    return None


def _calculate_age(value):
    born = _to_datetime(value)
    if born is None:
        return None
    today = datetime.now()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return age if 0 <= age <= 120 else None


def _month_label(value):
    try:
        year, month = str(value).split("-")
        return f"{MONTHS_ES[int(month) - 1]} {year[-2:]}"
    except (ValueError, IndexError):
        return str(value)


def _last_month_keys(count=12):
    """Devuelve meses calendario consecutivos, incluido el mes actual."""
    current = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    keys = []
    for offset in range(count - 1, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        keys.append(f"{year:04d}-{month:02d}")
    return keys


def _ocular_regex():
    return "|".join(re.escape(word) for word in OCULAR_KEYWORDS)


def _is_ocular_text(value):
    text = _normalize_text(value)
    return any(keyword in text for keyword in OCULAR_KEYWORDS)


def _exam_profile(value):
    text = _normalize_text(value)
    if any(key in text for key in ("RETINA", "MACULA", "OCT", "FONDO", "ANGIOGRAFIA")):
        return "Retina y macula"
    if any(key in text for key in ("GLAUCOMA", "TONOMETRIA", "CAMPIMETRIA", "PRESION")):
        return "Glaucoma"
    if any(key in text for key in ("CORNEA", "PAQUIMETRIA", "TOPOGRAFIA")):
        return "Cornea"
    if any(key in text for key in ("CATARATA", "CRISTALINO", "BIOMETRIA")):
        return "Catarata"
    if any(key in text for key in ("REFRACCION", "AGUDEZA", "OPTICA")):
        return "Vision y refraccion"
    return "Otros estudios"


def _parse_ta(value):
    if not value:
        return None
    match = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", str(value))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _cache_is_valid():
    if not CACHE_FILE.exists() or (datetime.now().timestamp() - CACHE_FILE.stat().st_mtime) >= CACHE_TTL_SECONDS:
        return False
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file).get("cache_version") == CACHE_VERSION
    except (OSError, ValueError, TypeError):
        return False


def _read_cache():
    with open(CACHE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    data["desde_cache"] = True
    return data


def _write_cache(data):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False)


def _safe_count(collection, query=None):
    try:
        return collection.count_documents(query or {})
    except Exception:
        return 0


def _aggregate_list(collection, pipeline):
    try:
        return list(collection.aggregate(pipeline, allowDiskUse=True))
    except Exception:
        return []


def _find_list(collection, query, projection=None, limit=MAX_SAMPLE, sort_field="_id"):
    try:
        cursor = collection.find(query, projection or {})
        if sort_field:
            cursor = cursor.sort(sort_field, -1)
        return list(cursor.limit(limit))
    except Exception:
        return []


def _format_money(value):
    return f"${value:,.2f}"


def _scale(value, max_value, max_px):
    if max_value <= 0:
        return 0
    return value / max_value * max_px


def _filter_choice(filters, key, allowed, default):
    value = str((filters or {}).get(key, default))
    return value if value in allowed else default


def _nice_axis_max(value, ticks=5):
    """Devuelve un máximo redondeado para construir una escala legible."""
    if value <= 0:
        return 1.0
    rough_step = value / max(ticks, 1)
    magnitude = 10 ** math.floor(math.log10(rough_step))
    normalized = rough_step / magnitude
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return nice * magnitude * ticks


def _axis_ticks(max_value, count=5):
    axis_max = _nice_axis_max(max_value, count)
    return axis_max, [axis_max * index / count for index in range(count + 1)]


def _format_tick(value, money=False):
    if money:
        return f"${value:,.0f}"
    if abs(value) >= 1000:
        return f"{value / 1000:.1f}k"
    return f"{value:.0f}"


def _svg_text(text):
    return html.escape(str(text), quote=True)


def _svg_defs():
    return (
        "<defs>"
        '<filter id="chartShadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="2.4" flood-color="#0F2942" flood-opacity="0.18"/>'
        "</filter>"
        '<linearGradient id="areaFade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{COLOR_PRIMARY}" stop-opacity="0.38"/>'
        f'<stop offset="100%" stop-color="{COLOR_PRIMARY}" stop-opacity="0.02"/>'
        "</linearGradient>"
        "</defs>"
        f"<style>text{{font-family:{FONT_STACK};}}</style>"
    )


def _svg_shell(width, height, body):
    return (
        f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="{FONT_STACK}">'
        f"{_svg_defs()}{body}</svg>"
    )


def _line_svg(rows, chart_type="line"):
    width, height = 900, 420
    if not rows:
        return _empty_svg(width, height, "Tendencia de atenciones", "No hay fechas suficientes para graficar.")

    labels = [row["label"] for row in rows]
    values = [float(row["total"]) for row in rows]
    max_value = max(values) or 1
    axis_max, ticks = _axis_ticks(max_value)
    avg_value = mean(values)
    left, right, top, bottom = 72, 30, 44, 76
    chart_w, chart_h = width - left - right, height - top - bottom
    step = chart_w / max(len(values) - 1, 1)
    points = []

    for index, value in enumerate(values):
        x = left + index * step
        y = top + chart_h - _scale(value, axis_max, chart_h)
        points.append((x, y))

    avg_y = top + chart_h - _scale(avg_value, axis_max, chart_h)
    max_index = values.index(max_value)
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"{left},{top + chart_h} {polyline} {left + chart_w},{top + chart_h}"
    body = [
        f'<rect width="900" height="420" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="450" y="25" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Tendencia mensual de atenciones INEO</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
        f'<line x1="{left}" y1="{avg_y:.1f}" x2="{left + chart_w}" y2="{avg_y:.1f}" stroke="{COLOR_DANGER}" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<text x="{left + chart_w - 4}" y="{avg_y - 6:.1f}" text-anchor="end" font-size="12" font-weight="700" fill="{COLOR_DANGER}">Promedio {avg_value:.1f}</text>',
    ]

    for tick in ticks:
        y = top + chart_h - _scale(tick, axis_max, chart_h)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLOR_AXIS}">{_format_tick(tick)}</text>')

    if chart_type == "bar":
        slot = chart_w / max(len(values), 1)
        bar_w = min(52, slot * 0.62)
        for index, value in enumerate(values):
            x = left + index * slot + (slot - bar_w) / 2
            h = _scale(value, axis_max, chart_h)
            y = top + chart_h - h
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="5" fill="{COLOR_PRIMARY}" filter="url(#chartShadow)"/>')
            body.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{COLOR_TEXT}">{int(value)}</text>')
            points[index] = (x + bar_w / 2, y)
    else:
        body.append(f'<polygon points="{area}" fill="url(#areaFade)"/>')
        body.append(f'<polyline points="{polyline}" fill="none" stroke="{COLOR_PRIMARY}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" filter="url(#chartShadow)"/>')

    for index, (x, y) in enumerate(points):
        color = COLOR_SUCCESS if index == max_index else COLOR_PRIMARY
        if chart_type != "bar":
            radius = 8 if index == max_index else 6
            body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="#ffffff" stroke="{color}" stroke-width="3"/>')
            body.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{COLOR_TEXT}">{int(values[index])}</text>')
        body.append(f'<text x="{x:.1f}" y="{top + chart_h + 28}" text-anchor="middle" font-size="11" fill="{COLOR_MUTED}" transform="rotate(-28 {x:.1f},{top + chart_h + 28})">{_svg_text(labels[index])}</text>')

    body.append(f'<text x="18" y="215" transform="rotate(-90 18,215)" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Cantidad de atenciones</text>')
    body.append(f'<text x="450" y="394" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Periodo (mes)</text>')
    body.append(f'<text x="450" y="414" text-anchor="middle" font-size="10" fill="{COLOR_MUTED}">Fuente: MongoDB INEO | Frecuencia mensual</text>')
    return _svg_shell(width, height, "".join(body))


def _donut_svg(area_counts, top_n=4):
    width, height = 760, 420
    if not area_counts:
        return _empty_svg(width, height, "Composición por área", "No hay áreas de atención registradas.")

    ordered = sorted(area_counts.items(), key=lambda item: item[1], reverse=True)
    top_n = max(3, min(int(top_n), 7))
    if len(ordered) > top_n:
        ordered = ordered[: top_n - 1] + [("Otros", sum(value for _, value in ordered[top_n - 1:]))]

    total = sum(value for _, value in ordered) or 1
    cx, cy, radius = 250, 220, 112
    circumference = 2 * math.pi * radius
    offset = 0
    body = [
        f'<rect width="760" height="420" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="380" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Composición de atenciones por área</text>',
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#E7EDF4" stroke-width="58"/>',
    ]

    for index, (label, value) in enumerate(ordered):
        length = value / total * circumference
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="58" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" stroke-dashoffset="{-offset:.2f}" '
            'transform="rotate(-90 250 220)" stroke-linecap="butt"/>'
        )
        pct = value / total * 100
        y = 126 + index * 48
        body.append(f'<rect x="440" y="{y - 15}" width="18" height="18" rx="5" fill="{color}"/>')
        body.append(f'<text x="468" y="{y}" font-size="13" font-weight="700" fill="{COLOR_TEXT}">{_svg_text(label)}</text>')
        body.append(f'<text x="468" y="{y + 18}" font-size="12" fill="{COLOR_MUTED}">{value} atenciones | {pct:.1f}%</text>')
        offset += length

    body.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="28" font-weight="800" fill="{COLOR_TEXT}">{total}</text>')
    body.append(f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="12" fill="{COLOR_MUTED}">Total</text>')
    body.append(f'<text x="380" y="405" text-anchor="middle" font-size="11" fill="{COLOR_MUTED}">Cada segmento muestra cantidad y porcentaje del total</text>')
    return _svg_shell(width, height, "".join(body))


def _area_bar_svg(area_counts, top_n=4):
    ordered = sorted(area_counts.items(), key=lambda item: item[1], reverse=True)[: max(3, min(int(top_n), 7))]
    return _bar_svg(
        "Atenciones por área",
        ordered,
        "Cantidad de atenciones",
        x_label="Área de atención",
    )


def _barh_svg(rows):
    width, height = 900, 430
    if not rows:
        return _empty_svg(width, height, "Estudios oculares más frecuentes", "No hay estudios para graficar.")

    rows = list(rows[:7])
    max_value = max(value for _, value in rows) or 1
    axis_max, ticks = _axis_ticks(max_value)
    left, top, bar_h, gap = 260, 64, 28, 20
    chart_w = 560
    avg_value = mean([value for _, value in rows])
    avg_x = left + _scale(avg_value, axis_max, chart_w)
    body = [
        f'<rect width="900" height="430" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Estudios oculares más frecuentes</text>',
        f'<line x1="{avg_x:.1f}" y1="54" x2="{avg_x:.1f}" y2="372" stroke="{COLOR_DANGER}" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<text x="{avg_x + 5:.1f}" y="52" font-size="12" font-weight="700" fill="{COLOR_DANGER}">Promedio {avg_value:.1f}</text>',
    ]

    for tick in ticks:
        x = left + _scale(tick, axis_max, chart_w)
        body.append(f'<line x1="{x:.1f}" y1="54" x2="{x:.1f}" y2="372" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{x:.1f}" y="391" text-anchor="middle" font-size="11" fill="{COLOR_AXIS}">{_format_tick(tick)}</text>')

    for index, (label, value) in enumerate(rows):
        y = top + index * (bar_h + gap)
        bar_w = _scale(value, axis_max, chart_w)
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(f'<text x="245" y="{y + 19}" text-anchor="end" font-size="12" fill="{COLOR_AXIS}">{_svg_text(_safe_label(label, max_len=32))}</text>')
        body.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="6" fill="{color}" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{left + bar_w + 8:.1f}" y="{y + 19}" font-size="12" font-weight="700" fill="{COLOR_TEXT}">{value}</text>')

    body.append(f'<text x="540" y="416" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Cantidad de solicitudes</text>')
    return _svg_shell(width, height, "".join(body))


def _bar_svg(title, rows, y_label, x_label="Categoría"):
    width, height = 840, 420
    if not rows:
        return _empty_svg(width, height, title, "No hay datos suficientes.")

    max_value = max(value for _, value in rows) or 1
    axis_max, ticks = _axis_ticks(max_value)
    left, top, bottom = 70, 58, 78
    chart_w, chart_h = width - left - 36, height - top - bottom
    slot = chart_w / len(rows)
    bar_w = min(62, slot * 0.62)
    body = [
        f'<rect width="840" height="420" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="420" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">{_svg_text(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
    ]

    for tick in ticks:
        y = top + chart_h - _scale(tick, axis_max, chart_h)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLOR_AXIS}">{_format_tick(tick)}</text>')

    for index, (label, value) in enumerate(rows):
        x = left + index * slot + (slot - bar_w) / 2
        h = _scale(value, axis_max, chart_h)
        y = top + chart_h - h
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="6" fill="{color}" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="{COLOR_TEXT}">{value}</text>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + chart_h + 28}" text-anchor="middle" font-size="11" fill="{COLOR_MUTED}">{_svg_text(_safe_label(label, max_len=16))}</text>')

    body.append(f'<text x="18" y="215" transform="rotate(-90 18,215)" font-size="13" font-weight="700" fill="{COLOR_AXIS}">{_svg_text(y_label)}</text>')
    body.append(f'<text x="420" y="395" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">{_svg_text(x_label)}</text>')
    body.append(f'<text x="420" y="414" text-anchor="middle" font-size="10" fill="{COLOR_MUTED}">Fuente: MongoDB INEO | Valores mostrados sobre cada barra</text>')
    return _svg_shell(width, height, "".join(body))


def _sign_alert_rate_svg(rows):
    """Compara tasas, no conteos crudos, para evitar sesgo por datos faltantes."""
    width, height = 900, 420
    if not rows or not any(row[2] for row in rows):
        return _empty_svg(width, height, "Alertas de signos vitales", "No hay mediciones válidas para comparar.")

    left, top, chart_w, chart_h = 82, 58, 770, 270
    slot = chart_w / len(rows)
    bar_w = min(76, slot * 0.56)
    body = [
        f'<rect width="900" height="420" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Porcentaje de mediciones fuera de rango</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
    ]
    for tick in range(0, 101, 20):
        y = top + chart_h - tick / 100 * chart_h
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLOR_AXIS}">{tick}%</text>')
    for index, (label, alerts, valid) in enumerate(rows):
        rate = alerts / valid * 100 if valid else 0
        x = left + index * slot + (slot - bar_w) / 2
        h = rate / 100 * chart_h
        y = top + chart_h - h
        color = COLOR_DANGER if rate >= 20 else COLOR_WARNING if rate > 0 else COLOR_SUCCESS
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="6" fill="{color}" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{max(y - 9, top + 13):.1f}" text-anchor="middle" font-size="12" font-weight="800" fill="{COLOR_TEXT}">{rate:.1f}%</text>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + chart_h + 25}" text-anchor="middle" font-size="12" font-weight="700" fill="{COLOR_TEXT}">{_svg_text(label)}</text>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + chart_h + 43}" text-anchor="middle" font-size="10" fill="{COLOR_AXIS}">{alerts} de {valid}</text>')
    body.append(f'<text x="22" y="210" transform="rotate(-90 22,210)" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Mediciones fuera de rango (%)</text>')
    body.append(f'<text x="450" y="386" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Variable de signos vitales</text>')
    body.append(f'<text x="450" y="408" text-anchor="middle" font-size="10" fill="{COLOR_MUTED}">El denominador se muestra debajo de cada variable; escala fija de 0% a 100%</text>')
    legend_items = ((COLOR_SUCCESS, "Sin alertas"), (COLOR_WARNING, "Alerta moderada (&lt;20%)"), (COLOR_DANGER, "Alerta alta (≥20%)"))
    for index, (color, text) in enumerate(legend_items):
        lx = left + index * 220
        body.append(f'<rect x="{lx:.1f}" y="34" width="12" height="12" rx="3" fill="{color}"/>')
        body.append(f'<text x="{lx + 18:.1f}" y="44" font-size="10.5" fill="{COLOR_AXIS}">{text}</text>')
    return _svg_shell(width, height, "".join(body))


def _revenue_type_svg(rows):
    """Ranking administrativo por ingreso; evita una correlación tautológica con subtotal."""
    width, height = 900, 430
    if not rows:
        return _empty_svg(width, height, "Ingresos por tipo de servicio", "No hay cargos con subtotal y tipo válidos.")
    rows = rows[:7]
    max_value = max(row[1] for row in rows) or 1
    axis_max, ticks = _axis_ticks(max_value)
    left, top, chart_w, bar_h, gap = 235, 62, 610, 30, 18
    total = sum(row[1] for row in rows) or 1
    body = [
        f'<rect width="900" height="430" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Ingresos registrados por tipo de servicio</text>',
    ]
    for tick in ticks:
        x = left + _scale(tick, axis_max, chart_w)
        body.append(f'<line x1="{x:.1f}" y1="52" x2="{x:.1f}" y2="370" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{x:.1f}" y="391" text-anchor="middle" font-size="10" fill="{COLOR_AXIS}">{_format_tick(tick, money=True)}</text>')
    for index, (label, amount, count) in enumerate(rows):
        y = top + index * (bar_h + gap)
        bar_w = _scale(amount, axis_max, chart_w)
        pct = amount / total * 100
        color = COLOR_PRIMARY if index == 0 else COLOR_PRIMARY_LIGHT
        body.append(f'<text x="220" y="{y + 20}" text-anchor="end" font-size="12" fill="{COLOR_TEXT}">{_svg_text(_safe_label(label, max_len=27))}</text>')
        body.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="5" fill="{color}" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{min(left + bar_w + 8, 838):.1f}" y="{y + 13}" font-size="11" font-weight="800" fill="{COLOR_TEXT}">{_svg_text(_format_money(amount))}</text>')
        body.append(f'<text x="{min(left + bar_w + 8, 838):.1f}" y="{y + 27}" font-size="9" fill="{COLOR_AXIS}">{pct:.1f}% · {count} cargos</text>')
    body.append(f'<text x="540" y="416" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Ingreso acumulado en cargos (MXN)</text>')
    return _svg_shell(width, height, "".join(body))


def _service_amount_svg(rows):
    """Compara importes promedio por servicio mediante barras y etiquetas directas."""
    width, height = 1100, 500
    if not rows:
        return _empty_svg(width, height, "Importe promedio por servicio", "No hay servicios con importes válidos.")

    rows = rows[:7]
    max_value = max(row[1] for row in rows) or 1
    axis_max, ticks = _axis_ticks(max_value)
    left, top, chart_w, bar_h, gap = 330, 65, 680, 34, 20
    body = [
        f'<rect width="1100" height="500" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="550" y="30" text-anchor="middle" font-size="22" font-weight="800" fill="{COLOR_TEXT}">Importe promedio por servicio</text>',
    ]
    for tick in ticks:
        x = left + _scale(tick, axis_max, chart_w)
        body.append(f'<line x1="{x:.1f}" y1="52" x2="{x:.1f}" y2="425" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{x:.1f}" y="448" text-anchor="middle" font-size="12" fill="{COLOR_AXIS}">{_format_tick(tick, money=True)}</text>')

    for index, (label, average, count) in enumerate(rows):
        y = top + index * (bar_h + gap)
        bar_w = _scale(average, axis_max, chart_w)
        color = COLOR_PRIMARY if index == 0 else COLOR_PRIMARY_LIGHT
        body.append(f'<text x="315" y="{y + 22}" text-anchor="end" font-size="13" fill="{COLOR_TEXT}">{_svg_text(_safe_label(label, max_len=39))}</text>')
        body.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="6" fill="{color}" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{min(left + bar_w + 10, 1025):.1f}" y="{y + 15}" font-size="12" font-weight="800" fill="{COLOR_TEXT}">{_svg_text(_format_money(average))}</text>')
        body.append(f'<text x="{min(left + bar_w + 10, 1025):.1f}" y="{y + 29}" font-size="10" fill="{COLOR_AXIS}">n={count}</text>')

    body.append(f'<text x="670" y="480" text-anchor="middle" font-size="14" font-weight="700" fill="{COLOR_AXIS}">Importe promedio del cargo (MXN)</text>')
    return _svg_shell(width, height, "".join(body))


def _histogram_box_svg(amounts, bins_count=None):
    width, height = 900, 440
    clean = sorted(value for value in amounts if value > 0)
    if len(clean) < 3:
        return _empty_svg(width, height, "Distribución de importes por servicio", "Se necesitan al menos 3 importes.")

    min_value, max_value = clean[0], clean[-1]
    if min_value == max_value:
        max_value = min_value + 1

    bins_count = int(bins_count or min(10, max(5, int(math.sqrt(len(clean))))))
    bins_count = max(5, min(bins_count, 12))
    step = (max_value - min_value) / bins_count
    bins = [0] * bins_count
    for value in clean:
        index = min(int((value - min_value) / step), bins_count - 1)
        bins[index] += 1

    avg = mean(clean)
    med = median(clean)
    q1 = _percentile(clean, 25)
    q3 = _percentile(clean, 75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    outliers = [value for value in clean if value > upper]
    left, top, chart_w, chart_h = 72, 64, 790, 210
    max_bin = max(bins) or 1
    axis_max, y_ticks = _axis_ticks(max_bin)
    slot = chart_w / bins_count
    box_y = 335

    def x_for(value):
        return left + (value - min_value) / (max_value - min_value) * chart_w

    body = [
        f'<rect width="900" height="440" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Distribución de importes por servicio</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="{COLOR_AXIS}"/>',
    ]

    for tick in y_ticks:
        y = top + chart_h - _scale(tick, axis_max, chart_h)
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="{COLOR_GRID}" stroke-dasharray="4 4"/>')
        body.append(f'<text x="{left - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{COLOR_AXIS}">{_format_tick(tick)}</text>')

    for index, count in enumerate(bins):
        h = _scale(count, axis_max, chart_h)
        x = left + index * slot + 4
        y = top + chart_h - h
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot - 8:.1f}" height="{h:.1f}" rx="5" fill="{COLOR_PRIMARY}" opacity="0.82" filter="url(#chartShadow)"/>')
        body.append(f'<text x="{x + (slot - 8) / 2:.1f}" y="{y - 7:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="{COLOR_TEXT}">{count}</text>')

    for index in range(bins_count + 1):
        value = min_value + index * step
        x = left + index * slot
        if index % max(1, math.ceil(bins_count / 5)) == 0 or index == bins_count:
            body.append(f'<text x="{x:.1f}" y="{top + chart_h + 23}" text-anchor="middle" font-size="10" fill="{COLOR_AXIS}">{_format_tick(value, money=True)}</text>')

    for value, color, label in ((avg, COLOR_DANGER, "Media"), (med, COLOR_SUCCESS, "Mediana")):
        x = x_for(value)
        body.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_h}" stroke="{color}" stroke-width="2" stroke-dasharray="6 4"/>')
        body.append(f'<text x="{x + 4:.1f}" y="{top + 14}" font-size="11" font-weight="700" fill="{color}">{label}</text>')

    q1_x, q3_x, med_x = x_for(q1), x_for(q3), x_for(med)
    body.append(f'<line x1="{left}" y1="{box_y}" x2="{left + chart_w}" y2="{box_y}" stroke="{COLOR_AXIS}" stroke-width="2"/>')
    body.append(f'<rect x="{q1_x:.1f}" y="{box_y - 24}" width="{max(q3_x - q1_x, 3):.1f}" height="48" rx="6" fill="#CFE8E4" stroke="{COLOR_SUCCESS}" stroke-width="2"/>')
    body.append(f'<line x1="{med_x:.1f}" y1="{box_y - 28}" x2="{med_x:.1f}" y2="{box_y + 28}" stroke="{COLOR_PRIMARY_DARK}" stroke-width="3"/>')
    body.append(f'<text x="18" y="170" transform="rotate(-90 18,170)" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Frecuencia de cargos</text>')
    body.append(f'<text x="450" y="305" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Importe del servicio (MXN)</text>')
    body.append(f'<text x="{left}" y="393" font-size="12" fill="{COLOR_AXIS}">Q1 ${q1:,.0f} | Mediana ${med:,.0f} | Q3 ${q3:,.0f} | Atípicos {len(outliers)}</text>')
    body.append(f'<text x="450" y="424" text-anchor="middle" font-size="11" fill="{COLOR_MUTED}">Caja inferior: 50 % central de los importes y mediana</text>')
    return _svg_shell(width, height, "".join(body))


def _heatmap_svg(matrix):
    width, height = 600, 430
    labels = ["Cantidad", "Precio", "Subtotal"]
    if not matrix:
        return _empty_svg(width, height, "Relación financiera", "No hay cargos suficientes para calcular la correlación.")

    cell, start_x, start_y = 82, 150, 82
    body = [
        f'<rect width="600" height="430" rx="18" fill="{COLOR_CARD_BG}"/>',
        f'<text x="300" y="30" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">Relación entre cantidad, precio y subtotal</text>',
    ]

    for index, label in enumerate(labels):
        body.append(f'<text x="{start_x + index * cell + cell / 2}" y="68" text-anchor="middle" font-size="12" font-weight="700" fill="{COLOR_AXIS}">{label}</text>')
        body.append(f'<text x="138" y="{start_y + index * cell + cell / 2 + 5}" text-anchor="end" font-size="12" font-weight="700" fill="{COLOR_AXIS}">{label}</text>')

    for row in range(3):
        for col in range(3):
            value = matrix[row][col]
            color = _corr_color(value)
            x = start_x + col * cell
            y = start_y + row * cell
            body.append(f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="8" fill="{color}" filter="url(#chartShadow)"/>')
            body.append(f'<text x="{x + cell / 2}" y="{y + cell / 2 + 5}" text-anchor="middle" font-size="16" font-weight="800" fill="#ffffff">{value:.2f}</text>')

    body.append(f'<text x="274" y="354" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Variable comparada (eje X)</text>')
    body.append(f'<text x="52" y="205" transform="rotate(-90 52,205)" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_AXIS}">Variable de origen (eje Y)</text>')
    legend_colors = [_corr_color(-1), _corr_color(-0.5), _corr_color(0), _corr_color(0.5), _corr_color(1)]
    for index, color in enumerate(legend_colors):
        body.append(f'<rect x="390" y="{105 + index * 34}" width="24" height="34" fill="{color}"/>')
    body.append(f'<text x="424" y="117" font-size="10" fill="{COLOR_AXIS}">-1 inversa</text>')
    body.append(f'<text x="424" y="188" font-size="10" fill="{COLOR_AXIS}">0 sin relación lineal</text>')
    body.append(f'<text x="424" y="252" font-size="10" fill="{COLOR_AXIS}">1 directa</text>')
    body.append(f'<text x="300" y="404" text-anchor="middle" font-size="11" fill="{COLOR_MUTED}">Coeficiente de Pearson: de -1 a 1 | Correlación no implica causalidad</text>')
    return _svg_shell(width, height, "".join(body))


def _empty_svg(width, height, title, message):
    return _svg_shell(
        width,
        height,
        (
            f'<rect width="{width}" height="{height}" rx="18" fill="{COLOR_CARD_BG}"/>'
            f'<text x="{width / 2}" y="42" text-anchor="middle" font-size="20" font-weight="800" fill="{COLOR_TEXT}">{_svg_text(title)}</text>'
            f'<circle cx="{width / 2}" cy="{height / 2 - 26}" r="22" fill="none" stroke="{COLOR_GRID}" stroke-width="4"/>'
            f'<text x="{width / 2}" y="{height / 2 - 18}" text-anchor="middle" font-size="20" fill="{COLOR_MUTED}">!</text>'
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" font-size="14" fill="{COLOR_MUTED}">{_svg_text(message)}</text>'
        ),
    )


def _percentile(sorted_values, pct):
    if not sorted_values:
        return 0
    position = (len(sorted_values) - 1) * pct / 100
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[int(position)]
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def _hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _lerp_color(color_a, color_b, ratio):
    ra, ga, ba = _hex_to_rgb(color_a)
    rb, gb, bb = _hex_to_rgb(color_b)
    ratio = max(0.0, min(1.0, ratio))
    return (
        round(ra + (rb - ra) * ratio),
        round(ga + (gb - ga) * ratio),
        round(ba + (bb - ba) * ratio),
    )


def _corr_color(value):
    """Escala divergente roja (inversa) -> gris neutro (0) -> teal (directa)."""
    value = max(-1, min(1, value))
    neutral = "#8091A6"
    if value >= 0:
        r, g, b = _lerp_color(neutral, COLOR_SUCCESS, value)
    else:
        r, g, b = _lerp_color(neutral, COLOR_DANGER, abs(value))
    return f"rgb({r},{g},{b})"


def _correlation_matrix(records):
    rows = []
    for record in records:
        cantidad = _to_float(record.get("cantidad"))
        precio = _to_float(record.get("precio"))
        subtotal = _to_float(record.get("subtotal"))
        if cantidad > 0 and precio > 0 and subtotal > 0:
            rows.append((cantidad, precio, subtotal))

    if len(rows) < 4:
        return []

    columns = list(zip(*rows))
    return [[_pearson(columns[row], columns[col]) for col in range(3)] for row in range(3)]


def _pearson(xs, ys):
    avg_x, avg_y = mean(xs), mean(ys)
    num = sum((x - avg_x) * (y - avg_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - avg_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - avg_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0
    return num / (den_x * den_y)


def _load_optimized_data(db):
    regex = _ocular_regex()

    total_pacientes = _safe_count(db["pacientes"])
    open_attentions = _safe_count(db["atencion"], {"status": "ABIERTA"})
    total_camas = _safe_count(db["camas"])
    camas_ocupadas = _safe_count(db["camas"], {"ocupada": 1})

    month_rows = _aggregate_list(
        db["atencion"],
        [
            {"$match": {"fecha_ing": {"$type": "date"}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$fecha_ing"}}, "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ],
    )
    month_map = {str(row["_id"]): int(row["total"]) for row in month_rows}
    month_counts = [
        {"key": key, "label": _month_label(key), "total": month_map.get(key, 0)}
        for key in _last_month_keys(12)
    ]

    area_rows = _aggregate_list(
        db["atencion"],
        [
            {"$group": {"_id": {"$ifNull": ["$area", "Sin area"]}, "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ],
    )
    area_counts = {str(row["_id"]): int(row["total"]) for row in area_rows}

    exam_rows = _aggregate_list(
        db["examenes_det"],
        [
            {"$match": {"nombre_examen": {"$regex": regex, "$options": "i"}}},
            {"$group": {"_id": "$nombre_examen", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}},
            {"$limit": 50},
        ],
    )
    ocular_only = True
    if not exam_rows:
        ocular_only = False
        exam_rows = _aggregate_list(
            db["examenes_det"],
            [
                {"$group": {"_id": "$nombre_examen", "total": {"$sum": 1}}},
                {"$sort": {"total": -1}},
                {"$limit": 50},
            ],
        )

    top_exams = [(_safe_label(row["_id"], "Sin nombre", 42), int(row["total"])) for row in exam_rows[:7]]
    profile_counter = Counter()
    for row in exam_rows:
        profile = _exam_profile(row["_id"]) if ocular_only else "Estudios registrados"
        profile_counter[profile] += int(row["total"])

    ocular_patients_rows = _aggregate_list(
        db["cuenta_paciente"],
        [
            {"$match": {"descripcion": {"$regex": regex, "$options": "i"}, "Id_exp": {"$ne": None}}},
            {"$group": {"_id": "$Id_exp"}},
            {"$count": "total"},
        ],
    )
    ocular_patients = int(ocular_patients_rows[0]["total"]) if ocular_patients_rows else 0

    financial_records = _find_list(
        db["cuenta_paciente"],
        {"subtotal": {"$gt": 0}},
        {"subtotal": 1, "cantidad": 1, "precio": 1, "tipo": 1, "descripcion": 1},
        limit=MAX_SAMPLE,
    )
    if not financial_records:
        financial_records = _find_list(
            db["examenes_det"],
            {"subtotal": {"$gt": 0}},
            {"subtotal": 1, "cantidad": 1, "precio": 1, "tipo": 1, "nombre_examen": 1},
            limit=MAX_SAMPLE,
        )
    subtotals = [_to_float(row.get("subtotal")) for row in financial_records if _to_float(row.get("subtotal")) > 0]

    signs = _find_list(
        db["signos_vitales"],
        {},
        {"ta": 1, "fc": 1, "fr": 1, "temp": 1, "spo2": 1, "fecha_registro": 1},
        limit=MAX_SAMPLE,
        sort_field="fecha_registro",
    )
    sign_stats = _count_sign_anomalies(signs)

    revenue_counter = defaultdict(lambda: {"amount": 0.0, "count": 0})
    service_counter = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for row in financial_records:
        label = _safe_label(row.get("tipo") or "Sin clasificar", max_len=30)
        service_label = _safe_label(
            row.get("descripcion") or row.get("nombre_examen") or "Sin descripción",
            max_len=48,
        )
        subtotal = _to_float(row.get("subtotal"))
        if subtotal > 0:
            revenue_counter[label]["amount"] += subtotal
            revenue_counter[label]["count"] += 1
            service_counter[service_label]["amount"] += subtotal
            service_counter[service_label]["count"] += 1
    revenue_by_type = sorted(
        [(label, values["amount"], values["count"]) for label, values in revenue_counter.items()],
        key=lambda item: item[1], reverse=True,
    )
    service_amounts = sorted(
        [
            (label, values["amount"] / values["count"], values["count"])
            for label, values in service_counter.items() if values["count"]
        ],
        key=lambda item: item[1], reverse=True,
    )

    patient_dates = _find_list(db["pacientes"], {}, {"fecnac": 1}, limit=MAX_SAMPLE, sort_field="_id")
    ages = [age for age in (_calculate_age(row.get("fecnac")) for row in patient_dates) if age is not None]

    diagnosticos_oculares = _safe_count(
        db["diagnosticos"],
        {
            "$or": [
                {"diagnostico_principal": {"$regex": regex, "$options": "i"}},
                {"diagnosticos_secundarios": {"$regex": regex, "$options": "i"}},
            ]
        },
    )

    return {
        "total_pacientes": total_pacientes,
        "open_attentions": open_attentions,
        "total_camas": total_camas,
        "camas_ocupadas": camas_ocupadas,
        "month_counts": month_counts,
        "area_counts": area_counts,
        "top_exams": top_exams,
        "profile_counts": dict(profile_counter.most_common(7)),
        "ocular_patients": ocular_patients,
        "subtotals": subtotals,
        "financial_records": financial_records,
        "signs_total_sample": len(signs),
        "sign_anomalies": sign_stats["alerts"],
        "sign_valid": sign_stats["valid"],
        "revenue_by_type": revenue_by_type,
        "service_amounts": service_amounts,
        "ages": ages,
        "diagnosticos_oculares": diagnosticos_oculares,
    }


def _count_sign_anomalies(signs):
    anomalies = defaultdict(int)
    valid = defaultdict(int)
    for sign in signs:
        fc = _to_float(sign.get("fc"), None)
        fr = _to_float(sign.get("fr"), None)
        temp = _to_float(sign.get("temp"), None)
        spo2 = _to_float(sign.get("spo2"), None)
        ta = _parse_ta(sign.get("ta"))
        if ta:
            valid["TA"] += 1
            if ta[0] < 90 or ta[0] > 140 or ta[1] < 60 or ta[1] > 90:
                anomalies["TA"] += 1
        for label, value, low, high in (
            ("FC", fc, 60, 100), ("FR", fr, 12, 20), ("Temp", temp, 36.1, 37.2)
        ):
            if value is not None:
                valid[label] += 1
                if value < low or value > high:
                    anomalies[label] += 1
        if spo2 is not None:
            valid["SpO2"] += 1
            if spo2 < 95:
                anomalies["SpO2"] += 1
    return {"alerts": dict(anomalies), "valid": dict(valid)}


def _build_role_guidance(data, avg_ticket, outliers, bed_rate, best_month, best_exam):
    """Genera recomendaciones por rol a partir de los resultados actuales."""
    alerts = data["sign_anomalies"]
    main_alert = max(alerts.items(), key=lambda item: item[1], default=None)
    main_area = max(data["area_counts"].items(), key=lambda item: item[1], default=None)
    main_profile = max(data["profile_counts"].items(), key=lambda item: item[1], default=None)

    medico = (
        f"El perfil con mayor demanda es {main_profile[0]} ({main_profile[1]} registros). "
        "Úselo para priorizar la revisión de expedientes y el seguimiento clínico; la gráfica no sustituye la valoración médica."
        if main_profile else
        "Aún no hay estudios suficientes para definir un perfil clínico predominante. Revise la captura de diagnósticos y estudios."
    )
    enfermeria = (
        f"La variable con más registros fuera del rango de referencia es {main_alert[0]} ({main_alert[1]}). "
        "Confirme cada medición y valore al paciente antes de escalarla; un registro fuera de rango no equivale por sí solo a un diagnóstico."
        if main_alert and main_alert[1] > 0 else
        "La muestra reciente no contiene signos fuera de los rangos configurados. Mantenga la vigilancia y verifique que los signos se registren completos."
    )
    estudios = (
        f"El estudio más solicitado es {best_exam[0]} ({best_exam[1]} solicitudes). "
        "Considere su demanda al organizar agenda, equipo, materiales y tiempos de entrega."
        if best_exam else
        "No hay solicitudes suficientes para identificar el estudio de mayor demanda. Verifique nombres y registros de exámenes."
    )
    administrativo = (
        f"El área con mayor volumen es {main_area[0]} ({main_area[1]} atenciones)"
        + (f" y el periodo pico es {best_month['label']} ({best_month['total']})" if best_month else "")
        + ". Use estos datos para distribuir personal, horarios y capacidad de atención."
        if main_area else
        "No hay atenciones suficientes para comparar la carga por área. Revise el registro de área y fecha de ingreso."
    )
    administrador = (
        f"La ocupación registrada es {bed_rate:.1f}% y el ticket promedio de la muestra es {_format_money(avg_ticket)}. "
        f"Se detectaron {outliers} importes atípicos; revise su documentación antes de considerarlos errores."
        if data["total_camas"] or data["subtotals"] else
        "No hay camas o importes suficientes para evaluar capacidad y comportamiento financiero. Revise catálogos y captura de cargos."
    )

    return [
        {"rol": "Médico", "icon": "fa-user-doctor", "enfoque": medico},
        {"rol": "Enfermería", "icon": "fa-heart-pulse", "enfoque": enfermeria},
        {"rol": "Estudios", "icon": "fa-microscope", "enfoque": estudios},
        {"rol": "Administrativo", "icon": "fa-clipboard-list", "enfoque": administrativo},
        {"rol": "Administrador", "icon": "fa-user-gear", "enfoque": administrador},
    ]


def _chart_explanation(what, how, result, action, caution=None):
    return {
        "que_muestra": what,
        "como_leer": how,
        "resultado_actual": result,
        "accion": action,
        "precaucion": caution,
    }


def build_ineo_graphics_context(db, force_refresh=False, filters=None):
    filters = {key: value for key, value in dict(filters or {}).items() if key in FILTER_KEYS}
    has_custom_filters = bool(filters)
    if not force_refresh and not has_custom_filters and _cache_is_valid():
        return _read_cache()

    trend_months = int(_filter_choice(filters, "trend_months", {"3", "6", "12"}, "12"))
    trend_type = _filter_choice(filters, "trend_type", {"line", "bar"}, "line")
    area_type = _filter_choice(filters, "area_type", {"donut", "bar"}, "bar")
    area_top = int(_filter_choice(filters, "area_top", {"3", "4", "7"}, "4"))
    exam_top = int(_filter_choice(filters, "exam_top", {"3", "5", "7"}, "7"))
    exam_order = _filter_choice(filters, "exam_order", {"desc", "asc"}, "desc")
    exam_type = _filter_choice(filters, "exam_type", {"horizontal", "vertical"}, "horizontal")
    profile_top = int(_filter_choice(filters, "profile_top", {"3", "5", "7"}, "7"))
    profile_order = _filter_choice(filters, "profile_order", {"desc", "asc"}, "desc")
    amount_top = int(_filter_choice(filters, "amount_top", {"3", "5", "7"}, "7"))
    amount_order = _filter_choice(filters, "amount_order", {"desc", "asc"}, "desc")
    sign_variable = _filter_choice(filters, "sign_variable", {"all", "TA", "FC", "FR", "Temp", "SpO2"}, "all")
    revenue_top = int(_filter_choice(filters, "revenue_top", {"3", "5", "7"}, "5"))

    data = _load_optimized_data(db)
    month_counts = data["month_counts"][-trend_months:]
    subtotals_all = data["subtotals"]
    subtotals = subtotals_all
    revenue_total = sum(subtotals)
    avg_ticket = mean(subtotals) if subtotals else 0.0
    med_ticket = median(subtotals) if subtotals else 0.0
    q1 = _percentile(sorted(subtotals), 25) if subtotals else 0.0
    q3 = _percentile(sorted(subtotals), 75) if subtotals else 0.0
    iqr = q3 - q1
    outliers = len([value for value in subtotals if value > q3 + 1.5 * iqr]) if subtotals else 0
    bed_rate = data["camas_ocupadas"] / data["total_camas"] * 100 if data["total_camas"] else 0.0
    signs_alerts_total = sum(data["sign_anomalies"].values())

    best_month = max(month_counts, key=lambda row: row["total"], default=None)
    exam_rows = sorted(data["top_exams"], key=lambda item: item[1], reverse=exam_order == "desc")[:exam_top]
    best_exam = max(data["top_exams"], key=lambda item: item[1], default=None)
    ocular_exam_total = sum(value for _, value in data["top_exams"])
    profile_rows = sorted(data["profile_counts"].items(), key=lambda item: item[1], reverse=profile_order == "desc")[:profile_top]
    sign_rows = [(label, data["sign_anomalies"].get(label, 0), data["sign_valid"].get(label, 0)) for label in ["TA", "FC", "FR", "Temp", "SpO2"]]
    if sign_variable != "all":
        sign_rows = [row for row in sign_rows if row[0] == sign_variable]
    revenue_rows = data["revenue_by_type"][:revenue_top]
    service_rows = sorted(
        data["service_amounts"], key=lambda item: item[1], reverse=amount_order == "desc"
    )[:amount_top]

    context = {
        "cache_version": CACHE_VERSION,
        "fecha_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "desde_cache": False,
        "filter_values": {
            "trend_months": str(trend_months), "trend_type": trend_type,
            "area_type": area_type, "area_top": str(area_top),
            "exam_top": str(exam_top), "exam_order": exam_order, "exam_type": exam_type,
            "profile_top": str(profile_top), "profile_order": profile_order,
            "amount_top": str(amount_top), "amount_order": amount_order,
            "sign_variable": sign_variable, "revenue_top": str(revenue_top),
        },
        "metricas": [
            {"label": "Pacientes", "value": f"{data['total_pacientes']:,}", "icon": "fa-users", "tone": "primary"},
            {"label": "Atenciones abiertas", "value": f"{data['open_attentions']:,}", "icon": "fa-hospital-user", "tone": "success"},
            {"label": "Estudios visualizados", "value": f"{ocular_exam_total:,}", "icon": "fa-eye", "tone": "info"},
            {"label": "Pacientes perfil ocular", "value": f"{data['ocular_patients']:,}", "icon": "fa-user-md", "tone": "purple"},
            {"label": "Ocupacion camas", "value": f"{bed_rate:.1f}%", "icon": "fa-bed", "tone": "warning"},
            {"label": "Importe promedio por cargo", "value": _format_money(avg_ticket), "icon": "fa-receipt", "tone": "danger"},
        ],
        "hallazgos": [
            {
                "titulo": "Tendencia temporal",
                "detalle": f"El mayor volumen aparece en {best_month['label']} con {best_month['total']} atenciones."
                if best_month
                else "No hay fechas suficientes para evaluar tendencia mensual.",
                "icon": "fa-chart-line",
            },
            {
                "titulo": "Estudio dominante",
                "detalle": f"{best_exam[0]} concentra {best_exam[1]} solicitudes; conviene revisar agenda e insumos."
                if best_exam
                else "No hay estudios suficientes para detectar la categoria dominante.",
                "icon": "fa-eye",
            },
            {
                "titulo": "Seguimiento de enfermeria",
                "detalle": f"Se detectaron {signs_alerts_total} alertas en una muestra reciente de {data['signs_total_sample']} signos vitales.",
                "icon": "fa-heartbeat",
            },
            {
                "titulo": "Control administrativo",
                "detalle": f"Ingreso en cargos analizados {_format_money(revenue_total)}; {outliers} importes superan el límite superior por IQR."
                if subtotals
                else "No hay importes suficientes para evaluar ingresos y valores atipicos.",
                "icon": "fa-file-invoice-dollar",
            },
        ],
        "presentacion": _build_role_guidance(
            data, avg_ticket, outliers, bed_rate, best_month, best_exam
        ),
        "estadistica": {
            "observaciones": len(subtotals),
            "media": avg_ticket,
            "mediana": med_ticket,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "outliers": outliers,
            "edad_promedio": mean(data["ages"]) if data["ages"] else 0.0,
            "diagnosticos_oculares": data["diagnosticos_oculares"],
        },
        "graficas": [
            {
                "id": "trend",
                "titulo": "Evolución mensual de atenciones",
                "subtitulo": f"Atenciones por mes calendario en los últimos {trend_months} meses; los meses sin registros aparecen en cero.",
                "svg": _line_svg(month_counts, trend_type),
                "filtros": [
                    {"name": "trend_months", "label": "Periodos", "options": [("3", "3 meses"), ("6", "6 meses"), ("12", "12 meses")]},
                    {"name": "trend_type", "label": "Tipo", "options": [("line", "Línea"), ("bar", "Barras")]},
                ],
                "lectura": "Identifica meses pico y compara contra el promedio para anticipar carga operativa.",
                "explicacion": _chart_explanation(
                    f"La cantidad de atenciones registradas en cada uno de los últimos {trend_months} meses calendario.",
                    "El eje horizontal representa los meses y el vertical el número de atenciones. Los puntos altos indican mayor carga; la línea de promedio sirve como referencia.",
                    f"El periodo con más atenciones es {best_month['label']} con {best_month['total']} registros." if best_month else "No existen fechas válidas suficientes para calcular una tendencia.",
                    "Compare los periodos altos con disponibilidad de personal, consultorios y camas para anticipar recursos.",
                    "Un aumento puede deberse a mayor demanda o a una mejora en el registro; debe confirmarse con la operación de la clínica.",
                ),
            },
            {
                "id": "area",
                "titulo": "Distribución de atenciones por área",
                "subtitulo": "Comparación del volumen y participación de cada área de atención.",
                "svg": _donut_svg(data["area_counts"], area_top) if area_type == "donut" else _area_bar_svg(data["area_counts"], area_top),
                "filtros": [
                    {"name": "area_type", "label": "Tipo", "options": [("bar", "Barras (recomendado)"), ("donut", "Dona")]},
                    {"name": "area_top", "label": "Categorías", "options": [("3", "3"), ("4", "4"), ("7", "Hasta 7")]},
                ],
                "lectura": "Las barras facilitan comparar áreas; la dona solo se recomienda cuando se desea enfatizar participación del total.",
                "explicacion": _chart_explanation(
                    "Cómo se distribuyen las atenciones entre las áreas registradas.",
                    "En barras, compare longitudes desde una base común en cero. En dona, compare porcentajes del total sin interpretar el ángulo como precisión exacta.",
                    f"El área con mayor volumen es {max(data['area_counts'], key=data['area_counts'].get)} con {max(data['area_counts'].values())} atenciones." if data["area_counts"] else "No hay áreas registradas para comparar.",
                    "Use la proporción para revisar la asignación de personal, espacios y materiales por área.",
                    "La gráfica muestra volumen, no gravedad clínica ni calidad de la atención.",
                ),
            },
            {
                "id": "exams",
                "titulo": "Estudios oculares más solicitados",
                "subtitulo": f"Ranking de {len(exam_rows)} estudios por cantidad de solicitudes.",
                "svg": _barh_svg(exam_rows) if exam_type == "horizontal" else _bar_svg("Estudios oculares más solicitados", exam_rows, "Cantidad de solicitudes", "Tipo de estudio"),
                "filtros": [
                    {"name": "exam_top", "label": "Mostrar", "options": [("3", "Top 3"), ("5", "Top 5"), ("7", "Top 7")]},
                    {"name": "exam_order", "label": "Orden", "options": [("desc", "Mayor a menor"), ("asc", "Menor a mayor")]},
                    {"name": "exam_type", "label": "Tipo", "options": [("horizontal", "Horizontal"), ("vertical", "Vertical")]},
                ],
                "lectura": "Senala que estudios requieren mas agenda, insumos o personal especializado.",
                "explicacion": _chart_explanation(
                    "Los siete estudios con más solicitudes dentro de los registros analizados.",
                    "La longitud de cada barra corresponde al número de solicitudes; la barra superior representa el estudio más frecuente.",
                    f"{best_exam[0]} ocupa el primer lugar con {best_exam[1]} solicitudes." if best_exam else "No hay estudios suficientes para elaborar la comparación.",
                    "Priorice agenda, mantenimiento de equipo e insumos para los estudios con barras más largas.",
                    "Solo se muestran hasta siete categorías y los nombres dependen de la calidad de captura.",
                ),
            },
            {
                "id": "profiles",
                "titulo": "Perfil de estudios oculares",
                "subtitulo": "Agrupación por retina, glaucoma, córnea, catarata y refracción.",
                "svg": _bar_svg("Perfil de estudios oculares", profile_rows, "Cantidad de registros", "Perfil ocular"),
                "filtros": [
                    {"name": "profile_top", "label": "Mostrar", "options": [("3", "Top 3"), ("5", "Top 5"), ("7", "Hasta 7")]},
                    {"name": "profile_order", "label": "Orden", "options": [("desc", "Mayor a menor"), ("asc", "Menor a mayor")]},
                ],
                "lectura": "Resume la demanda clinica por linea de atencion ocular.",
                "explicacion": _chart_explanation(
                    "La agrupación de estudios por perfiles o líneas de atención ocular.",
                    "Compare la altura de las barras: una barra mayor indica más registros asociados con ese perfil.",
                    f"El perfil predominante es {max(data['profile_counts'], key=data['profile_counts'].get)} con {max(data['profile_counts'].values())} registros." if data["profile_counts"] else "No fue posible formar perfiles con los datos disponibles.",
                    "Apoye la planeación de seguimiento médico y capacidad de estudios con los perfiles de mayor demanda.",
                    "La clasificación se basa en palabras del nombre del estudio y no constituye un diagnóstico del paciente.",
                ),
            },
            {
                "id": "amounts",
                "titulo": "Importe promedio por servicio",
                "subtitulo": f"Comparación directa de {len(service_rows)} servicios; cada etiqueta muestra el promedio y número de cargos.",
                "svg": _service_amount_svg(service_rows),
                "filtros": [
                    {"name": "amount_top", "label": "Mostrar", "options": [("3", "Top 3"), ("5", "Top 5"), ("7", "Top 7")]},
                    {"name": "amount_order", "label": "Orden", "options": [("desc", "Mayor a menor"), ("asc", "Menor a mayor")]},
                ],
                "lectura": "Compara directamente el importe promedio de cada servicio y muestra cuántos cargos forman cada promedio.",
                "explicacion": _chart_explanation(
                    "El importe promedio registrado para cada servicio.",
                    "Una barra más larga representa un importe promedio mayor; n indica cuántos cargos forman el cálculo.",
                    f"El servicio con mayor promedio es {service_rows[0][0]} con {_format_money(service_rows[0][1])}." if service_rows else "No hay servicios válidos para comparar.",
                    "Compare servicios con suficiente número de cargos antes de tomar decisiones.",
                    "El importe promedio no representa utilidad ni pago cobrado.",
                ),
            },
            {
                "id": "signs",
                "titulo": "Alertas de signos vitales",
                "subtitulo": f"Porcentaje fuera de rango entre las mediciones válidas de una muestra reciente de {data['signs_total_sample']} registros.",
                "svg": _sign_alert_rate_svg(sign_rows),
                "filtros": [
                    {"name": "sign_variable", "label": "Variable", "options": [("all", "Todas"), ("TA", "Tensión arterial"), ("FC", "Frecuencia cardiaca"), ("FR", "Frecuencia respiratoria"), ("Temp", "Temperatura"), ("SpO2", "Saturación de oxígeno")]},
                ],
                "lectura": "Compare porcentajes, no conteos crudos: debajo de cada barra aparece el número de alertas y mediciones válidas.",
                "explicacion": _chart_explanation(
                    "Qué porcentaje de las mediciones válidas de TA, FC, FR, temperatura y SpO2 quedó fuera de los rangos de referencia configurados.",
                    "El eje vertical mantiene una escala fija de 0% a 100%. Debajo de cada variable se muestra el numerador y denominador para dar contexto.",
                    f"Se contabilizaron {signs_alerts_total} alertas en una muestra de {data['signs_total_sample']} registros de signos vitales.",
                    "Enfermería debe confirmar la medición, revisar el contexto del paciente y aplicar el protocolo clínico correspondiente.",
                    "Es un apoyo de vigilancia; no diagnostica ni reemplaza el criterio del personal de salud.",
                ),
            },
            {
                "id": "revenue",
                "titulo": "Ingresos registrados por tipo de servicio",
                "subtitulo": f"Comparación de ingreso, participación y número de cargos para {len(revenue_rows)} tipos de servicio.",
                "svg": _revenue_type_svg(revenue_rows),
                "filtros": [
                    {"name": "revenue_top", "label": "Mostrar", "options": [("3", "Top 3"), ("5", "Top 5"), ("7", "Top 7")]},
                ],
                "lectura": "Ordena los tipos por ingreso registrado y muestra también su porcentaje y número de cargos para no confundir volumen con precio.",
                "explicacion": _chart_explanation(
                    "Cuánto ingreso registrado aporta cada tipo de servicio en los cargos analizados.",
                    "La longitud representa pesos acumulados. La etiqueta agrega porcentaje del total mostrado y cantidad de cargos.",
                    f"El tipo con mayor ingreso es {revenue_rows[0][0]} con {_format_money(revenue_rows[0][1])} en {revenue_rows[0][2]} cargos." if revenue_rows else "No hay tipos de servicio válidos para comparar.",
                    "Revise si los tipos con mayor ingreso requieren más capacidad, control de cuentas o conciliación administrativa.",
                    "Ingreso registrado no equivale a pago cobrado ni utilidad. Los cargos sin tipo se agrupan como 'Sin clasificar'.",
                ),
            },
        ],
        "error": None,
    }

    if not has_custom_filters:
        _write_cache(context)
    return context
