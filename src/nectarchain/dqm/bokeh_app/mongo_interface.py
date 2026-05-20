"""
Bokeh server app — MongoDB explorer
====================================
Auto-discovers fields in a MongoDB collection, builds appropriate filter
controls for each field type, and displays matching documents in a DataTable.

Run with:
    bokeh serve main.py --show

Configuration: edit the three constants below or set environment variables
    MONGO_URI, MONGO_DB, MONGO_COLLECTION
"""

import os
from datetime import datetime, date

from pymongo import MongoClient
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource,
    DataTable,
    DateFormatter,
    Div,
    NumberFormatter,
    RangeSlider,
    DatetimeRangeSlider,
    Select,
    StringFormatter,
    TableColumn,
    TextInput,
)

# ── Configuration ────────────────────────────────────────────────────────────

MONGO_URI        = os.getenv("MONGO_URI",        "mongodb://192.168.30.104:27017")
MONGO_DB         = os.getenv("MONGO_DB",         "test")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "runconfig")

# Maximum number of documents fetched for display (keep UI responsive)
MAX_DOCS = 10000

# ── Connect & introspect ──────────────────────────────────────────────────────

client     = MongoClient(MONGO_URI)
db         = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

def _infer_fields(sample_size: int = 10000) -> dict:
    """
    Sample documents and return a dict:
        field_name -> {"type": "numeric"|"date"|"string"|"bool", "values": [...]}
    Skips the internal _id field.
    """
    docs   = list(collection.find({}, {"_id": 0}).limit(sample_size))
    if not docs:
        return {}

    # Collect all values per field across the sample
    raw: dict[str, list] = {}
    for doc in docs:
        for k, v in doc.items():
            raw.setdefault(k, [])
            if v is not None:
                raw[k].append(v)

    fields = {}
    for name, values in raw.items():
        if name == "firstvar" or name == "secondvar" or name == "thirdvar":
            continue
        if not values:
            fields[name] = {"type": "string", "values": []}
            continue

        # Determine dominant type
        type_counts = {"numeric": 0, "date": 0, "bool": 0, "string": 0}
        for v in values:
            if isinstance(v, bool):
                type_counts["bool"] += 1
            elif isinstance(v, (int, float)):
                type_counts["numeric"] += 1
            elif isinstance(v, (datetime, date)):
                type_counts["date"] += 1
            else:
                type_counts["string"] += 1

        dominant = max(type_counts, key=type_counts.get)
        fields[name] = {"type": dominant, "values": values}

    return fields

FIELD_META = _infer_fields()

# ── Build controls ────────────────────────────────────────────────────────────

controls: dict = {}   # field_name -> bokeh widget

def _make_control(name: str, meta: dict):
    """Return the most appropriate Bokeh widget for the field."""
    ftype  = meta["type"]
    values = meta["values"]

    if ftype == "numeric" and values:
        lo  = min(float(v) for v in values if isinstance(v, (int, float)))
        hi  = max(float(v) for v in values if isinstance(v, (int, float)))
        # Avoid degenerate slider (min == max)
        if lo == hi:
            hi = lo + 1
        step = (hi - lo) / 100 if (hi - lo) > 100 else 0.01
        return RangeSlider(
            title=name,
            start=lo, end=hi,
            value=(lo, hi),
            step=step,
            sizing_mode="stretch_width",
        )

    if ftype == "date" and values:
        dates = []
        for v in values:
            if isinstance(v, datetime):
                dates.append(v)
            elif isinstance(v, date):
                dates.append(datetime(v.year, v.month, v.day))
        if dates:
            lo = min(dates)
            hi = max(dates)
            if lo == hi:
                from datetime import timedelta
                hi = lo + timedelta(days=1)
            return DatetimeRangeSlider(
                title=name,
                start=lo, end=hi,
                value=(lo, hi),
                sizing_mode="stretch_width",
            )

    if ftype == "bool":
        return Select(
            title=name,
            options=["Any", "True", "False"],
            value="Any",
            sizing_mode="stretch_width",
        )

    # string  — free-text search
    return TextInput(
        title=f"{name} contains",
        value="",
        sizing_mode="stretch_width",
    )

for fname, fmeta in FIELD_META.items():
    controls[fname] = _make_control(fname, fmeta)

