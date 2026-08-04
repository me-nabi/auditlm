# charts.py
# Altair trend charts for the dashboard.
# Gradient area + line, a readable time axis, and a hover crosshair with tooltip.

import altair as alt
import pandas as pd


def _axis_time(t: dict) -> alt.Axis:
    # labelAngle=0 + a small tickCount is what keeps timestamps horizontal and
    # legible instead of the rotated ISO strings Streamlit's default chart emits.
    return alt.Axis(
        format="%b %d",
        labelAngle=0,
        tickCount=5,
        grid=False,
        domainColor=t["baseline"],
        tickColor=t["baseline"],
        tickSize=4,
        labelColor=t["muted"],
        labelFontSize=11,
        labelPadding=6,
        title=None,
    )


def _axis_value(t: dict, fmt: str) -> alt.Axis:
    return alt.Axis(
        format=fmt,
        tickCount=4,
        grid=True,
        gridColor=t["grid"],
        gridDash=[3, 3],
        domain=False,
        ticks=False,
        labelColor=t["muted"],
        labelFontSize=11,
        labelPadding=8,
        title=None,
    )


def trend_chart(
    df: pd.DataFrame,
    value_col: str,
    color: str,
    t: dict,
    value_fmt: str = ".2f",
    axis_fmt: str = ".2f",
    value_title: str = "Value",
    height: int = 190,
) -> alt.LayerChart:
    """Single-series time chart: gradient area, 2px line, hover crosshair + tooltip."""
    d = (
        df[["timestamp", value_col]]
        .dropna(subset=[value_col])
        .rename(columns={value_col: "value"})
        .copy()
    )
    d["timestamp"] = pd.to_datetime(d["timestamp"])

    x = alt.X("timestamp:T", axis=_axis_time(t))
    y = alt.Y("value:Q", axis=_axis_value(t, axis_fmt), scale=alt.Scale(nice=True, zero=False))

    base = alt.Chart(d)

    area = base.mark_area(
        line=False,
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=color, offset=0),
                alt.GradientStop(color=color, offset=1),
            ],
            x1=1, x2=1, y1=1, y2=0,
        ),
        opacity=0.16,
    ).encode(x=x, y=y)

    line = base.mark_line(
        color=color, strokeWidth=2, strokeCap="round", strokeJoin="round",
    ).encode(x=x, y=y)

    hover = alt.selection_point(
        fields=["timestamp"], nearest=True, on="pointerover", empty=False, clear="pointerout",
    )

    # Invisible wide hit target — hover works anywhere on the plot, not just on the line.
    hit = base.mark_rule(opacity=0).encode(
        x=x,
        tooltip=[
            alt.Tooltip("timestamp:T", title="Run", format="%b %d, %Y"),
            alt.Tooltip("value:Q", title=value_title, format=value_fmt),
        ],
    ).add_params(hover)

    rule = base.mark_rule(color=t["baseline"], strokeWidth=1).encode(x=x).transform_filter(hover)

    dot = base.mark_point(
        color=color, fill=color, size=68, stroke=t["surface"], strokeWidth=2,
    ).encode(x=x, y=y).transform_filter(hover)

    return (
        alt.layer(area, line, rule, hit, dot)
        .properties(height=height)
        .configure_view(stroke=None)
        .configure(background="transparent")
    )
