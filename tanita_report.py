"""Build a readable Tanita body composition report.

The script reads one Tanita CSV file. It writes a PDF. It can also write a
self-contained HTML file. It does not use Jupyter.

Example:
    python tanita_report.py DATA1.CSV
    python tanita_report.py DATA1.CSV -o report.pdf --html report.html
"""

import argparse
import html
import io
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.ticker import MaxNLocator

import tanita_parser

A4 = (8.27, 11.69)

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
CHROME = "#f0efec"

FAT = "#eb6834"
MUSCLE = "#2a78d6"
MARKER = "#6250d6"

FAT_CMAP = LinearSegmentedColormap.from_list(
    "fat",
    ["#fbe6dc", "#f6c3ad", "#ef9a73", "#eb6834", "#c94a1c", "#8f3313"],
)
MUSCLE_CMAP = LinearSegmentedColormap.from_list(
    "muscle",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)

FAT_NORM = Normalize(vmin=15, vmax=30)
MUSCLE_NORM = Normalize(vmin=0, vmax=35)

# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

GROUP_ORDER = ["general", "fat", "muscle", "markers"]

GROUPS = {
    "general": {"pt": "Dados gerais", "en": "General"},
    "fat": {"pt": "Gordura", "en": "Fat"},
    "muscle": {"pt": "Músculo", "en": "Muscle"},
    "markers": {"pt": "Marcadores", "en": "Markers"},
}

MEASUREMENTS = [
    {
        "key": "datetime",
        "group": "general",
        "dec": None,
        "pt": "Data e hora",
        "en": "Date and time",
        "unit_pt": "",
        "unit_en": "",
    },
    {
        "key": "AG",
        "group": "general",
        "dec": 0,
        "pt": "Idade",
        "en": "Age",
        "unit_pt": "anos",
        "unit_en": "years",
    },
    {
        "key": "Hm",
        "group": "general",
        "dec": 0,
        "pt": "Altura",
        "en": "Height",
        "unit_pt": "cm",
        "unit_en": "cm",
    },
    {
        "key": "Wk",
        "group": "general",
        "dec": 1,
        "pt": "Massa corporal",
        "en": "Body mass",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "MI",
        "group": "general",
        "dec": 1,
        "pt": "IMC",
        "en": "BMI",
        "unit_pt": "kg/m²",
        "unit_en": "kg/m²",
    },
    {
        "key": "FW",
        "group": "fat",
        "dec": 1,
        "pt": "Gordura total",
        "en": "Total fat",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "Fr",
        "group": "fat",
        "dec": 1,
        "pt": "Braço direito",
        "en": "Right arm",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "Fl",
        "group": "fat",
        "dec": 1,
        "pt": "Braço esquerdo",
        "en": "Left arm",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "FR",
        "group": "fat",
        "dec": 1,
        "pt": "Perna direita",
        "en": "Right leg",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "FL",
        "group": "fat",
        "dec": 1,
        "pt": "Perna esquerda",
        "en": "Left leg",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "FT",
        "group": "fat",
        "dec": 1,
        "pt": "Tronco",
        "en": "Torso",
        "unit_pt": "%",
        "unit_en": "%",
    },
    {
        "key": "mW",
        "group": "muscle",
        "dec": 1,
        "pt": "Músculo total",
        "en": "Total muscle",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "mr",
        "group": "muscle",
        "dec": 1,
        "pt": "Braço direito",
        "en": "Right arm",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "ml",
        "group": "muscle",
        "dec": 1,
        "pt": "Braço esquerdo",
        "en": "Left arm",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "mR",
        "group": "muscle",
        "dec": 1,
        "pt": "Perna direita",
        "en": "Right leg",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "mL",
        "group": "muscle",
        "dec": 1,
        "pt": "Perna esquerda",
        "en": "Left leg",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "mT",
        "group": "muscle",
        "dec": 1,
        "pt": "Tronco",
        "en": "Torso",
        "unit_pt": "kg",
        "unit_en": "kg",
    },
    {
        "key": "IF",
        "group": "markers",
        "dec": 0,
        "pt": "Gordura visceral",
        "en": "Visceral fat",
        "unit_pt": "nível",
        "unit_en": "level",
    },
    {
        "key": "rD",
        "group": "markers",
        "dec": 0,
        "pt": "Calorias diárias",
        "en": "Daily calories",
        "unit_pt": "kcal",
        "unit_en": "kcal",
    },
    {
        "key": "rA",
        "group": "markers",
        "dec": 0,
        "pt": "Idade metabólica",
        "en": "Metabolic age",
        "unit_pt": "anos",
        "unit_en": "years",
    },
    {
        "key": "ww",
        "group": "markers",
        "dec": 1,
        "pt": "Água corporal total",
        "en": "Total body water",
        "unit_pt": "%",
        "unit_en": "%",
    },
]

ENTRY_BY_KEY = {entry["key"]: entry for entry in MEASUREMENTS}

FAT_KEYS = ["FW", "Fr", "Fl", "FR", "FL", "FT"]
MUSCLE_KEYS = ["mW", "mr", "ml", "mR", "mL", "mT"]

# Each muscle segment uses the same body area as one fat segment.
MUSCLE_TO_FAT = {"mr": "Fr", "ml": "Fl", "mR": "FR", "mL": "FL", "mT": "FT"}
TILE_KEYS = ["Wk", "MI", "FW", "mW"]

