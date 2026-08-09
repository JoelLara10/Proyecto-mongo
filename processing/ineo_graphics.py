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

CHART_COLORS = ["#667eea", "#48bb78", "#ed8936", "#f56565", "#9f7aea", "#4299e1", "#14b8a6"]


def empty_context(error=None):
    return {
        "fecha_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "desde_cache": False,
        "metricas": [],
        "graficas": [],
        "hallazgos": [],
        "presentacion": [],
        "estadistica": {},
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
    return CACHE_FILE.exists() and (datetime.now().timestamp() - CACHE_FILE.stat().st_mtime) < CACHE_TTL_SECONDS


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


def _svg_text(text):
    return html.escape(str(text), quote=True)


def _svg_shell(width, height, body):
    return f'<svg class="chart-svg" viewBox="0 0 {width} {height}" role="img" xmlns="http://www.w3.org/2000/svg">{body}</svg>'


def _line_svg(rows):
    width, height = 900, 420
    if not rows:
        return _empty_svg(width, height, "Tendencia de atenciones", "No hay fechas suficientes para graficar.")

    labels = [row["label"] for row in rows]
    values = [float(row["total"]) for row in rows]
    max_value = max(values) or 1
    avg_value = mean(values)
    left, right, top, bottom = 72, 30, 44, 76
    chart_w, chart_h = width - left - right, height - top - bottom
    step = chart_w / max(len(values) - 1, 1)
    points = []

    for index, value in enumerate(values):
        x = left + index * step
        y = top + chart_h - _scale(value, max_value, chart_h)
        points.append((x, y))

    avg_y = top + chart_h - _scale(avg_value, max_value, chart_h)
    max_index = values.index(max_value)
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"{left},{top + chart_h} {polyline} {left + chart_w},{top + chart_h}"
    body = [
        '<rect width="900" height="420" fill="#ffffff"/>',
        '<text x="450" y="25" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">Tendencia mensual de atenciones INEO</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
        f'<polygon points="{area}" fill="#90cdf4" opacity="0.35"/>',
        f'<line x1="{left}" y1="{avg_y:.1f}" x2="{left + chart_w}" y2="{avg_y:.1f}" stroke="#e53e3e" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<text x="{left + chart_w - 4}" y="{avg_y - 6:.1f}" text-anchor="end" font-size="12" fill="#e53e3e">Promedio {avg_value:.1f}</text>',
        f'<polyline points="{polyline}" fill="none" stroke="#667eea" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>',
    ]

    for index, (x, y) in enumerate(points):
        color = "#38a169" if index == max_index else "#667eea"
        radius = 8 if index == max_index else 6
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="#ffffff" stroke="{color}" stroke-width="3"/>')
        body.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#2d3748">{int(values[index])}</text>')
        body.append(f'<text x="{x:.1f}" y="{top + chart_h + 28}" text-anchor="middle" font-size="11" fill="#4a5568" transform="rotate(-28 {x:.1f},{top + chart_h + 28})">{_svg_text(labels[index])}</text>')

    body.append('<text x="18" y="215" transform="rotate(-90 18,215)" font-size="13" font-weight="700" fill="#4a5568">Numero de atenciones</text>')
    body.append('<text x="450" y="405" text-anchor="middle" font-size="11" fill="#718096">Fuente: MongoDB INEO | Escala temporal mensual</text>')
    return _svg_shell(width, height, "".join(body))


def _donut_svg(area_counts):
    width, height = 760, 420
    if not area_counts:
        return _empty_svg(width, height, "Composicion por area", "No hay areas de atencion registradas.")

    ordered = sorted(area_counts.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) > 4:
        ordered = ordered[:3] + [("Otros", sum(value for _, value in ordered[3:]))]

    total = sum(value for _, value in ordered) or 1
    cx, cy, radius = 250, 220, 112
    circumference = 2 * math.pi * radius
    offset = 0
    body = [
        '<rect width="760" height="420" fill="#ffffff"/>',
        '<text x="380" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">Composicion de atenciones por area</text>',
        f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="#edf2f7" stroke-width="58"/>',
    ]

    for index, (label, value) in enumerate(ordered):
        length = value / total * circumference
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="58" '
            f'stroke-dasharray="{length:.2f} {circumference - length:.2f}" stroke-dashoffset="{-offset:.2f}" '
            'transform="rotate(-90 250 220)"/>'
        )
        pct = value / total * 100
        y = 126 + index * 48
        body.append(f'<rect x="440" y="{y - 15}" width="18" height="18" rx="4" fill="{color}"/>')
        body.append(f'<text x="468" y="{y}" font-size="13" font-weight="700" fill="#2d3748">{_svg_text(label)}</text>')
        body.append(f'<text x="468" y="{y + 18}" font-size="12" fill="#718096">{value} atenciones | {pct:.1f}%</text>')
        offset += length

    body.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="28" font-weight="800" fill="#2d3748">{total}</text>')
    body.append(f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="12" fill="#718096">Total</text>')
    body.append('<text x="380" y="405" text-anchor="middle" font-size="11" fill="#718096">Pastel usado solo con pocas categorias para lectura clara</text>')
    return _svg_shell(width, height, "".join(body))


def _barh_svg(rows):
    width, height = 900, 430
    if not rows:
        return _empty_svg(width, height, "Estudios oculares mas frecuentes", "No hay estudios para graficar.")

    rows = list(reversed(rows[:7]))
    max_value = max(value for _, value in rows) or 1
    left, top, bar_h, gap = 260, 64, 28, 20
    chart_w = 560
    avg_value = mean([value for _, value in rows])
    avg_x = left + _scale(avg_value, max_value, chart_w)
    body = [
        '<rect width="900" height="430" fill="#ffffff"/>',
        '<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">Estudios oculares mas frecuentes</text>',
        f'<line x1="{avg_x:.1f}" y1="54" x2="{avg_x:.1f}" y2="372" stroke="#e53e3e" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<text x="{avg_x + 5:.1f}" y="52" font-size="12" fill="#e53e3e">Promedio {avg_value:.1f}</text>',
    ]

    for index, (label, value) in enumerate(rows):
        y = top + index * (bar_h + gap)
        bar_w = _scale(value, max_value, chart_w)
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(f'<text x="245" y="{y + 19}" text-anchor="end" font-size="12" fill="#4a5568">{_svg_text(_safe_label(label, max_len=32))}</text>')
        body.append(f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="{bar_h}" rx="6" fill="{color}"/>')
        body.append(f'<text x="{left + bar_w + 8:.1f}" y="{y + 19}" font-size="12" font-weight="700" fill="#2d3748">{value}</text>')

    body.append('<text x="450" y="410" text-anchor="middle" font-size="11" fill="#718096">Grafica de barras: compara categorias, maximo 7 colores</text>')
    return _svg_shell(width, height, "".join(body))


def _bar_svg(title, rows, y_label):
    width, height = 840, 420
    if not rows:
        return _empty_svg(width, height, title, "No hay datos suficientes.")

    max_value = max(value for _, value in rows) or 1
    left, top, bottom = 70, 58, 78
    chart_w, chart_h = width - left - 36, height - top - bottom
    slot = chart_w / len(rows)
    bar_w = min(62, slot * 0.62)
    body = [
        '<rect width="840" height="420" fill="#ffffff"/>',
        f'<text x="420" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">{_svg_text(title)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
    ]

    for index, (label, value) in enumerate(rows):
        x = left + index * slot + (slot - bar_w) / 2
        h = _scale(value, max_value, chart_h)
        y = top + chart_h - h
        color = CHART_COLORS[index % len(CHART_COLORS)]
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="6" fill="{color}"/>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#2d3748">{value}</text>')
        body.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + chart_h + 28}" text-anchor="middle" font-size="11" fill="#4a5568">{_svg_text(_safe_label(label, max_len=16))}</text>')

    body.append(f'<text x="18" y="215" transform="rotate(-90 18,215)" font-size="13" font-weight="700" fill="#4a5568">{_svg_text(y_label)}</text>')
    body.append('<text x="420" y="405" text-anchor="middle" font-size="11" fill="#718096">Colores separados por categoria y etiquetas directas</text>')
    return _svg_shell(width, height, "".join(body))


def _histogram_box_svg(amounts):
    width, height = 900, 440
    clean = sorted(value for value in amounts if value > 0)
    if len(clean) < 3:
        return _empty_svg(width, height, "Distribucion de importes por servicio", "Se necesitan al menos 3 importes.")

    min_value, max_value = clean[0], clean[-1]
    if min_value == max_value:
        max_value = min_value + 1

    bins_count = min(10, max(5, int(math.sqrt(len(clean)))))
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
    slot = chart_w / bins_count
    box_y = 335

    def x_for(value):
        return left + (value - min_value) / (max_value - min_value) * chart_w

    body = [
        '<rect width="900" height="440" fill="#ffffff"/>',
        '<text x="450" y="28" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">Distribucion de importes por servicio</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#cbd5e1"/>',
    ]

    for index, count in enumerate(bins):
        h = _scale(count, max_bin, chart_h)
        x = left + index * slot + 4
        y = top + chart_h - h
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{slot - 8:.1f}" height="{h:.1f}" rx="5" fill="#4299e1" opacity="0.78"/>')

    for value, color, label in ((avg, "#e53e3e", "Media"), (med, "#38a169", "Mediana")):
        x = x_for(value)
        body.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + chart_h}" stroke="{color}" stroke-width="2" stroke-dasharray="6 4"/>')
        body.append(f'<text x="{x + 4:.1f}" y="{top + 14}" font-size="11" fill="{color}">{label}</text>')

    q1_x, q3_x, med_x = x_for(q1), x_for(q3), x_for(med)
    body.append(f'<line x1="{left}" y1="{box_y}" x2="{left + chart_w}" y2="{box_y}" stroke="#a0aec0" stroke-width="2"/>')
    body.append(f'<rect x="{q1_x:.1f}" y="{box_y - 24}" width="{max(q3_x - q1_x, 3):.1f}" height="48" rx="6" fill="#c6f6d5" stroke="#2f855a" stroke-width="2"/>')
    body.append(f'<line x1="{med_x:.1f}" y1="{box_y - 28}" x2="{med_x:.1f}" y2="{box_y + 28}" stroke="#22543d" stroke-width="3"/>')
    body.append(f'<text x="{left}" y="393" font-size="12" fill="#4a5568">Q1 ${q1:,.0f} | Mediana ${med:,.0f} | Q3 ${q3:,.0f} | Outliers {len(outliers)}</text>')
    body.append('<text x="450" y="424" text-anchor="middle" font-size="11" fill="#718096">Histograma + caja: media, mediana, cuartiles e IQR</text>')
    return _svg_shell(width, height, "".join(body))


