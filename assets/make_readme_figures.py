"""Generate the README visuals in assets/.

Outputs: assets/workflow.png, assets/layer_preview_map.png,
assets/arcgis_pro_project_thumbnail.png, assets/slides/slide_01-05.png and
assets/slides_preview.gif.

The permit map preview uses the saved FY2026 extract of the same TOPS
construction-permit layer (MapServer/23) from the tableau_DDOT repository.
No API requests are made.

    python -m pip install matplotlib pandas pillow
    python assets/make_readme_figures.py --permits-csv ../tableau_DDOT/data/raw/fy2026_new_permits_all_api_records.csv

Uses the Inter font when installed and falls back to the default otherwise.
"""
import argparse
import json
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
SLIDES = OUT / "slides"
SLIDES.mkdir(parents=True, exist_ok=True)
PROJECT = ROOT / "arcgispro" / "DDOT_CS12_GIS"

parser = argparse.ArgumentParser()
parser.add_argument("--permits-csv", type=Path, required=True,
                    help="tableau_DDOT data/raw/fy2026_new_permits_all_api_records.csv")
args = parser.parse_args()

for f in fm.findSystemFonts():
    if "Inter" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Inter"})

DARK, MUTED = "#1F2937", "#6B7280"
NAVY, PURPLE, TEAL, ORANGE = "#1E3A5F", "#560085", "#0F766E", "#C2410C"

# ---------------------------------------------------------------- project facts (read from the .aprx)
aprx = zipfile.ZipFile(PROJECT / "DDOT_CS12_GIS.aprx")
layers = {}
for name in ["Map/Roadway_SubBlock.json", "Map/DDOT___Public_Space_Construction_Permits___Status.json",
             "Map/CityworksRequest.json"]:
    j = json.loads(aprx.read(name))
    conn = j["featureTable"]["dataConnection"]
    classes = [c["label"] for g in j["renderer"].get("groups", []) for c in g["classes"]]
    layers[j["name"]] = {"url": conn["workspaceConnectionString"].replace("URL=", ""),
                         "layer": conn["dataset"], "classes": classes, "visible": j.get("visibility", False)}
version = aprx.read("DocumentInfo.xml").decode().split("<Version>")[1].split("<")[0]

# Actual ArcGIS Pro thumbnail (BMP inside a .jpg name) -> PNG
thumb_src = next((PROJECT / "Index").rglob("Thumbnail/*.jpg"))
Image.open(thumb_src).convert("RGB").save(OUT / "arcgis_pro_project_thumbnail.png")

# ---------------------------------------------------------------- permit preview data
permits = pd.read_csv(args.permits_csv, usecols=["StatusDescription", "Longitude", "Latitude"], low_memory=False)
# Same colours as the ArcGIS Pro unique-value renderer for StatusDescription.
STATUS_COLORS = {"Issued": "#005CE6", "Permit Expired": "#FF0000", "Suspended": "#A8A800", "Revoked": "#111111"}


def draw_permit_map(ax, s=2.0, legend_fs=9):
    ax.set_facecolor("#F3F4F6")
    lat0 = np.radians(38.9)
    for status in ["Permit Expired", "Issued", "Suspended", "Revoked"]:
        m = permits.StatusDescription.eq(status)
        if m.any():
            ax.scatter(permits.Longitude[m] * np.cos(lat0), permits.Latitude[m], s=s if m.sum() > 100 else s * 12,
                       c=STATUS_COLORS[status], alpha=0.55 if m.sum() > 100 else 1, linewidths=0,
                       label=f"{status} ({m.sum():,})")
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    handles = [Line2D([], [], marker="o", ls="", ms=legend_fs * 0.8, color=STATUS_COLORS[k],
                      label=f"{k} ({permits.StatusDescription.eq(k).sum():,})") for k in STATUS_COLORS]
    ax.legend(handles=handles, loc="lower left", fontsize=legend_fs, frameon=True, facecolor="white",
              edgecolor="#D1D5DB", title="StatusDescription", title_fontsize=legend_fs + 0.5)


def box(fig_or_ax, x, y, w, h, title, body, fc, tc="white", title_fs=13, body_fs=10.5, transform=None):
    tr = transform or fig_or_ax.transAxes
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.015", transform=tr,
                           fc=fc, ec="none")
    fig_or_ax.add_artist(patch) if hasattr(fig_or_ax, "add_artist") else None
    fig_or_ax.text(x + w / 2, y + h * 0.7, title, ha="center", va="center", fontsize=title_fs,
                   fontweight="bold", color=tc, transform=tr)
    fig_or_ax.text(x + w / 2, y + h * 0.33, body, ha="center", va="center", fontsize=body_fs, color=tc,
                   transform=tr, linespacing=1.4)


def arrow(ax, x1, y1, x2, y2, dashed=False):
    ax.add_artist(FancyArrowPatch((x1, y1), (x2, y2), transform=ax.transAxes, arrowstyle="-|>",
                                  mutation_scale=18, lw=1.8, color="#9CA3AF",
                                  linestyle=(0, (4, 3)) if dashed else "-"))