TEXT = {
    "pt": {
        "title": "Relatório de composição corporal",
        "page_body": "Distribuição por segmento",
        "page_evolution": "Evolução",
        "page_markers": "Músculo e marcadores",
        "sub_evolution": "Massa corporal, IMC e gordura",
        "sub_markers": "Músculo por segmento e marcadores",
        "indicator": "Indicador",
        "table_title": "Últimas medições",
        "unit": "Un.",
        "latest": "Atual",
        "previous": "Anterior",
        "earlier": "Antes",
        "vs_previous": "vs. medição anterior",
        "reference": "Linha cinza: total da medição.",
        "measured_on": "Medição de",
        "fat_segments": "Gordura por segmento (%)",
        "muscle_segments": "Músculo por segmento (kg)",
        "markers": "Marcadores",
        "mass": "Massa corporal",
        "bmi": "IMC",
        "total_fat": "Gordura total",
        "total_muscle": "Músculo total",
        "metabolic_age": "Metabólica",
        "real_age": "Idade real",
        "visceral": "Gordura visceral",
        "calories": "Calorias diárias",
        "water": "Água corporal total",
        "total_value": "Total",
        "fat_panel": "Gordura (%)",
        "muscle_panel": "Músculo (kg)",
        "not_measured": "Cabeça e pescoço não medidos.",
        "front_view": "Vista frontal: o lado direito do corpo aparece à esquerda.",
        "note": "Faixas de referência genéricas. Este relatório não é avaliação médica.",
        "generated": "Gerado em",
        "bmi_band": "18,5–25,0",
        "fat_band": "8–20 %",
        "water_band": "50–65 %",
        "limit": "limite 12",
        "x_axis": "Data",
        "y_level": "Nível",
        "y_years": "Anos",
        "file_written": "Arquivo gravado:",
        "count_measurements": "medições",
        "count_days": "dias com medição",
    },
    "en": {
        "title": "Body composition report",
        "page_body": "Segment distribution",
        "page_evolution": "Trends",
        "page_markers": "Muscle and markers",
        "sub_evolution": "Body mass, BMI and fat",
        "sub_markers": "Muscle by segment and markers",
        "indicator": "Indicator",
        "table_title": "Latest measurements",
        "unit": "Unit",
        "latest": "Latest",
        "previous": "Previous",
        "earlier": "Earlier",
        "vs_previous": "vs. previous measurement",
        "reference": "Grey line: total of the same measurement.",
        "measured_on": "Measurement of",
        "fat_segments": "Fat by segment (%)",
        "muscle_segments": "Muscle by segment (kg)",
        "markers": "Markers",
        "mass": "Body mass",
        "bmi": "BMI",
        "total_fat": "Total fat",
        "total_muscle": "Total muscle",
        "metabolic_age": "Metabolic",
        "real_age": "Real age",
        "visceral": "Visceral fat",
        "calories": "Daily calories",
        "water": "Total body water",
        "total_value": "Total",
        "fat_panel": "Fat (%)",
        "muscle_panel": "Muscle (kg)",
        "not_measured": "Head and neck were not measured.",
        "front_view": "Front view: the right side of the body is on the left.",
        "note": "General reference ranges. This report is not a medical assessment.",
        "generated": "Generated on",
        "bmi_band": "18.5–25.0",
        "fat_band": "8–20%",
        "water_band": "50–65%",
        "limit": "limit 12",
        "x_axis": "Date",
        "y_level": "Level",
        "y_years": "Years",
        "file_written": "File written:",
        "count_measurements": "measurements",
        "count_days": "days with a measurement",
    },
}

# Body polygons in normalised units. x is 0 to 1. y is 0 to 2.2.
# The viewer sees the front of the body. The right side is on the left.
BODY_POLYGONS = {
    "FR": [(0.402, 1.07), (0.495, 1.07), (0.492, 0.03), (0.440, 0.03)],
    "FL": [(0.598, 1.07), (0.505, 1.07), (0.508, 0.03), (0.560, 0.03)],
    "Fr": [(0.398, 1.80), (0.330, 1.80), (0.285, 1.22), (0.345, 1.19)],
    "Fl": [(0.602, 1.80), (0.670, 1.80), (0.715, 1.22), (0.655, 1.19)],
    "FT": [
        (0.400, 1.82),
        (0.440, 1.25),
        (0.400, 1.045),
        (0.600, 1.045),
        (0.560, 1.25),
        (0.600, 1.82),
    ],
}

BODY_LABELS = {
    "Fr": {"xy": (0.328, 1.48), "rotation": 90},
    "Fl": {"xy": (0.672, 1.48), "rotation": 90},
    "FR": {"xy": (0.448, 0.55), "rotation": 90},
    "FL": {"xy": (0.552, 0.55), "rotation": 90},
    "FT": {"xy": (0.500, 1.42), "rotation": 0},
}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def entry_for(key):
    return ENTRY_BY_KEY[key]


def unit_of(entry, lang):
    return entry["unit_pt"] if lang == "pt" else entry["unit_en"]


def label_of(entry, lang):
    return entry["pt"] if lang == "pt" else entry["en"]