def _heatmap_svg(matrix):
    width, height = 600, 430
    labels = ["Cantidad", "Precio", "Subtotal"]
    if not matrix:
        return _empty_svg(width, height, "Relacion financiera", "No hay cargos suficientes para correlacion.")

    cell, start_x, start_y = 82, 150, 82
    body = [
        '<rect width="600" height="430" fill="#ffffff"/>',
        '<text x="300" y="30" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">Relacion cantidad, precio y subtotal</text>',
    ]

    for index, label in enumerate(labels):
        body.append(f'<text x="{start_x + index * cell + cell / 2}" y="68" text-anchor="middle" font-size="12" font-weight="700" fill="#4a5568">{label}</text>')
        body.append(f'<text x="138" y="{start_y + index * cell + cell / 2 + 5}" text-anchor="end" font-size="12" font-weight="700" fill="#4a5568">{label}</text>')

    for row in range(3):
        for col in range(3):
            value = matrix[row][col]
            color = _corr_color(value)
            x = start_x + col * cell
            y = start_y + row * cell
            body.append(f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="8" fill="{color}"/>')
            body.append(f'<text x="{x + cell / 2}" y="{y + cell / 2 + 5}" text-anchor="middle" font-size="16" font-weight="800" fill="#ffffff">{value:.2f}</text>')

    body.append('<text x="300" y="392" text-anchor="middle" font-size="11" fill="#718096">Mapa de calor: correlacion no implica causalidad</text>')
    return _svg_shell(width, height, "".join(body))


def _empty_svg(width, height, title, message):
    return _svg_shell(
        width,
        height,
        (
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
            f'<text x="{width / 2}" y="42" text-anchor="middle" font-size="20" font-weight="800" fill="#2d3748">{_svg_text(title)}</text>'
            f'<text x="{width / 2}" y="{height / 2}" text-anchor="middle" font-size="14" fill="#718096">{_svg_text(message)}</text>'
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


def _corr_color(value):
    value = max(-1, min(1, value))
    if value >= 0:
        r = int(102 - value * 54)
        g = int(126 + value * 64)
        b = int(234 - value * 112)
    else:
        r = int(102 + abs(value) * 143)
        g = int(126 - abs(value) * 61)
        b = int(234 - abs(value) * 104)
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
    )[-12:]
    month_counts = [{"label": _month_label(row["_id"]), "total": int(row["total"])} for row in month_rows]

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
        {"subtotal": 1, "cantidad": 1, "precio": 1},
        limit=MAX_SAMPLE,
    )
    if not financial_records:
        financial_records = _find_list(
            db["examenes_det"],
            {"subtotal": {"$gt": 0}},
            {"subtotal": 1, "cantidad": 1, "precio": 1},
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
    sign_anomalies = _count_sign_anomalies(signs)

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
        "sign_anomalies": sign_anomalies,
        "ages": ages,
        "diagnosticos_oculares": diagnosticos_oculares,
    }


def _count_sign_anomalies(signs):
    anomalies = defaultdict(int)
    for sign in signs:
        fc = _to_float(sign.get("fc"), None)
        fr = _to_float(sign.get("fr"), None)
        temp = _to_float(sign.get("temp"), None)
        spo2 = _to_float(sign.get("spo2"), None)
        ta = _parse_ta(sign.get("ta"))
        if ta and (ta[0] < 90 or ta[0] > 140 or ta[1] < 60 or ta[1] > 90):
            anomalies["TA"] += 1
        if fc is not None and (fc < 60 or fc > 100):
            anomalies["FC"] += 1
        if fr is not None and (fr < 12 or fr > 20):
            anomalies["FR"] += 1
        if temp is not None and (temp < 36.1 or temp > 37.2):
            anomalies["Temp"] += 1
        if spo2 is not None and spo2 < 95:
            anomalies["SpO2"] += 1
    return dict(anomalies)


def build_ineo_graphics_context(db, force_refresh=False):
    if not force_refresh and _cache_is_valid():
        return _read_cache()

    data = _load_optimized_data(db)
    subtotals = data["subtotals"]
    revenue_total = sum(subtotals)
    avg_ticket = mean(subtotals) if subtotals else 0.0
    med_ticket = median(subtotals) if subtotals else 0.0
    q1 = _percentile(sorted(subtotals), 25) if subtotals else 0.0
    q3 = _percentile(sorted(subtotals), 75) if subtotals else 0.0
    iqr = q3 - q1
    outliers = len([value for value in subtotals if value > q3 + 1.5 * iqr]) if subtotals else 0
    bed_rate = data["camas_ocupadas"] / data["total_camas"] * 100 if data["total_camas"] else 0.0
    signs_alerts_total = sum(data["sign_anomalies"].values())

    best_month = max(data["month_counts"], key=lambda row: row["total"], default=None)
    best_exam = data["top_exams"][0] if data["top_exams"] else None
    ocular_exam_total = sum(value for _, value in data["top_exams"])
    profile_rows = list(data["profile_counts"].items())
    sign_rows = [(label, data["sign_anomalies"].get(label, 0)) for label in ["TA", "FC", "FR", "Temp", "SpO2"]]

    context = {
        "fecha_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "desde_cache": False,
        "metricas": [
            {"label": "Pacientes", "value": f"{data['total_pacientes']:,}", "icon": "fa-users", "tone": "primary"},
            {"label": "Atenciones abiertas", "value": f"{data['open_attentions']:,}", "icon": "fa-hospital-user", "tone": "success"},
            {"label": "Estudios visualizados", "value": f"{ocular_exam_total:,}", "icon": "fa-eye", "tone": "info"},
            {"label": "Pacientes perfil ocular", "value": f"{data['ocular_patients']:,}", "icon": "fa-user-md", "tone": "purple"},
            {"label": "Ocupacion camas", "value": f"{bed_rate:.1f}%", "icon": "fa-bed", "tone": "warning"},
            {"label": "Ticket promedio", "value": _format_money(avg_ticket), "icon": "fa-receipt", "tone": "danger"},
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
                "detalle": f"Ingreso muestreado {revenue_total:,.2f}; {outliers} servicios superan el limite superior por IQR."
                if subtotals
                else "No hay importes suficientes para evaluar ingresos y valores atipicos.",
                "icon": "fa-file-invoice-dollar",
            },
        ],
        "presentacion": [
            {"rol": "Medicos", "enfoque": "Priorizar perfiles oculares frecuentes, estudios dominantes y seguimiento oportuno."},
            {"rol": "Enfermeria", "enfoque": "Vigilar signos fuera de rango y ocupacion para reaccionar antes de saturacion."},
            {"rol": "Administrativos", "enfoque": "Revisar volumen mensual, ticket promedio, outliers de cobro y carga por area."},
        ],
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
                "titulo": "Linea: evolucion mensual",
                "subtitulo": "Tendencia de atenciones por periodo con promedio y maximo.",
                "svg": _line_svg(data["month_counts"]),
                "lectura": "Identifica meses pico y compara contra el promedio para anticipar carga operativa.",
            },
            {
                "titulo": "Pastel: composicion por area",
                "subtitulo": "Composicion porcentual con pocas categorias.",
                "svg": _donut_svg(data["area_counts"]),
                "lectura": "Ayuda a ver la proporcion de consulta, urgencias u hospitalizacion dentro del total.",
            },
            {
                "titulo": "Barras: top estudios",
                "subtitulo": "Comparacion de categorias, limitada a 7 para evitar exceso de color.",
                "svg": _barh_svg(data["top_exams"]),
                "lectura": "Senala que estudios requieren mas agenda, insumos o personal especializado.",
            },
            {
                "titulo": "Barras: perfil ocular",
                "subtitulo": "Agrupa estudios por retina, glaucoma, cornea, catarata y refraccion.",
                "svg": _bar_svg("Perfil de estudios oculares", profile_rows, "Cantidad"),
                "lectura": "Resume la demanda clinica por linea de atencion ocular.",
            },
            {
                "titulo": "Histograma y caja: importes",
                "subtitulo": "Distribucion, media, mediana, cuartiles y outliers por IQR.",
                "svg": _histogram_box_svg(subtotals),
                "lectura": "Permite detectar cargos atipicos y explicar variacion del gasto por servicio.",
            },
            {
                "titulo": "Barras: alertas de signos",
                "subtitulo": "Conteo de variables fuera de rangos clinicos de referencia.",
                "svg": _bar_svg("Registros fuera de rango en signos vitales", sign_rows, "Alertas"),
                "lectura": "Orienta revisiones de enfermeria y monitoreo de pacientes con datos anormales.",
            },
            {
                "titulo": "Mapa de calor: relacion financiera",
                "subtitulo": "Correlacion entre cantidad, precio y subtotal.",
                "svg": _heatmap_svg(_correlation_matrix(data["financial_records"])),
                "lectura": "Evita asumir causalidad: una correlacion alta solo indica relacion estadistica.",
            },
        ],
        "error": None,
    }

    _write_cache(context)
    return context