# ── DataTable setup ───────────────────────────────────────────────────────────

def _make_columns() -> list[TableColumn]:
    cols = []
    for fname, fmeta in FIELD_META.items():
        ftype = fmeta["type"]
        if ftype == "numeric":
            fmt = NumberFormatter(format="0,0.##")
        elif ftype == "date":
            fmt = DateFormatter(format="%Y-%m-%d__%H:%M:%S")
        else:
            fmt = StringFormatter()
        cols.append(TableColumn(field=fname, title=fname, formatter=fmt))
    return cols

source     = ColumnDataSource(data={f: [] for f in FIELD_META})
table_cols = _make_columns()
data_table = DataTable(
    source=source,
    columns=table_cols,
    sizing_mode="stretch_width",
    height=600,
    autosize_mode="force_fit",
)

status_div = Div(
    text="",
    styles={"font-size": "13px", "color": "#555", "margin-bottom": "6px"},
    sizing_mode="stretch_width",
)

# ── Query builder ─────────────────────────────────────────────────────────────

def _build_query() -> dict:
    """Translate current widget values into a MongoDB filter dict."""
    query: dict = {}

    for fname, widget in controls.items():
        ftype = FIELD_META[fname]["type"]

        if ftype == "numeric":
            lo, hi = widget.value
            if lo > widget.start or hi < widget.end:
                query[fname] = {"$gte": lo, "$lte": hi}

        elif ftype == "date":
            lo_ms, hi_ms = widget.value   # milliseconds since epoch
            if lo_ms > widget.start or hi_ms < widget.end:
                lo_dt = datetime.fromtimestamp(lo_ms / 1000)
                hi_dt = datetime.fromtimestamp(hi_ms / 1000)
                query[fname] = {"$gte": lo_dt, "$lte": hi_dt}

        elif ftype == "bool":
            if widget.value == "True":
                query[fname] = True
            elif widget.value == "False":
                query[fname] = False
            # "Any" → no filter on this field

        else:  # string / TextInput
            txt = widget.value.strip()
            if txt:
                query[fname] = {"$regex": txt, "$options": "i"}

    return query


def update(attr, old, new):
    query = _build_query()
    cursor = collection.find(query, {"_id": 0}).limit(MAX_DOCS)
    docs   = list(cursor)

    if not docs:
        source.data = {f: [] for f in FIELD_META}
        status_div.text = "No documents match the current filters."
        return

    df = pd.DataFrame(docs)

    # Ensure all expected columns exist (some docs may lack optional fields)
    for fname in FIELD_META:
        if fname not in df.columns:
            df[fname] = None

    # Convert datetime columns to ms-since-epoch so Bokeh DateFormatter works
    for fname, fmeta in FIELD_META.items():
        if fmeta["type"] == "date" and fname in df.columns:
            df[fname] = pd.to_datetime(df[fname], errors="coerce")

    total = collection.count_documents(query)
    shown = len(df)
    status_div.text = (
        f"<b>{shown}</b> documents shown"
        + (f" (of {total} matching — increase MAX_DOCS to see more)" if total > shown else "")
    )

    source.data = {fname: df[fname].tolist() for fname in FIELD_META if fname in df.columns}

# ── Wire controls ─────────────────────────────────────────────────────────────

for widget in controls.values():
    widget.on_change("value", update)

# ── Layout ────────────────────────────────────────────────────────────────────

header = Div(
    text=f"<h2 style='margin:0'>MongoDB explorer — <code>{MONGO_DB}.{MONGO_COLLECTION}</code></h2>",
    sizing_mode="stretch_width",
)

sidebar = column(
    *controls.values(),
    width=280,
    sizing_mode="fixed",
    styles={"overflow-y": "auto", "max-height": "90vh", "padding-right": "8px"},
)

main_area = column(
    status_div,
    data_table,
    sizing_mode="stretch_width",
)

layout = column(
    header,
    row(sidebar, main_area, sizing_mode="stretch_width"),
    sizing_mode="stretch_width",
)

update(attr=None, old=None, new=None)   # initial data load

curdoc().add_root(layout)
curdoc().title = f"{MONGO_DB}.{MONGO_COLLECTION} explorer"