def format_value(entry, value):
    if value is None:
        return "—"
    if entry["key"] == "datetime":
        return value.strftime("%d/%m/%Y\n%H:%M")
    decimals = entry["dec"]
    if decimals == 0:
        return f"{value:.0f}"
    return f"{value:.1f}"


def value_at(data, key, index):
    if index is None:
        return None
    values = data.get(key)
    if values is None or index >= len(values):
        return None
    return values[index]


def get_values(data, key, rows):
    values = data.get(key, [])
    result = []
    for index in rows:
        value = values[index] if index < len(values) else None
        result.append(float("nan") if value is None else value)
    return result


def get_datetimes(data, rows):
    values = data.get("datetime", [])
    return [values[index] for index in rows]


def all_rows(data, daily=True):
    dates = data.get("datetime", [])
    indices = list(range(len(dates)))
    if daily:
        last_by_day = {}
        for index in indices:
            day = dates[index].date()
            if day not in last_by_day or dates[index] > dates[last_by_day[day]]:
                last_by_day[day] = index
        indices = sorted(last_by_day.values())
    return indices


def recent_rows(data, count=3, daily=True):
    return all_rows(data, daily)[-count:]


def last_valid(values):
    for value in reversed(values):
        if value is not None and not math.isnan(value):
            return value
    return None


def padded_limits(values, pad=0.08):
    clean = [value for value in values if value is not None and not math.isnan(value)]
    if not clean:
        return 0.0, 1.0
    low, high = min(clean), max(clean)
    margin = (high - low) * pad
    if margin == 0:
        margin = 1.0
    return low - margin, high + margin


def date_limits(dates):
    span = dates[-1] - dates[0]
    pad = max(span * 0.02, timedelta(days=10))
    return dates[0] - pad, dates[-1] + span * 0.10


# ---------------------------------------------------------------------------
# Page furniture
# ---------------------------------------------------------------------------


def page_header(fig, title, subtitle):
    fig.text(
        0.06,
        0.965,
        title,
        fontsize=16,
        fontweight="bold",
        color=INK,
        ha="left",
        va="top",
    )
    fig.text(0.06, 0.936, subtitle, fontsize=8.5, color=INK_2, ha="left", va="top")
    fig.add_artist(
        Line2D(
            [0.06, 0.94],
            [0.918, 0.918],
            color=GRID,
            linewidth=0.8,
            transform=fig.transFigure,
        )
    )


def page_footer(fig, page, pages, lang, generated=None):
    if generated is None:
        generated = datetime.now()
    stamp = generated.strftime("%d/%m/%Y %H:%M")
    fig.text(
        0.06,
        0.025,
        f"{TEXT[lang]['generated']} {stamp}",
        fontsize=7,
        color=MUTED,
        ha="left",
        va="center",
    )
    fig.text(
        0.94,
        0.025,
        f"{page} / {pages}",
        fontsize=7,
        color=MUTED,
        ha="right",
        va="center",
    )


def section_title(fig, y, text):
    fig.text(
        0.075,
        y,
        text,
        fontsize=10.5,
        fontweight="bold",
        color=INK,
        ha="left",
        va="center",
    )


def reference_legend(fig, y, text):
    fig.add_artist(
        Line2D(
            [0.74, 0.765],
            [y, y],
            color=AXIS,
            linewidth=1.0,
            transform=fig.transFigure,
        )
    )
    fig.text(0.775, y, text, fontsize=7, color=MUTED, ha="left", va="center")


def subtitle_for(data, rows, lang):
    dates = data.get("datetime", [])
    if not dates:
        return ""
    days = len({value.date() for value in dates})
    first, last = dates[0], dates[-1]
    count = len(dates)
    return (
        f"Tanita {data.get('MO', ['-'])[0]} · {count} {TEXT[lang]['count_measurements']}"
        f" · {days} {TEXT[lang]['count_days']}"
        f" · {first.strftime('%d/%m/%Y')} – {last.strftime('%d/%m/%Y')}"
    )


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


def tile_data(data, rows, lang):
    latest = rows[-1] if rows else None
    previous = rows[-2] if len(rows) > 1 else None
    tiles = []
    for key in TILE_KEYS:
        entry = entry_for(key)
        current = value_at(data, key, latest)
        before = value_at(data, key, previous)
        text = "—" if current is None else format_value(entry, current)
        unit = unit_of(entry, lang)
        delta = "—"
        if current is not None and before is not None:
            difference = current - before
            sign = "+" if difference > 0 else ("−" if difference < 0 else "±")
            decimals = entry["dec"] or 0
            delta = f"{sign}{abs(difference):.{decimals}f}"
        label = label_of(entry, lang)
        tiles.append(
            {
                "label": f"{label} ({unit})" if unit else label,
                "value": text,
                "unit": unit,
                "delta": delta,
            }
        )
    return tiles


