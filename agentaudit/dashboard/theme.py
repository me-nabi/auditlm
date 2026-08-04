# theme.py
# Design tokens, icons, CSS, and small HTML components for the dashboard.
# Everything visual lives here so pages stay readable and the look stays consistent.

from typing import Optional, Sequence

import streamlit as st

# --------------------------------------------------------------------------- #
# Tokens — one validated palette, stepped for each surface
# --------------------------------------------------------------------------- #

LIGHT = {
    "surface":    "#fcfcfb",
    "plane":      "#f4f4f1",
    "raised":     "#ffffff",
    "ink":        "#0b0b0b",
    "ink_2":      "#52514e",
    "muted":      "#898781",
    "grid":       "#e1e0d9",
    "baseline":   "#c3c2b7",
    "border":     "rgba(11,11,11,0.10)",
    "border_soft": "rgba(11,11,11,0.06)",
    "hover":      "rgba(11,11,11,0.04)",
    "series":     ("#2a78d6", "#eb6834", "#1baf7a", "#eda100"),
    "good":       "#0ca30c",
    "good_text":  "#006300",
    "warning":    "#fab219",
    "warn_text":  "#8a5a00",
    "critical":   "#d03b3b",
    "crit_text":  "#a02f2f",
}

DARK = {
    "surface":    "#1a1a19",
    "plane":      "#0d0d0d",
    "raised":     "#212120",
    "ink":        "#ffffff",
    "ink_2":      "#c3c2b7",
    "muted":      "#898781",
    "grid":       "#2c2c2a",
    "baseline":   "#383835",
    "border":     "rgba(255,255,255,0.12)",
    "border_soft": "rgba(255,255,255,0.07)",
    "hover":      "rgba(255,255,255,0.05)",
    "series":     ("#3987e5", "#d95926", "#199e70", "#c98500"),
    "good":       "#0ca30c",
    "good_text":  "#0ca30c",
    "warning":    "#fab219",
    "warn_text":  "#fab219",
    "critical":   "#d03b3b",
    "crit_text":  "#e66767",
}


def tokens() -> dict:
    """Active token set.

    Driven by `theme.base` in .streamlit/config.toml — the same setting that
    decides how Streamlit paints its own chrome, so the two can never disagree.
    (`st.context.theme.type` is NOT used here: it reports the *browser's*
    colour-scheme preference, which is happily "dark" while a pinned config
    renders light, leaving white text on a light background.)
    """
    try:
        base = (st.get_option("theme.base") or "light").strip().lower()
    except Exception:
        base = "light"
    return DARK if base == "dark" else LIGHT


def tone_colors(t: dict, tone: str) -> tuple[str, str]:
    """(accent, text) for a semantic tone."""
    return {
        "good":     (t["good"], t["good_text"]),
        "warning":  (t["warning"], t["warn_text"]),
        "critical": (t["critical"], t["crit_text"]),
        "info":     (t["series"][0], t["series"][0]),
        "neutral":  (t["baseline"], t["ink_2"]),
    }[tone]


# --------------------------------------------------------------------------- #
# Icons — inline stroke SVG, inherits currentColor
# --------------------------------------------------------------------------- #

_PATHS = {
    "overview": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/>'
                '<rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "details":  '<path d="M10 2v4"/><path d="M14 2v4"/>'
                '<path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/>'
                '<path d="M8 12h8"/><path d="M8 16h5"/>',
    "trends":   '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "compare":  '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/>'
                '<path d="M13 6h3a2 2 0 0 1 2 2v7"/><path d="M11 18H8a2 2 0 0 1-2-2V9"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "shield":   '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 '
                '6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "inbox":    '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
                '<path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    "check":    '<path d="M20 6 9 17l-5-5"/>',
    "x":        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "alert":    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
                '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "up":       '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
    "down":     '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "dot":      '<circle cx="12" cy="12" r="4"/>',
    "arrow":    '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "help":     '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
}


def icon(name: str, size: int = 16, stroke: float = 2) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" style="flex:none;">{_PATHS[name]}</svg>'
    )


# --------------------------------------------------------------------------- #
# Global stylesheet
# --------------------------------------------------------------------------- #