def draw_workflow(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    srcs = [("Roadway SubBlock", "DCGIS Transportation\nMapServer/162", PURPLE),
            ("Construction Permits", "DDOT TOPS\nMapServer/23", ORANGE),
            ("Cityworks Requests", "DDOT Cityworks\nMapServer/1", TEAL)]
    for i, (t, b, c) in enumerate(srcs):
        y = 0.7 - i * 0.3
        box(ax, 0.0, y, 0.22, 0.24, t, b, c)
        arrow(ax, 0.225, y + 0.12, 0.315, 0.5)
    box(ax, 0.32, 0.22, 0.2, 0.56, f"ArcGIS Pro {version}", "", NAVY)
    ax.text(0.42, 0.42, "DDOT_CS12_GIS.aprx\nWeb Mercator map\nTopographic + Hillshade\nbasemap; live layers",
            ha="center", va="center", fontsize=10, color="white", linespacing=1.4, transform=ax.transAxes)
    arrow(ax, 0.525, 0.5, 0.6, 0.5)
    box(ax, 0.605, 0.3, 0.17, 0.4, "Field inventory", "src/01_export_\nfield_inventory.py\n(arcpy, read-only)",
        "#374151", body_fs=10)
    arrow(ax, 0.78, 0.5, 0.835, 0.5)
    box(ax, 0.84, 0.3, 0.16, 0.4, "CSV reports", "3 per-layer\nfield lists +\nall_ddot_fields.csv", "#6B7280",
        body_fs=10)
    ax.text(0.92, 0.18, "Next: spatial analysis\n(in progress)", ha="center", fontsize=10.5, color=MUTED,
            style="italic", transform=ax.transAxes)
    arrow(ax, 0.92, 0.295, 0.92, 0.25, dashed=True)


# ---------------------------------------------------------------- standalone figures
def fig_workflow():
    fig = plt.figure(figsize=(13, 4.6), dpi=200, facecolor="white")
    fig.text(0.02, 0.92, "Project workflow: three live DDOT/DCGIS services in one ArcGIS Pro project",
             fontsize=16, fontweight="bold", color=DARK)
    draw_workflow(fig.add_axes([0.02, 0.03, 0.96, 0.82]))
    fig.savefig(OUT / "workflow.png", facecolor="white")
    plt.close(fig)


def fig_map():
    fig = plt.figure(figsize=(10, 10.8), dpi=200, facecolor="white")
    fig.text(0.5, 0.96, "Construction Permits layer (TOPS MapServer/23): data preview", ha="center",
             fontsize=18, fontweight="bold", color=DARK)
    fig.text(0.5, 0.932, f"{len(permits):,} FY2026 new-permit location records, coloured by StatusDescription "
             "(Issued and Permit Expired use the project's symbol colours)", ha="center", fontsize=10.5, color=MUTED)
    draw_permit_map(fig.add_axes([0.03, 0.05, 0.94, 0.86]), s=2.4, legend_fs=10)
    fig.text(0.5, 0.02, "Points from the saved tableau_DDOT extract of the same layer; the ArcGIS Pro map itself "
             "streams the live service.", ha="center", fontsize=9, color=MUTED)
    fig.savefig(OUT / "layer_preview_map.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- slides
W, H, NS = 13.333, 7.5, 5


def slide_base(num, title, subtitle=None):
    fig = plt.figure(figsize=(W, H), dpi=150, facecolor="white")
    fig.patches.append(plt.Rectangle((0, 0.93), 1, 0.07, transform=fig.transFigure, fc=NAVY))
    fig.patches.append(plt.Rectangle((0, 0.925), 1, 0.006, transform=fig.transFigure, fc=PURPLE))
    fig.text(0.035, 0.957, "DDOT  |  ArcGIS Pro + Python GIS Project", color="white", fontsize=12,
             va="center", fontweight="semibold")
    fig.text(0.965, 0.957, f"{num} / {NS}", color="#CBD5E1", fontsize=11, va="center", ha="right")
    fig.text(0.035, 0.85, title, fontsize=26, fontweight="bold", color=DARK)
    if subtitle:
        fig.text(0.035, 0.805, subtitle, fontsize=13, color=MUTED)
    return fig


def save_slide(fig, n):
    fig.savefig(SLIDES / f"slide_{n:02d}.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def slides():
    # 1 - title
    fig = plt.figure(figsize=(W, H), dpi=150, facecolor="#0F172A")
    ax = fig.add_axes([0.55, 0.06, 0.42, 0.88])
    draw_permit_map(ax, s=1.2, legend_fs=7.5)
    ax.set_facecolor("#0F172A")
    ax.get_legend().remove()
    fig.patches.append(plt.Rectangle((0.05, 0.585), 0.1, 0.008, transform=fig.transFigure, fc="#A78BFA"))
    fig.text(0.05, 0.73, "ArcGIS Pro + Python", fontsize=36, fontweight="bold", color="white")
    fig.text(0.05, 0.63, "DDOT GIS Project", fontsize=36, fontweight="bold", color="#A78BFA")
    fig.text(0.05, 0.54, "Roadway subblocks, construction permits and\nCityworks service requests in one "
             "ArcGIS Pro\nproject, with arcpy automation.", fontsize=16, color="#E5E7EB", linespacing=1.5, va="top")
    fig.text(0.05, 0.2, "ArcGIS Pro  •  arcpy  •  DCGIS feature services", fontsize=13, color="#9CA3AF")
    fig.text(0.05, 0.1, "Amir Moayyedi", fontsize=15, color="white", fontweight="semibold")
    fig.text(0.05, 0.05, f"1 / {NS}", fontsize=11, color="#6B7280")
    save_slide(fig, 1)

    # 2 - data sources
    fig = slide_base(2, "Three live DDOT / DCGIS data sources", "Connected as feature-service layers; "
                     "nothing is copied into the project")
    cards = [("Roadway SubBlock", "Line segments of DC's\nroadway network\n\nDCGIS_DATA /\nTransportation_WebMercator\n"
              "MapServer/162\n\nSymbol: single purple line", PURPLE),
             ("Public Space Construction\nPermits (Status)", "Permit locations\n\nDCGIS_APPS / DDOT_TOPS\nMapServer/23\n\n"
              "Coloured by StatusDescription:\nIssued · Permit Expired ·\nApproved (Pending Payment) · Pending", ORANGE),
             ("Cityworks Requests", "Service requests\n\nDDOT / Cityworks\nMapServer/1\n\nColoured by STATUS:\n"
              "Open · Pending · Inspection\nCompleted · Completed · Closed", TEAL)]
    for i, (t, b, c) in enumerate(cards):
        x0 = 0.035 + i * 0.316
        fig.patches.append(FancyBboxPatch((x0, 0.1), 0.295, 0.64, boxstyle="round,pad=0,rounding_size=0.012",
                                          transform=fig.transFigure, fc=c, ec="none"))
        fig.text(x0 + 0.1475, 0.65, t, ha="center", va="center", fontsize=16, fontweight="bold", color="white",
                 linespacing=1.2)
        fig.text(x0 + 0.1475, 0.34, b, ha="center", va="center", fontsize=12, color="white", linespacing=1.45)
    save_slide(fig, 2)

    # 3 - workflow
    fig = slide_base(3, "Project workflow", f"ArcGIS Pro {version} project + read-only arcpy automation")
    draw_workflow(fig.add_axes([0.03, 0.1, 0.94, 0.62]))
    save_slide(fig, 3)

    # 4 - permit layer preview
    fig = slide_base(4, "What the permit layer looks like", f"{len(permits):,} FY2026 new-permit location "
                     "records from the same TOPS layer (tableau_DDOT extract)")
    draw_permit_map(fig.add_axes([0.03, 0.04, 0.5, 0.74]), s=1.4, legend_fs=9)
    fig.text(0.58, 0.68, "Why it matters", fontsize=17, fontweight="bold", color=DARK)
    fig.text(0.58, 0.62,
             "• Permits cluster along the downtown\n   grid and the main corridors.\n\n"
             "• One permit can list many locations,\n   so a map of rows over-weights big\n   multi-site permits.\n\n"
             "• Joining permits to roadway subblocks\n   and Cityworks requests is the core\n   spatial task of this project.",
             fontsize=13, color="#374151", linespacing=1.35, va="top")
    save_slide(fig, 4)

    # 5 - status & next steps
    fig = slide_base(5, "Status and next steps", "This repository is the project foundation; analysis is in progress")
    done = ["ArcGIS Pro project with all three DDOT layers", "Status symbology for permits and Cityworks requests",
            "File geodatabase and toolbox created", "arcpy field-inventory script (01)"]
    todo = ["Run the field inventory and commit the CSV reports", "Spatial joins: permits ↔ subblocks ↔ requests",
            "Maps and layouts exported from ArcGIS Pro", "Findings and technical report"]
    for col, (head, items, c, mark) in enumerate([("Done", done, TEAL, "✓"), ("Next", todo, "#9CA3AF", "○")]):
        x0 = 0.035 + col * 0.48
        fig.text(x0, 0.7, head, fontsize=18, fontweight="bold", color=c)
        for i, t in enumerate(items):
            fig.text(x0, 0.6 - i * 0.12, f"{mark}  {t}", fontsize=14, color=DARK)
    save_slide(fig, 5)

    frames = [Image.open(SLIDES / f"slide_{i:02d}.png").convert("RGB").resize((1000, 562), Image.LANCZOS)
              for i in range(1, NS + 1)]
    frames = [f.quantize(colors=200, method=Image.Quantize.MEDIANCUT) for f in frames]
    frames[0].save(OUT / "slides_preview.gif", save_all=True, append_images=frames[1:], duration=3200,
                   loop=0, optimize=True)


fig_workflow()
fig_map()
slides()
print("done", version, {k: v["layer"] for k, v in layers.items()}, len(permits))