def build_table(data, rows, lang):
    text = TEXT[lang]
    recent = list(reversed(rows))
    while len(recent) < 3:
        recent.append(None)
    recent = recent[:3]

    headers = [text["indicator"], text["unit"]]
    for index, name in zip(recent, ("latest", "previous", "earlier")):
        date = data["datetime"][index].strftime("%d/%m/%Y") if index is not None else "—"
        headers.append(f"{text[name]}\n{date}")

    table = [{"kind": "head", "cells": headers}]
    for group in GROUP_ORDER:
        table.append({"kind": "group", "label": GROUPS[group][lang]})
        for entry in MEASUREMENTS:
            if entry["group"] != group:
                continue
            values = [value_at(data, entry["key"], index) for index in recent]
            table.append(
                {
                    "kind": "row",
                    "label": label_of(entry, lang),
                    "unit": unit_of(entry, lang),
                    "values": values,
                    "entry": entry,
                }
            )
    return table


def draw_table(fig, box, table, lang):
    text = TEXT[lang]
    heights = []
    for row in table:
        if row["kind"] == "head":
            heights.append(1.5)
        elif row["kind"] == "group":
            heights.append(1.0)
        else:
            heights.append(1.0)

    ax = fig.add_axes(box)
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, sum(heights))

    x_label = 0.0
    x_unit = 0.47
    value_edges = [0.74, 0.875, 1.0]

    y = sum(heights)
    for row, height in zip(table, heights):
        y -= height
        middle = y + height / 2
        if row["kind"] == "head":
            ax.add_patch(Rectangle((0, y), 1, height, color=CHROME, linewidth=0))
            ax.text(
                x_label,
                middle,
                row["cells"][0],
                fontsize=7.4,
                fontweight="bold",
                color=INK_2,
                va="center",
                ha="left",
            )
            ax.text(
                x_unit,
                middle,
                row["cells"][1],
                fontsize=7.4,
                fontweight="bold",
                color=INK_2,
                va="center",
                ha="left",
            )
            for right, cell in zip(value_edges, row["cells"][2:]):
                ax.text(
                    right,
                    middle,
                    cell,
                    fontsize=7.4,
                    fontweight="bold",
                    color=INK_2,
                    va="center",
                    ha="right",
                    linespacing=1.25,
                )
        elif row["kind"] == "group":
            ax.add_patch(Rectangle((0, y), 1, height, color=CHROME, linewidth=0))
            ax.text(
                x_label,
                middle,
                row["label"].upper(),
                fontsize=7.2,
                fontweight="bold",
                color=INK_2,
                va="center",
                ha="left",
            )
        else:
            ax.text(
                x_label,
                middle,
                row["label"],
                fontsize=9,
                color=INK,
                va="center",
                ha="left",
            )
            ax.text(
                x_unit,
                middle,
                row["unit"],
                fontsize=8,
                color=MUTED,
                va="center",
                ha="left",
            )
            for column, (right, value) in enumerate(zip(value_edges, row["values"])):
                ax.text(
                    right,
                    middle,
                    format_value(row["entry"], value),
                    fontsize=9,
                    color=INK,
                    fontweight="bold" if column == 0 else "normal",
                    va="center",
                    ha="right",
                    linespacing=1.2,
                )
            ax.axhline(y, color=GRID, linewidth=0.6, xmin=0, xmax=1)


def draw_tiles(fig, tiles):
    width = 0.88 / len(tiles)
    for index, tile in enumerate(tiles):
        x = 0.06 + index * width
        fig.text(x, 0.876, tile["label"], fontsize=7.8, color=MUTED, va="center")
        fig.text(
            x,
            0.852,
            tile["value"],
            fontsize=19,
            fontweight="bold",
            color=INK,
            va="top",
        )
        fig.text(x, 0.806, tile["delta"], fontsize=7.8, color=INK_2, va="center")
        if index:
            fig.add_artist(
                Line2D(
                    [x - 0.018, x - 0.018],
                    [0.80, 0.888],
                    color=GRID,
                    linewidth=0.7,
                    transform=fig.transFigure,
                )
            )


def page_table(data, rows, lang, page, pages, generated=None):
    fig = plt.figure(figsize=A4, facecolor=SURFACE)
    text = TEXT[lang]
    page_header(fig, text["title"], subtitle_for(data, rows, lang))
    draw_tiles(fig, tile_data(data, rows, lang))
    table = build_table(data, rows, lang)
    draw_table(fig, [0.06, 0.04, 0.88, 0.745], table, lang)
    page_footer(fig, page, pages, lang, generated)
    return fig, table


# ---------------------------------------------------------------------------
# Trend charts
# ---------------------------------------------------------------------------