def inject_css(t: dict) -> None:
    st.markdown(
        f"""
        <style>
        .stAppDeployButton, [data-testid="stSkillsNudge"] {{ display: none; }}
        footer {{ visibility: hidden; }}
        [data-testid="stMainBlockContainer"] {{ padding-top: 3rem; max-width: 1400px; }}
        [data-testid="stSidebar"] {{
            border-right: 1px solid {t['baseline']};
            background: {t['plane']};
        }}
        [data-testid="stSidebarContent"] {{ padding-top: 1.2rem; }}

        /* ---------- Sidebar brand ---------- */
        .aa-brand {{ display:flex; align-items:center; gap:11px; padding:0 4px 18px 4px; }}
        .aa-logo {{
            width:38px; height:38px; border-radius:11px; display:grid; place-items:center;
            color:#fff; background:linear-gradient(140deg, {t['series'][0]}, #1b5bab);
            box-shadow:0 3px 10px rgba(42,120,214,0.32);
        }}
        .aa-brand-name {{ font-size:17px; font-weight:700; letter-spacing:-0.01em; color:{t['ink']}; line-height:1.15; }}
        .aa-brand-sub {{ font-size:11px; color:{t['muted']}; letter-spacing:0.02em; }}

        .aa-db {{
            margin:0 4px; padding:10px 11px; border:1px solid {t['border_soft']};
            border-radius:11px; background:{t['raised']}; overflow:hidden;
        }}
        .aa-db-top {{ display:flex; align-items:center; gap:7px; }}
        .aa-db-name {{
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
            font-weight:600; color:{t['ink']};
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }}
        .aa-db-meta {{ font-size:11px; color:{t['muted']}; margin-top:4px; padding-left:15px; }}
        .aa-live {{
            width:7px; height:7px; border-radius:50%; flex:none;
            background:{t['good']}; box-shadow:0 0 0 3px {t['good']}26;
        }}
        .aa-live-off {{ background:{t['muted']}; box-shadow:0 0 0 3px {t['muted']}26; }}

        .aa-nav-label {{
            font-size:10.5px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
            color:{t['muted']}; padding:16px 6px 7px 6px;
        }}

        /* Compact "change database" disclosure so it doesn't dominate the rail */
        [data-testid="stSidebar"] [data-testid="stExpander"] details {{
            border:none !important; background:transparent !important;
        }}
        [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
            padding:5px 6px !important; font-size:11.5px !important; color:{t['muted']} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{ color:{t['ink_2']} !important; }}

        /* Sidebar mini panel */
        .aa-mini {{
            margin:0 4px; padding:11px 12px; border:1px solid {t['border_soft']};
            border-radius:11px; background:{t['raised']};
        }}
        .aa-mini-label {{
            font-size:10px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
            color:{t['muted']}; margin-bottom:7px;
        }}
        .aa-mini-name {{ font-size:12.5px; font-weight:600; color:{t['ink']}; }}
        .aa-mini-time {{ font-size:11px; color:{t['muted']}; margin-top:1px; }}
        .aa-mini-row {{
            display:flex; align-items:center; justify-content:space-between;
            margin-top:9px; padding-top:9px; border-top:1px solid {t['border_soft']};
            font-size:11.5px; color:{t['ink_2']};
        }}
        .aa-mini-val {{ font-weight:650; color:{t['ink']}; font-variant-numeric:tabular-nums; }}

        /* ---------- Sidebar nav (restyled radio) ---------- */
        /* Streamlit puts an inline pixel width on the radio's element container,
           sizing it to the longest label. Every level from that container down
           has to be forced full-width (hence !important) or the hover/active
           surface stops short of the rail edge. */
        [data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stRadio"]) {{
            width:100% !important;
        }}
        [data-testid="stSidebar"] [data-testid="stRadio"] {{ width:100% !important; }}
        [data-testid="stSidebar"] [data-testid="stRadioGroup"] {{
            gap:3px; width:100% !important; align-items:stretch;
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"] {{
            position:relative; display:flex; width:100%; box-sizing:border-box;
            padding:9px 12px 9px 14px; border-radius:9px; margin:0;
            transition:background 120ms ease, color 120ms ease;
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"] > div,
        [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div {{
            width:100%;
        }}
        /* Active indicator: a real element, so the pill's radius can't clip it
           the way an inset box-shadow was being clipped into a faint arc. */
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]::before {{
            content:""; position:absolute; left:0; top:5px; bottom:5px; width:3px;
            border-radius:0 3px 3px 0; background:{t['series'][0]};
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div > div:first-child {{ display:none; }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"] p {{
            font-size:14px; font-weight:500; color:{t['ink_2']};
            display:flex; align-items:center; gap:11px;
        }}
        /* Material glyph inside each nav row */
        [data-testid="stSidebar"] [data-testid="stRadioOption"] [data-testid="stIconMaterial"] {{
            font-size:18px !important; color:{t['muted']};
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] [data-testid="stIconMaterial"] {{
            color:{t['series'][0]};
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{ background:{t['hover']}; }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{
            background:{t['series'][0]}1a;
        }}
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {{
            color:{t['series'][0]}; font-weight:600;
        }}

        /* ---------- Page header ---------- */
        .aa-head {{ display:flex; align-items:center; gap:12px; margin-bottom:4px; }}
        .aa-head-icon {{
            width:34px; height:34px; border-radius:10px; display:grid; place-items:center;
            background:{t['series'][0]}17; color:{t['series'][0]};
        }}
        .aa-head-title {{ font-size:25px; font-weight:700; letter-spacing:-0.02em; color:{t['ink']}; line-height:1.2; }}
        .aa-head-sub {{ font-size:14px; color:{t['muted']}; margin:0 0 22px 46px; }}

        .aa-sec {{
            font-size:11px; font-weight:700; letter-spacing:0.07em; text-transform:uppercase;
            color:{t['muted']}; margin:26px 0 10px 0;
        }}

        /* ---------- Stat cards ---------- */
        .aa-stat {{
            position:relative; background:{t['raised']}; border:1px solid {t['border_soft']};
            border-radius:14px; padding:15px 16px 12px 16px; height:100%; overflow:hidden;
            transition:border-color 140ms ease, transform 140ms ease;
        }}
        .aa-stat svg {{ display:block; max-width:100%; }}
        .aa-stat:hover {{ border-color:{t['border']}; transform:translateY(-1px); }}
        .aa-stat-top {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
        .aa-stat-label {{
            font-size:11px; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; color:{t['muted']};
        }}
        .aa-stat-value {{
            font-size:29px; font-weight:700; letter-spacing:-0.025em; color:{t['ink']};
            line-height:1.15; margin-top:7px;
        }}
        .aa-stat-foot {{ display:flex; align-items:flex-end; justify-content:space-between; gap:10px; margin-top:8px; height:34px; }}
        .aa-delta {{ display:inline-flex; align-items:center; gap:3px; font-size:12px; font-weight:600; }}
        .aa-stat-hint {{ font-size:11.5px; color:{t['muted']}; }}

        /* ---------- Badges ---------- */
        .aa-badge {{
            display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:600;
            padding:3px 10px; border-radius:999px; border:1px solid transparent; white-space:nowrap;
        }}

        /* ---------- Panels (Streamlit bordered container) ---------- */
        [data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > [data-testid="stVerticalBlock"] .aa-panel-title) {{
            background:{t['raised']}; border:1px solid {t['border_soft']} !important;
            border-radius:14px !important; padding:15px 17px 9px 17px !important;
        }}
        .aa-panel-title {{ font-size:13.5px; font-weight:650; color:{t['ink']}; }}
        .aa-panel-sub {{ font-size:11.5px; color:{t['muted']}; margin:1px 0 6px 0; }}

        .aa-field {{ margin-bottom:12px; }}
        .aa-field-label {{
            font-size:11px; font-weight:600; letter-spacing:0.05em; text-transform:uppercase;
            color:{t['muted']}; margin-bottom:5px;
        }}
        .aa-text {{
            border:1px solid {t['border_soft']}; border-left:3px solid var(--accent);
            border-radius:10px; padding:11px 13px; font-size:13.5px; line-height:1.55;
            color:{t['ink']}; background:{t['plane']}; white-space:pre-wrap; word-break:break-word;
        }}

        /* ---------- Empty state ---------- */
        .aa-empty {{
            display:flex; flex-direction:column; align-items:center; gap:9px;
            border:1px dashed {t['border']}; border-radius:16px; padding:44px 24px;
            background:{t['plane']}; text-align:center;
        }}
        .aa-empty-icon {{ color:{t['muted']}; }}
        .aa-empty-title {{ font-size:15px; font-weight:650; color:{t['ink']}; }}
        .aa-empty-body {{ font-size:13px; color:{t['muted']}; max-width:460px; line-height:1.6; }}
        .aa-empty-body code {{
            background:{t['hover']}; padding:1px 6px; border-radius:5px;
            font-size:12px; color:{t['ink_2']};
        }}

        /* ---------- Diff rows ---------- */
        .aa-diff {{
            display:flex; align-items:center; gap:14px; padding:12px 15px;
            border:1px solid {t['border_soft']}; border-radius:11px;
            background:{t['raised']}; margin-bottom:7px;
        }}
        .aa-diff-name {{ flex:1.6; font-size:13.5px; font-weight:600; color:{t['ink']}; }}
        .aa-diff-val {{ flex:1; font-size:13px; color:{t['ink_2']}; font-variant-numeric:tabular-nums; }}
        .aa-diff-val b {{ color:{t['ink']}; font-weight:600; }}
        .aa-diff-arrow {{ color:{t['muted']}; display:flex; }}

        /* ---------- Streamlit widget polish ---------- */
        [data-testid="stExpander"] details {{
            border:1px solid {t['border_soft']} !important; border-radius:11px !important;
            background:{t['raised']} !important;
        }}
        [data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #

def brand(t: dict) -> None:
    st.sidebar.markdown(
        f"""
        <div class="aa-brand">
            <div class="aa-logo">{icon('shield', 21, 2)}</div>
            <div>
                <div class="aa-brand-name">AgentAudit</div>
                <div class="aa-brand-sub">LLM evaluation · v0.1.0</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def db_chip(t: dict, name: str, meta: str = "", connected: bool = True) -> None:
    dot_cls = "aa-live" if connected else "aa-live aa-live-off"
    meta_html = f'<div class="aa-db-meta">{meta}</div>' if meta else ""
    st.sidebar.markdown(
        f"""
        <div class="aa-db">
            <div class="aa-db-top">
                <span class="{dot_cls}"></span>
                <span class="aa-db-name" title="{name}">{name}</span>
            </div>
            {meta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def last_run_panel(t: dict, pipeline: str, when: str, rows: list[tuple[str, str, str]]) -> None:
    """Compact 'latest run' summary for the sidebar. rows = [(label, value, color)]."""
    row_html = "".join(
        f'<div class="aa-mini-row"><span>{label}</span>'
        f'<span class="aa-mini-val" style="color:{color};">{value}</span></div>'
        for label, value, color in rows
    )
    st.sidebar.markdown(
        f"""
        <div class="aa-mini">
            <div class="aa-mini-label">Latest run</div>
            <div class="aa-mini-name">{pipeline}</div>
            <div class="aa-mini-time">{when}</div>
            {row_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_head(t: dict, ico: str, title: str, sub: str) -> None:
    st.markdown(
        f"""
        <div class="aa-head">
            <div class="aa-head-icon">{icon(ico, 19)}</div>
            <div class="aa-head-title">{title}</div>
        </div>
        <div class="aa-head-sub">{sub}</div>
        """,
        unsafe_allow_html=True,
    )


def section(label: str) -> None:
    st.markdown(f'<div class="aa-sec">{label}</div>', unsafe_allow_html=True)


def badge(t: dict, tone: str, ico: Optional[str], text: str) -> str:
    accent, fg = tone_colors(t, tone)
    glyph = f'<span style="display:flex;">{icon(ico, 12, 2.5)}</span>' if ico else ""
    return (
        f'<span class="aa-badge" style="color:{fg};background:{accent}1f;'
        f'border-color:{accent}44;">{glyph}{text}</span>'
    )


def sparkline(values: Sequence[float], color: str, width: int = 108, height: int = 30) -> str:
    """Inline SVG sparkline — area + line, no axes."""
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return ""

    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1.0

    # Inset both axes so the 2.6px end-cap dot and the stroke stay fully inside
    # the viewBox instead of being clipped at the edges.
    pad_x, pad_y = 4, 4
    step = (width - 2 * pad_x) / (len(pts) - 1)

    coords = [
        (pad_x + i * step, height - pad_y - ((v - lo) / span) * (height - 2 * pad_y))
        for i, v in enumerate(pts)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = (
        f"M{pad_x},{height} "
        + " ".join(f"L{x:.1f},{y:.1f}" for x, y in coords)
        + f" L{width - pad_x},{height} Z"
    )
    cx, cy = coords[-1]
    uid = abs(hash((line, color))) % 100000

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">
      <defs><linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="{color}" stop-opacity="0.28"/>
        <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
      </linearGradient></defs>
      <path d="{area}" fill="url(#g{uid})"/>
      <polyline points="{line}" stroke="{color}" stroke-width="1.8"
                stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.6" fill="{color}"/>
    </svg>
    """


def stat_card(
    t: dict,
    label: str,
    value: str,
    tone: str = "info",
    delta: Optional[float] = None,
    lower_is_better: bool = True,
    spark: Optional[Sequence[float]] = None,
    hint: str = "",
) -> None:
    accent, _ = tone_colors(t, tone)

    delta_html = f'<span class="aa-stat-hint">{hint}</span>' if hint else "<span></span>"
    if delta is not None and abs(delta) > 1e-9:
        improved = (delta < 0) if lower_is_better else (delta > 0)
        d_color = t["good_text"] if improved else t["crit_text"]
        arrow = "down" if delta < 0 else "up"
        delta_html = (
            f'<span class="aa-delta" style="color:{d_color};">'
            f'{icon(arrow, 13, 2.5)}{abs(delta):.2f}</span>'
        )

    spark_html = sparkline(spark, accent) if spark else ""

    st.markdown(
        f"""
        <div class="aa-stat">
            <div class="aa-stat-top">
                <span class="aa-stat-label">{label}</span>
                <span style="width:7px;height:7px;border-radius:50%;background:{accent};flex:none;"></span>
            </div>
            <div class="aa-stat-value">{value}</div>
            <div class="aa-stat-foot">{delta_html}{spark_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(t: dict, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="aa-empty">
            <div class="aa-empty-icon">{icon('inbox', 30, 1.5)}</div>
            <div class="aa-empty-title">{title}</div>
            <div class="aa-empty-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
