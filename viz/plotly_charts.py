"""
plotly chart builders for the streamlit dashboard. return plotly figures so the
streamlit app can display them interactively.

parallels the matplotlib builders in panels/*.py but uses plotly so hover, zoom,
pan, and event-tooltip interactions work out of the box.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common import load_events, load_keywords

# same color palette as the matplotlib version so outputs are consistent
LANG_COLORS = {"right_loaded": "#c23b22", "left_loaded": "#2e75b6", "neutral": "#7f7f7f"}
STANCE_COLORS = {"pro_enforcement": "#c23b22", "pro_immigrant_labor": "#2e75b6", "neutral_mixed": "#bfbfbf"}

CATEGORY_COLORS = {
    "election":    "#111111",
    "enforcement": "#c23b22",
    "pandemic":    "#2a9d8f",
    "legal":       "#6b4b9a",
    "policy":      "#555555",
}
CATEGORY_DASH = {
    "election": "solid", "enforcement": "dash", "pandemic": "dash",
    "legal": "dash", "policy": "dot",
}


def _event_shapes(y_min: float = 0, y_max: float = 1, yref: str = "paper"):
    """vertical lines + hover annotations for every policy event."""
    shapes = []
    annotations = []
    for ev in load_events():
        d = datetime.strptime(str(ev["date"])[:10], "%Y-%m-%d")
        cat = ev.get("category", "policy")
        shapes.append(
            dict(
                type="line",
                x0=d, x1=d,
                y0=y_min, y1=y_max,
                yref=yref,
                line=dict(
                    color=CATEGORY_COLORS.get(cat, "#555"),
                    width=1.2 if cat == "election" else 1.0,
                    dash=CATEGORY_DASH.get(cat, "dash"),
                ),
                opacity=0.8 if cat == "election" else 0.65,
            )
        )
        annotations.append(
            dict(
                x=d,
                y=1.02,
                yref=yref,
                showarrow=False,
                text=ev["shown"],
                textangle=-90,
                xanchor="left",
                yanchor="bottom",
                font=dict(size=9, color="#222"),
                hovertext=ev.get("note", ev["shown"]) + f"<br>{ev['date']}",
                bgcolor="rgba(255,255,255,0.8)",
            )
        )
    return shapes, annotations


# ---------- panel 1: language share ----------

def language_stacked_area(share: pd.DataFrame, title: str, mode: str = "share") -> go.Figure:
    """share is a df with index=date. columns are either bucket shares (mode='share')
    or raw counts (mode='volume'). mode controls y-axis formatting."""
    kw = load_keywords()["buckets"]
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    for bucket in ("right_loaded", "left_loaded", "neutral"):
        if bucket not in share.columns:
            continue
        hover = "%{x|%Y-Q%q} — " + kw[bucket]["display"] + (": %{y:.1%}<extra></extra>" if mode == "share" else ": %{y:,.0f} articles<extra></extra>")
        fig.add_trace(
            go.Scatter(
                x=share.index,
                y=share[bucket],
                mode="lines",
                stackgroup="one",
                name=kw[bucket]["display"],
                line=dict(width=0.5, color=LANG_COLORS[bucket]),
                fillcolor=LANG_COLORS[bucket],
                hovertemplate=hover,
            )
        )

    shapes, annotations = _event_shapes()
    y_conf = dict(tickformat=".0%", range=[0, 1]) if mode == "share" else dict(tickformat=",.0f", title="articles")
    fig.update_layout(
        title=title,
        xaxis_title="year",
        yaxis_title="share of mentions" if mode == "share" else "article volume",
        yaxis=y_conf,
        hovermode="x unified",
        shapes=shapes,
        annotations=annotations,
        height=400,
        margin=dict(t=90, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


# ---------- panel 2: stance mix ----------

def stance_stacked_area(share: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    for label in ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed"):
        if label not in share.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=share.index,
                y=share[label],
                mode="lines",
                stackgroup="one",
                name=label.replace("_", " "),
                line=dict(width=0.5, color=STANCE_COLORS[label]),
                fillcolor=STANCE_COLORS[label],
                hovertemplate="%{x|%Y-Q%q} — " + label + ": %{y:.1%}<extra></extra>",
            )
        )

    shapes, annotations = _event_shapes()
    fig.update_layout(
        title=title,
        xaxis_title="year",
        yaxis_title="share of posts",
        yaxis=dict(tickformat=".0%", range=[0, 1]),
        hovermode="x unified",
        shapes=shapes,
        annotations=annotations,
        height=400,
        margin=dict(t=90, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


# ---------- panel 3: topic heatmap ----------

TOPIC_DISPLAY = {
    "enforcement":   "ICE / workplace enforcement",
    "border":        "border / migration flow",
    "deportation":   "deportation operations",
    "criminal":      "criminal framing",
    "economic":      "economic contribution",
    "cropLoss":      "crop loss / labor shortage",
    "essential":     "essential worker framing",
    "humanitarian":  "humanitarian / families",
}


def topic_heatmap(share: pd.DataFrame, title: str) -> go.Figure:
    """share is df with rows=topics, columns=years."""
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no topics", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    ylabels = [TOPIC_DISPLAY.get(t, t) for t in share.index]
    years = share.columns.astype(int).tolist()
    x_centers = [datetime(y, 7, 1) for y in years]

    fig.add_trace(
        go.Heatmap(
            z=share.values,
            x=x_centers,
            y=ylabels,
            colorscale="Viridis",
            colorbar=dict(title="share of year"),
            hovertemplate="%{y} — %{x|%Y}: %{z:.1%}<extra></extra>",
        )
    )

    shapes, annotations = _event_shapes()
    fig.update_layout(
        title=title,
        xaxis_title="year",
        shapes=shapes,
        annotations=annotations,
        height=450,
        margin=dict(t=90, b=40, l=180, r=20),
    )
    fig.update_yaxes(autorange="reversed")
    return fig


# ---------- combined three-panel ----------

def three_panel(news_share: pd.DataFrame, stance_share: pd.DataFrame, topic_share: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        subplot_titles=("panel 1 — language share (news)", "panel 2 — stance mix (reddit)", "panel 3 — topic prevalence"),
        row_heights=[0.3, 0.3, 0.4],
    )
    kw = load_keywords()["buckets"]

    # panel 1
    if not news_share.empty:
        for bucket in ("right_loaded", "left_loaded", "neutral"):
            if bucket not in news_share.columns:
                continue
            fig.add_trace(
                go.Scatter(
                    x=news_share.index, y=news_share[bucket], mode="lines",
                    stackgroup="one_lang", name=kw[bucket]["display"],
                    line=dict(width=0.5, color=LANG_COLORS[bucket]),
                    fillcolor=LANG_COLORS[bucket], legendgroup="lang",
                ),
                row=1, col=1,
            )

    # panel 2
    if not stance_share.empty:
        for label in ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed"):
            if label not in stance_share.columns:
                continue
            fig.add_trace(
                go.Scatter(
                    x=stance_share.index, y=stance_share[label], mode="lines",
                    stackgroup="one_stance", name=label.replace("_", " "),
                    line=dict(width=0.5, color=STANCE_COLORS[label]),
                    fillcolor=STANCE_COLORS[label], legendgroup="stance",
                ),
                row=2, col=1,
            )

    # panel 3
    if not topic_share.empty:
        years = topic_share.columns.astype(int).tolist()
        x_centers = [datetime(y, 7, 1) for y in years]
        fig.add_trace(
            go.Heatmap(
                z=topic_share.values,
                x=x_centers,
                y=[TOPIC_DISPLAY.get(t, t) for t in topic_share.index],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="share", len=0.35, y=0.18),
                hovertemplate="%{y} — %{x|%Y}: %{z:.1%}<extra></extra>",
            ),
            row=3, col=1,
        )

    # events on all three rows
    for ev in load_events():
        d = datetime.strptime(str(ev["date"])[:10], "%Y-%m-%d")
        cat = ev.get("category", "policy")
        color = CATEGORY_COLORS.get(cat, "#555")
        dash = CATEGORY_DASH.get(cat, "dash")
        for row in (1, 2, 3):
            fig.add_vline(
                x=d, line_color=color, line_width=1.0, line_dash=dash,
                opacity=0.7, row=row, col=1,
            )
        # labels only on top row
        fig.add_annotation(
            x=d, y=1.05, yref="y domain", xref="x",
            text=ev["shown"], textangle=-90, xanchor="left", yanchor="bottom",
            showarrow=False, font=dict(size=8), row=1, col=1,
        )

    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=1, col=1)
    fig.update_yaxes(range=[0, 1], tickformat=".0%", row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=3, col=1)
    fig.update_layout(
        height=900,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=80, b=40, l=180, r=30),
    )
    return fig