def style_panel(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(length=0, labelsize=7.5, colors=MUTED)


def style_dates(ax, limits, show_labels=True, dense=True, short=False):
    ax.set_xlim(*limits)
    if dense:

        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y" if short or not dense else "%m/%Y"))
    if not show_labels:
        ax.tick_params(labelbottom=False)


def axis_titles(ax, x_text, y_text, size=7):
    ax.set_xlabel(x_text, fontsize=size, color=MUTED, labelpad=2)
    ax.set_ylabel(y_text, fontsize=size, color=MUTED, labelpad=2)


def plot_series(ax, dates, values, colour, width=1.4):
    ax.plot(
        dates,
        values,
        color=colour,
        linewidth=width,
        marker="o",
        markersize=3.4,
        markerfacecolor=SURFACE,
        markeredgecolor=colour,
        markeredgewidth=0.9,
        zorder=3,
    )


def band_label(ax, y, label, va="top"):
    # The x position uses axes coordinates. The y position uses data values.
    ax.text(
        0.99,
        y,
        label,
        transform=ax.get_yaxis_transform(),
        ha="right",
        va=va,
        fontsize=6.8,
        color=MUTED,
    )


def small_multiples(
    fig,
    area,
    entries,
    data,
    rows,
    colour,
    reference,
    lang,
    shared=True,
    band=None,
    band_text=None,
    y_label=None,
):
    gs = fig.add_gridspec(
        2,
        3,
        left=area["left"],
        right=area["right"],
        top=area["top"],
        bottom=area["bottom"],
        wspace=0.38,
        hspace=0.78,
    )
    dates = get_datetimes(data, rows)
    limits = date_limits(dates)

    if shared:
        pool = []
        for entry in entries:
            pool.extend(get_values(data, entry["key"], rows))
        segment_limits = padded_limits(pool, 0.12)
        total_limits = segment_limits
    else:
        pool = []
        for entry in entries[1:]:
            pool.extend(get_values(data, entry["key"], rows))
        segment_limits = padded_limits(pool, 0.12)
        total_limits = padded_limits(get_values(data, entries[0]["key"], rows), 0.12)

    for index, entry in enumerate(entries):
        ax = fig.add_subplot(gs[index // 3, index % 3])
        values = get_values(data, entry["key"], rows)
        low, high = total_limits if index == 0 else segment_limits
        if band is not None:
            ax.axhspan(band[0], band[1], color=GRID, linewidth=0, zorder=1)
            if index == 0 and band_text:
                band_label(ax, band[1] - 0.4, band_text)
        if reference is not None and entry["key"] != reference["key"]:
            ax.plot(
                dates,
                get_values(data, reference["key"], rows),
                color=AXIS,
                linewidth=1.0,
                zorder=2,
            )
        width = 1.8 if reference is not None and entry["key"] == reference["key"] else 1.3
        plot_series(ax, dates, values, colour, width=width)
        ax.set_ylim(low, high)
        style_panel(ax)
        style_dates(ax, limits, show_labels=True, dense=False)
        axis_titles(ax, TEXT[lang]["x_axis"], y_label or "", size=6.8)
        ax.set_title(label_of(entry, lang), loc="left", fontsize=8.5, color=INK_2, pad=3)
        latest = last_valid(values)
        if latest is not None:
            ax.text(
                1.0,
                1.04,
                format_value(entry, latest),
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color=INK,
            )


def page_trends(data, rows, lang, page, pages, generated=None):
    fig = plt.figure(figsize=A4, facecolor=SURFACE)
    text = TEXT[lang]
    dates = get_datetimes(data, rows)
    limits = date_limits(dates)

    page_header(fig, text["page_evolution"], text["sub_evolution"])

    gridspec = fig.add_gridspec(
        2, 1, left=0.085, right=0.965, top=0.865, bottom=0.575, hspace=0.58
    )

    mass = entry_for("Wk")
    ax_mass = fig.add_subplot(gridspec[0, 0])
    mass_values = get_values(data, "Wk", rows)
    plot_series(ax_mass, dates, mass_values, INK, width=1.8)
    ax_mass.set_ylim(*padded_limits(mass_values, 0.10))
    style_panel(ax_mass)
    style_dates(ax_mass, limits, show_labels=True)
    axis_titles(ax_mass, text["x_axis"], f"{text['mass']} (kg)", size=7.5)
    latest = last_valid(mass_values)
    if latest is not None:
        ax_mass.text(
            1.0,
            0.94,
            format_value(mass, latest),
            transform=ax_mass.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            fontweight="bold",
            color=INK,
        )

    bmi = entry_for("MI")
    ax_bmi = fig.add_subplot(gridspec[1, 0], sharex=ax_mass)
    bmi_values = get_values(data, "MI", rows)
    ax_bmi.axhspan(18.5, 25.0, color=GRID, linewidth=0, zorder=1)
    band_label(ax_bmi, 24.8, text["bmi_band"])
    plot_series(ax_bmi, dates, bmi_values, INK, width=1.8)
    ax_bmi.set_ylim(min(18.5, min(bmi_values) - 0.8), max(bmi_values) + 0.8)
    style_panel(ax_bmi)
    style_dates(ax_bmi, limits, show_labels=True)
    axis_titles(ax_bmi, text["x_axis"], f"{text['bmi']} (kg/m²)", size=7.5)
    latest = last_valid(bmi_values)
    if latest is not None:
        ax_bmi.text(
            1.0,
            0.94,
            format_value(bmi, latest),
            transform=ax_bmi.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            fontweight="bold",
            color=INK,
        )

    section_title(fig, 0.528, text["fat_segments"])
    reference_legend(fig, 0.528, text["reference"])
    small_multiples(
        fig,
        {"left": 0.085, "right": 0.965, "top": 0.490, "bottom": 0.065},
        [entry_for(key) for key in FAT_KEYS],
        data,
        rows,
        FAT,
        entry_for("FW"),
        lang,
        band=(8, 20),
        band_text=text["fat_band"],
        y_label=text["fat_panel"],
    )

    page_footer(fig, page, pages, lang, generated)
    return fig


def markers_panels(fig, area, data, rows, lang):
    gs = fig.add_gridspec(
        2,
        2,
        left=area["left"],
        right=area["right"],
        top=area["top"],
        bottom=area["bottom"],
        wspace=0.34,
        hspace=0.82,
    )
    dates = get_datetimes(data, rows)
    limits = date_limits(dates)
    text = TEXT[lang]

    ax = fig.add_subplot(gs[0, 0])
    values = get_values(data, "IF", rows)
    plot_series(ax, dates, values, MARKER)
    ax.axhline(12, color=AXIS, linewidth=1.0, linestyle=(0, (4, 3)))
    clean = [value for value in values if not math.isnan(value)]
    ax.set_ylim(0, max(14, max(clean) + 1))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    style_panel(ax)
    style_dates(ax, limits, show_labels=True, short=True)
    ax.set_title(
        f"{text['visceral']} ({unit_of(entry_for('IF'), lang)})",
        loc="left",
        fontsize=9,
        color=INK_2,
        pad=3,
    )
    axis_titles(ax, text["x_axis"], text["y_level"], size=7.5)
    ax.text(
        0.99,
        12.2,
        text["limit"],
        transform=ax.get_yaxis_transform(),
        ha="right",
        va="bottom",
        fontsize=6.8,
        color=MUTED,
    )

    ax = fig.add_subplot(gs[0, 1])
    real = get_values(data, "AG", rows)
    metabolic = get_values(data, "rA", rows)
    ax.plot(dates, real, color=AXIS, linewidth=1.2, zorder=2)
    plot_series(ax, dates, metabolic, MARKER)
    ax.set_ylim(*padded_limits(real + metabolic, 0.10))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    style_panel(ax)
    style_dates(ax, limits, show_labels=True, short=True)
    ax.set_title(
        f"{text['metabolic_age']} ({unit_of(entry_for('rA'), lang)})",
        loc="left",
        fontsize=9,
        color=INK_2,
        pad=16,
    )
    axis_titles(ax, text["x_axis"], text["y_years"], size=7.5)
    handles = [
        Line2D(
            [0],
            [0],
            color=MARKER,
            linewidth=1.4,
            marker="o",
            markersize=3,
            markerfacecolor=SURFACE,
        ),
        Line2D([0], [0], color=AXIS, linewidth=1.2),
    ]
    ax.legend(
        handles,
        [text["metabolic_age"], text["real_age"]],
        loc="lower right",
        bbox_to_anchor=(1.0, 1.0),
        ncol=2,
        fontsize=6.8,
        handlelength=1.2,
        borderaxespad=0.1,
        labelcolor=INK_2,
    )

    ax = fig.add_subplot(gs[1, 0])
    values = get_values(data, "rD", rows)
    plot_series(ax, dates, values, MARKER)
    ax.set_ylim(*padded_limits(values, 0.10))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    style_panel(ax)
    style_dates(ax, limits, show_labels=True, short=True)
    ax.set_title(
        f"{text['calories']} ({unit_of(entry_for('rD'), lang)})",
        loc="left",
        fontsize=9,
        color=INK_2,
        pad=3,
    )
    axis_titles(ax, text["x_axis"], unit_of(entry_for("rD"), lang), size=7.5)

    ax = fig.add_subplot(gs[1, 1])
    values = get_values(data, "ww", rows)
    ax.axhspan(50, 65, color=GRID, linewidth=0, zorder=1)
    band_label(ax, 63, text["water_band"])
    plot_series(ax, dates, values, MARKER)
    ax.set_ylim(48, 67)
    style_panel(ax)
    style_dates(ax, limits, show_labels=True, short=True)
    ax.set_title(
        f"{text['water']} ({unit_of(entry_for('ww'), lang)})",
        loc="left",
        fontsize=9,
        color=INK_2,
        pad=3,
    )
    axis_titles(ax, text["x_axis"], unit_of(entry_for("ww"), lang), size=7.5)


def page_markers(data, rows, lang, page, pages, generated=None):
    fig = plt.figure(figsize=A4, facecolor=SURFACE)
    text = TEXT[lang]
    page_header(fig, text["page_markers"], text["sub_markers"])

    section_title(fig, 0.885, text["muscle_segments"])
    small_multiples(
        fig,
        {"left": 0.085, "right": 0.965, "top": 0.855, "bottom": 0.545},
        [entry_for(key) for key in MUSCLE_KEYS],
        data,
        rows,
        MUSCLE,
        None,
        lang,
        shared=False,
        y_label=text["muscle_panel"],
    )

    section_title(fig, 0.487, text["markers"])
    markers_panels(
        fig,
        {"left": 0.085, "right": 0.965, "top": 0.44, "bottom": 0.065},
        data,
        rows,
        lang,
    )

    page_footer(fig, page, pages, lang, generated)
    return fig


# ---------------------------------------------------------------------------
# Body diagram
# ---------------------------------------------------------------------------


def text_colour(colour):
    red, green, blue, _ = to_rgba(colour)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#ffffff" if luminance < 0.55 else INK


def draw_body(fig, box, values, cmap, norm, title, colourbar_ticks):
    ax = fig.add_axes(box)
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-0.02, 2.2)
    ax.set_aspect("equal")
    ax.set_axis_off()

    grey = GRID
    ax.add_patch(Rectangle((0.468, 1.79), 0.064, 0.16, facecolor=grey, edgecolor=SURFACE, linewidth=2))
    ax.add_patch(Circle((0.5, 2.04), 0.085, facecolor=grey, edgecolor=SURFACE, linewidth=2))

    for key in ("FR", "FL", "Fr", "Fl", "FT"):
        face = cmap(norm(values[key]))
        ax.add_patch(
            Polygon(
                BODY_POLYGONS[key],
                closed=True,
                facecolor=face,
                edgecolor=SURFACE,
                linewidth=2.2,
                joinstyle="round",
            )
        )

    for key, spec in BODY_LABELS.items():
        ax.text(
            spec["xy"][0],
            spec["xy"][1],
            f"{values[key]:.1f}",
            fontsize=7.5,
            color=text_colour(cmap(norm(values[key]))),
            ha="center",
            va="center",
            rotation=spec["rotation"],
            fontweight="bold",
        )

    fig.text(
        box[0] + box[2] / 2,
        box[1] + box[3] + 0.015,
        title,
        fontsize=10,
        fontweight="bold",
        color=INK,
        ha="center",
        va="center",
    )

    cax = fig.add_axes([box[0] + 0.04, box[1] - 0.035, box[2] - 0.08, 0.010])
    mappable = ScalarMappable(norm=norm, cmap=cmap)
    bar = fig.colorbar(mappable, cax=cax, orientation="horizontal")
    bar.set_ticks(colourbar_ticks)
    bar.ax.tick_params(labelsize=7, length=0, colors=MUTED)
    bar.outline.set_edgecolor(AXIS)
    bar.outline.set_linewidth(0.6)


def page_body(data, rows, lang, page, pages, generated=None):
    fig = plt.figure(figsize=A4, facecolor=SURFACE)
    text = TEXT[lang]
    latest = rows[-1]
    moment = data["datetime"][latest]
    page_header(
        fig,
        text["page_body"],
        f"{text['measured_on']} {moment.strftime('%d/%m/%Y %H:%M')}",
    )

    fat_values = {key: value_at(data, key, latest) for key in FAT_KEYS[1:]}
    muscle_values = {
        MUSCLE_TO_FAT[key]: value_at(data, key, latest)
        for key in MUSCLE_KEYS[1:]
    }

    draw_body(
        fig,
        [0.045, 0.270, 0.380, 0.540],
        fat_values,
        FAT_CMAP,
        FAT_NORM,
        text["fat_panel"],
        [15, 20, 25, 30],
    )
    draw_body(
        fig,
        [0.585, 0.270, 0.380, 0.540],
        muscle_values,
        MUSCLE_CMAP,
        MUSCLE_NORM,
        text["muscle_panel"],
        [0, 10, 20, 30],
    )

    fat_total = value_at(data, "FW", latest)
    muscle_total = value_at(data, "mW", latest)
    fig.text(
        0.235,
        0.208,
        f"{text['total_value']} {fat_total:.1f} %",
        fontsize=9,
        fontweight="bold",
        color=INK,
        ha="center",
    )
    fig.text(
        0.775,
        0.208,
        f"{text['total_value']} {muscle_total:.1f} kg",
        fontsize=9,
        fontweight="bold",
        color=INK,
        ha="center",
    )
    fig.text(0.06, 0.165, text["not_measured"], fontsize=7.5, color=MUTED, ha="left")
    fig.text(0.06, 0.145, text["front_view"], fontsize=7.5, color=MUTED, ha="left")
    page_footer(fig, page, pages, lang, generated)
    return fig


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_pages(data, lang="pt", daily=True, generated=None):
    series = all_rows(data, daily=daily)
    rows = series[-3:]
    table_page, table = page_table(data, rows, lang, 1, 4, generated)
    pages = [
        table_page,
        page_body(data, series, lang, 2, 4, generated),
        page_trends(data, series, lang, 3, 4, generated),
        page_markers(data, series, lang, 4, 4, generated),
    ]
    return pages, table


def write_pdf(path, pages, lang="pt"):
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(path) as pdf:
        info = pdf.infodict()
        info["Title"] = TEXT[lang]["title"]
        info["Creator"] = "tanita_report.py"
        info["CreationDate"] = datetime.now()
        for figure in pages:
            pdf.savefig(figure, facecolor=SURFACE)


def svg_for(figure):
    buffer = io.StringIO()
    figure.savefig(
        buffer,
        format="svg",
        bbox_inches="tight",
        pad_inches=0.04,
        facecolor=SURFACE,
    )
    markup = buffer.getvalue()
    return markup[markup.index("<svg") :]


def table_html(table):
    lines = ['<table class="data">']
    for row in table:
        if row["kind"] == "head":
            lines.append("<thead><tr>")
            for cell in row["cells"]:
                lines.append(f"<th>{html.escape(cell).replace(chr(10), '<br>')}</th>")
            lines.append("</tr></thead><tbody>")
        elif row["kind"] == "group":
            lines.append(
                f'<tr class="group"><th colspan="5">{html.escape(row["label"])}</th></tr>'
            )
        else:
            label = html.escape(row["label"])
            unit = html.escape(row["unit"])
            numbers = []
            for value in row["values"]:
                text = html.escape(format_value(row["entry"], value)).replace("\n", "<br>")
                numbers.append(f'<td class="num">{text}</td>')
            lines.append(
                f'<tr><td>{label}</td><td class="unit">{unit}</td>'
                + "".join(numbers)
                + "</tr>"
            )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def tiles_html(tiles):
    blocks = []
    for tile in tiles:
        blocks.append(
            '<div class="tile">'
            f'<div class="tile-label">{html.escape(tile["label"])}</div>'
            f'<div class="tile-value">{html.escape(tile["value"])}</div>'
            f'<div class="tile-delta">{html.escape(tile["delta"])}</div>'
            "</div>"
        )
    return "\n".join(blocks)


HTML_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  background: #f9f9f7; color: #0b0b0b;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
}
main { max-width: 940px; margin: 0 auto; background: #fcfcfb; padding: 32px 40px 40px; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 40px 0 8px; }
p.sub, p.note { color: #52514e; font-size: 13px; margin: 0 0 20px; }
p.note { margin-top: 32px; color: #898781; }
.tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0 8px; }
.tile { border-top: 1px solid #e1e0d9; padding-top: 10px; }
.tile-label { color: #898781; font-size: 12px; }
.tile-value { font-size: 30px; font-weight: 700; letter-spacing: -0.5px; }
.tile-delta { color: #52514e; font-size: 12px; }
table.data { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 8px; }
table.data th { text-align: left; font-size: 12px; color: #52514e; padding: 8px; background: #f0efec; }
table.data th:not(:first-child) { text-align: right; }
table.data td { padding: 6px 8px; border-bottom: 1px solid #e1e0d9; }
table.data td.unit { color: #898781; font-size: 12px; }
table.data td.num { text-align: right; font-variant-numeric: tabular-nums; }
table.data tr.group th { background: #f0efec; color: #52514e; text-transform: uppercase; font-size: 11px; letter-spacing: 0.4px; }
figure { margin: 16px 0 32px; }
figure svg { width: 100%; height: auto; display: block; }
@media (max-width: 640px) {
  body { padding: 0; }
  main { padding: 20px; }
  .tiles { grid-template-columns: repeat(2, 1fr); }
}
"""


def write_html(path, data, table, pages, lang="pt", daily=True):
    text = TEXT[lang]
    body, trends, markers = pages[1], pages[2], pages[3]
    tiles = tiles_html(tile_data(data, recent_rows(data, daily=daily), lang))
    document = f"""<!DOCTYPE html>
<html lang="{'pt-BR' if lang == 'pt' else 'en'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(text['title'])}</title>
<style>{HTML_STYLE}</style>
</head>
<body>
<main>
<h1>{html.escape(text['title'])}</h1>
<p class="sub">{html.escape(subtitle_for(data, recent_rows(data, daily=daily), lang))}</p>
<section class="tiles">
{tiles}
</section>
<h2>{html.escape(text['table_title'])}</h2>
{table_html(table)}
<h2>{html.escape(text['page_body'])}</h2>
<figure>{svg_for(body)}</figure>
<h2>{html.escape(text['page_evolution'])}</h2>
<figure>{svg_for(trends)}</figure>
<h2>{html.escape(text['page_markers'])}</h2>
<figure>{svg_for(markers)}</figure>
<p class="note">{html.escape(text['note'])}</p>
</main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as file:
        file.write(document)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Build a PDF report from one Tanita CSV file."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="DATA1.CSV",
        help="input CSV file (default: DATA1.CSV)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "output file (default: tanita_report_<date>_<time>.pdf,"
            " with the generation date and time)"
        ),
    )
    parser.add_argument(
        "--html",
        metavar="PATH",
        help="also write a self-contained HTML file",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="keep all rows, including rows from the same day",
    )
    parser.add_argument(
        "--lang",
        choices=("pt", "en"),
        default="pt",
        help="report language (default: pt)",
    )
    return parser


def main(argv=None):
    args = build_argument_parser().parse_args(argv)

    try:
        data = tanita_parser.load_csv(args.input)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 2
    except (KeyError, ValueError) as error:
        print(f"Error: cannot parse {args.input}: {error}", file=sys.stderr)
        return 1

    dates = data.get("datetime", [])
    if not dates:
        print(f"Error: no measurement found in {args.input}", file=sys.stderr)
        return 1

    # One timestamp for the file name and for the page footers.
    generated = datetime.now()
    pages, table = build_pages(
        data,
        lang=args.lang,
        daily=not args.raw,
        generated=generated,
    )

    if args.output is None:
        stamp = generated.strftime("%Y-%m-%d_%H-%M-%S")
        output = Path(f"tanita_report_{stamp}.pdf")
    else:
        output = Path(args.output)
        if output.suffix == "":
            output = output.with_suffix(".pdf")

    try:
        if output.suffix.lower() == ".html":
            write_html(output, data, table, pages, lang=args.lang, daily=not args.raw)
        else:
            write_pdf(output, pages, lang=args.lang)
        if args.html:
            write_html(
                Path(args.html),
                data,
                table,
                pages,
                lang=args.lang,
                daily=not args.raw,
            )
    except OSError as error:
        print(f"Error: cannot write the file: {error}", file=sys.stderr)
        return 1
    finally:
        plt.close("all")

    print(f"{TEXT[args.lang]['file_written']} {output}")
    if args.html:
        print(f"{TEXT[args.lang]['file_written']} {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
