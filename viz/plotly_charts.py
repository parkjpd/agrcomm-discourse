"""
plotly chart builders for the streamlit dashboard. every function returns a
plotly Figure so the app can drop it straight into st.plotly_chart().

same color palette + event overlay as the matplotlib versions in panels/*.py,
just using plotly so hover / zoom / pan are free.
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


# ============================================================
# deeper-look charts
# ============================================================


def _resample_to_year(share: pd.DataFrame) -> pd.DataFrame:
    """convert quarter-indexed share df to year-indexed by simple mean."""
    if share.empty:
        return share
    out = share.copy()
    out.index = pd.to_datetime(out.index)
    return out.groupby(out.index.year).mean()


def language_year_lines(share: pd.DataFrame, title: str) -> go.Figure:
    """panel 1 at year granularity — line per bucket, not stacked.
    makes the enforcement-framing trend (3% -> 9%) actually visible."""
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    yearly = _resample_to_year(share)
    kw = load_keywords()["buckets"]
    for bucket in ("right_loaded", "left_loaded", "neutral"):
        if bucket not in yearly.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=yearly.index, y=yearly[bucket],
                mode="lines+markers",
                name=kw[bucket]["display"],
                line=dict(color=LANG_COLORS[bucket], width=2.5),
                marker=dict(size=7),
                hovertemplate="%{x} — " + kw[bucket]["display"] + ": %{y:.1%}<extra></extra>",
            )
        )

    # event shapes at year scale
    shapes = []
    for ev in load_events():
        d = datetime.strptime(str(ev["date"])[:10], "%Y-%m-%d")
        cat = ev.get("category", "policy")
        shapes.append(dict(
            type="line", x0=d, x1=d, y0=0, y1=1, yref="paper",
            line=dict(color=CATEGORY_COLORS.get(cat, "#555"), width=1,
                      dash=CATEGORY_DASH.get(cat, "dash")),
            opacity=0.4,
        ))

    fig.update_layout(
        title=title,
        xaxis_title="year",
        yaxis_title="share of that year's farm-labor coverage",
        yaxis=dict(tickformat=".0%"),
        hovermode="x unified",
        shapes=shapes,
        height=420,
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


def framing_year_heatmap(share: pd.DataFrame, title: str) -> go.Figure:
    """news language as a heatmap: row per framing, column per year.
    viridis with framing on y so you can scan across years."""
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    kw = load_keywords()["buckets"]
    yearly = _resample_to_year(share)
    rows = [b for b in ("right_loaded", "left_loaded", "neutral") if b in yearly.columns]
    labels = [kw[b]["display"] for b in rows]
    z = yearly[rows].T.values
    x_labels = yearly.index.astype(int).tolist()

    fig.add_trace(go.Heatmap(
        z=z, x=x_labels, y=labels,
        colorscale="YlOrRd",
        colorbar=dict(title="share", tickformat=".0%"),
        hovertemplate="%{y} — %{x}: %{z:.1%}<extra></extra>",
        zmin=0,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="year",
        height=260,
        margin=dict(t=60, b=40, l=180, r=20),
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def stance_year_heatmap(share: pd.DataFrame, title: str) -> go.Figure:
    """reddit stance as a heatmap: row per stance, column per year."""
    fig = go.Figure()
    if share.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    yearly = _resample_to_year(share)
    display = {
        "pro_enforcement": "pro-enforcement",
        "pro_immigrant_labor": "pro-immigrant-labor",
        "neutral_mixed": "neutral / mixed",
    }
    rows = [s for s in ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed") if s in yearly.columns]
    labels = [display[r] for r in rows]
    z = yearly[rows].T.values
    x_labels = yearly.index.astype(int).tolist()

    fig.add_trace(go.Heatmap(
        z=z, x=x_labels, y=labels,
        colorscale="RdBu_r",
        zmid=0.33,
        colorbar=dict(title="share", tickformat=".0%"),
        hovertemplate="%{y} — %{x}: %{z:.1%}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="year",
        height=260,
        margin=dict(t=60, b=40, l=180, r=20),
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def volume_over_time(news_monthly: pd.Series, reddit_monthly: pd.Series, title: str) -> go.Figure:
    """discourse volume: how MUCH people are talking, month by month.
    two traces (news articles, reddit posts) on a shared axis. peaks near events = evidence of engagement.
    both inputs are pd.Series indexed by pd.Period('M') or pd.Timestamp."""
    fig = go.Figure()

    def _to_timestamp_index(s: pd.Series) -> pd.Series:
        if s is None or len(s) == 0:
            return pd.Series(dtype=float)
        if isinstance(s.index, pd.PeriodIndex):
            s = s.copy()
            s.index = s.index.to_timestamp()
        return s.sort_index()

    news_m = _to_timestamp_index(news_monthly)
    reddit_m = _to_timestamp_index(reddit_monthly)

    if news_m.empty and reddit_m.empty:
        fig.add_annotation(text="no volume data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    if not news_m.empty:
        fig.add_trace(go.Scatter(
            x=news_m.index, y=news_m.values,
            mode="lines", name="news articles / month",
            line=dict(color="#2e75b6", width=2),
            fill="tozeroy", fillcolor="rgba(46,117,182,0.15)",
            hovertemplate="%{x|%Y-%m} — %{y:,.0f} articles<extra></extra>",
        ))
    if not reddit_m.empty:
        fig.add_trace(go.Scatter(
            x=reddit_m.index, y=reddit_m.values,
            mode="lines", name="reddit posts / month",
            line=dict(color="#c23b22", width=2),
            yaxis="y2",
            hovertemplate="%{x|%Y-%m} — %{y:,.0f} posts<extra></extra>",
        ))

    shapes, annotations = _event_shapes(y_min=0, y_max=1, yref="paper")
    fig.update_layout(
        title=title,
        xaxis_title="month",
        yaxis=dict(title="news articles per month", side="left"),
        yaxis2=dict(title="reddit posts per month", side="right", overlaying="y"),
        hovermode="x unified",
        shapes=shapes, annotations=annotations,
        height=420,
        margin=dict(t=90, b=40, l=60, r=60),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


def event_discourse_waterfall(news_share: pd.DataFrame, window_days: int = 90, title: str = "") -> go.Figure:
    """for each event, compute change in enforcement-framing share: mean(post window) - mean(pre window).
    horizontal bar chart, sorted by magnitude. red = enforcement framing rose after event."""
    fig = go.Figure()
    if news_share.empty or "right_loaded" in news_share.columns is False:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    idx = pd.to_datetime(news_share.index)
    enf = news_share["right_loaded"] if "right_loaded" in news_share.columns else None
    if enf is None:
        fig.add_annotation(text="no enforcement column", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig
    enf = enf.copy()
    enf.index = idx

    rows = []
    for ev in load_events():
        d = datetime.strptime(str(ev["date"])[:10], "%Y-%m-%d")
        pre_mask = (enf.index >= d - pd.Timedelta(days=window_days)) & (enf.index < d)
        post_mask = (enf.index >= d) & (enf.index <= d + pd.Timedelta(days=window_days))
        pre = enf[pre_mask].mean() if pre_mask.any() else float("nan")
        post = enf[post_mask].mean() if post_mask.any() else float("nan")
        if pd.isna(pre) or pd.isna(post):
            continue
        rows.append({"event": ev["shown"], "date": d, "delta": post - pre, "category": ev.get("category", "policy")})

    if not rows:
        fig.add_annotation(text="no pre/post windows computable", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    df = pd.DataFrame(rows).sort_values("delta")
    colors = ["#c23b22" if d > 0 else "#2e75b6" for d in df["delta"]]
    labels = [f"{e}  ({d.strftime('%Y-%m')})" for e, d in zip(df["event"], df["date"])]

    fig.add_trace(go.Bar(
        x=df["delta"] * 100, y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v*100:+.1f} pp" for v in df["delta"]],
        textposition="outside",
        hovertemplate="%{y}<br>change: %{x:+.2f} pp<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="#333", line_width=1)
    fig.update_layout(
        title=title,
        xaxis_title=f"change in enforcement-framing share  ({window_days}d after − {window_days}d before, percentage points)",
        height=max(320, 28 * len(df) + 100),
        margin=dict(t=60, b=60, l=280, r=60),
        showlegend=False,
    )
    return fig


def stance_topic_sankey(reddit_raw: pd.DataFrame, title: str) -> go.Figure:
    """flow diagram: stance (left) -> topic (right). width = # posts.
    makes 'which topics drive which stance' legible in one glance."""
    fig = go.Figure()
    if reddit_raw is None or reddit_raw.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    df = reddit_raw.copy()
    if "stance" not in df.columns:
        fig.add_annotation(text="no stance column", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    topic_col = "true_topic" if "true_topic" in df.columns and df["true_topic"].notna().any() else None
    if topic_col is None:
        fig.add_annotation(text="no topic column", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    df = df.dropna(subset=["stance", topic_col])
    crosstab = pd.crosstab(df["stance"], df[topic_col])
    stances = list(crosstab.index)
    topics = list(crosstab.columns)
    stance_display = {"pro_enforcement": "pro-enforcement", "pro_immigrant_labor": "pro-immigrant-labor", "neutral_mixed": "neutral / mixed"}
    topic_display = {
        "enforcement": "ICE / enforcement", "border": "border", "deportation": "deportation",
        "criminal": "criminal framing", "economic": "economic", "cropLoss": "crop loss",
        "essential": "essential worker", "humanitarian": "humanitarian",
    }

    labels = [stance_display.get(s, s) for s in stances] + [topic_display.get(t, t) for t in topics]
    stance_colors_map = [STANCE_COLORS.get(s, "#999") for s in stances]
    topic_color = "#777"
    node_colors = stance_colors_map + [topic_color] * len(topics)

    sources, targets, values, link_colors = [], [], [], []
    for i, s in enumerate(stances):
        for j, t in enumerate(topics):
            v = int(crosstab.loc[s, t])
            if v == 0:
                continue
            sources.append(i)
            targets.append(len(stances) + j)
            values.append(v)
            base = STANCE_COLORS.get(s, "#999")
            link_colors.append(_rgba_from_hex(base, 0.35))

    fig.add_trace(go.Sankey(
        node=dict(pad=18, thickness=16, line=dict(color="#333", width=0.5),
                  label=labels, color=node_colors),
        link=dict(source=sources, target=targets, value=values, color=link_colors,
                  hovertemplate="%{source.label} → %{target.label}: %{value:,} posts<extra></extra>"),
    ))
    fig.update_layout(title=title, height=480, margin=dict(t=60, b=20, l=20, r=20))
    return fig


def _rgba_from_hex(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def platform_stance_comparison(dfs_by_platform: dict[str, pd.DataFrame], title: str, stance_col: str = "true_stance") -> go.Figure:
    """grouped bar chart comparing stance mix across platforms.
    dfs_by_platform: {'reddit': df, 'fb_ads': df, 'youtube': df}.
    every df must have a `stance_col` column."""
    fig = go.Figure()
    if not dfs_by_platform:
        fig.add_annotation(text="no platforms", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    stances = ["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"]
    display = {"pro_enforcement": "🟥 pro-enforcement", "pro_immigrant_labor": "🟦 pro-labor", "neutral_mixed": "⬜ neutral / mixed"}

    platforms = list(dfs_by_platform.keys())
    for stance in stances:
        shares = []
        for p in platforms:
            df = dfs_by_platform[p]
            if df is None or df.empty or stance_col not in df.columns:
                shares.append(0)
                continue
            sub = df.dropna(subset=[stance_col])
            if sub.empty:
                shares.append(0)
                continue
            shares.append((sub[stance_col] == stance).mean())
        fig.add_trace(go.Bar(
            x=platforms, y=shares,
            name=display[stance],
            marker_color=STANCE_COLORS[stance],
            text=[f"{v:.0%}" for v in shares],
            textposition="outside",
            hovertemplate="%{x} — " + display[stance] + ": %{y:.1%}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        barmode="group",
        yaxis=dict(tickformat=".0%", range=[0, 1]),
        height=420,
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


def platform_volume_over_time(monthly_by_platform: dict[str, pd.Series], title: str) -> go.Figure:
    """multi-line chart: one line per platform showing posts/articles/comments per month.
    normalized to each platform's own max so we can compare shape, not absolute size."""
    fig = go.Figure()
    if not monthly_by_platform:
        fig.add_annotation(text="no platforms", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    platform_colors = {
        "news": "#2e75b6",
        "reddit": "#c23b22",
        "fb_ads": "#1877f2",
        "youtube": "#ff0000",
    }

    for platform, series in monthly_by_platform.items():
        if series is None or len(series) == 0:
            continue
        s = series.copy().sort_index()
        if isinstance(s.index, pd.PeriodIndex):
            s.index = s.index.to_timestamp()
        denom = s.max() if s.max() > 0 else 1
        normalized = s / denom
        fig.add_trace(go.Scatter(
            x=s.index, y=normalized,
            mode="lines",
            name=platform,
            line=dict(color=platform_colors.get(platform, "#888"), width=2),
            hovertemplate="%{x|%Y-%m} — " + platform + ": %{y:.0%} of that platform's peak<extra></extra>",
        ))

    shapes, annotations = _event_shapes(y_min=0, y_max=1, yref="paper")
    fig.update_layout(
        title=title,
        xaxis_title="month",
        yaxis=dict(title="volume as share of platform's peak month", tickformat=".0%", range=[0, 1.05]),
        hovermode="x unified",
        shapes=shapes, annotations=annotations,
        height=440,
        margin=dict(t=90, b=40, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0),
    )
    return fig


def top_entities_by_stance(df: pd.DataFrame, entity_col: str, title: str, top_n: int = 10, stance_col: str = "true_stance") -> go.Figure:
    """horizontal stacked bar: top N entities (fb sponsors or yt channels) by post count,
    stacked by stance. shows who's pushing which side."""
    fig = go.Figure()
    if df is None or df.empty or entity_col not in df.columns:
        fig.add_annotation(text=f"no {entity_col}", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    d = df.dropna(subset=[entity_col, stance_col]).copy()
    if d.empty:
        fig.add_annotation(text="no labeled rows", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    top = d[entity_col].value_counts().head(top_n).index.tolist()
    d = d[d[entity_col].isin(top)]
    crosstab = pd.crosstab(d[entity_col], d[stance_col])
    crosstab = crosstab.loc[top]
    for s in ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed"):
        if s not in crosstab.columns:
            crosstab[s] = 0
    crosstab = crosstab[["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"]]
    # sort so the highest pro-enforcement share is at the top (most polarized)
    totals = crosstab.sum(axis=1).replace(0, 1)
    enf_share = crosstab["pro_enforcement"] / totals
    order = enf_share.sort_values(ascending=True).index.tolist()
    crosstab = crosstab.loc[order]

    display = {"pro_enforcement": "🟥 pro-enforcement", "pro_immigrant_labor": "🟦 pro-labor", "neutral_mixed": "⬜ neutral / mixed"}
    for stance in ("pro_enforcement", "pro_immigrant_labor", "neutral_mixed"):
        fig.add_trace(go.Bar(
            y=crosstab.index, x=crosstab[stance],
            name=display[stance],
            orientation="h",
            marker_color=STANCE_COLORS[stance],
            hovertemplate="%{y}<br>" + display[stance] + ": %{x} posts<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        barmode="stack",
        xaxis_title="posts / ads / comments",
        height=max(380, 30 * len(crosstab) + 120),
        margin=dict(t=60, b=60, l=280, r=40),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="left", x=0),
    )
    return fig


def discourse_sensitivity_scatter(sens: pd.DataFrame, title: str) -> go.Figure:
    """scatter: x = labor exposure (0-1), y = correlation between enforcement framing and
    60d forward return. labor-heavy commodities should land in the lower-right (high exposure,
    negative correlation). mechanized baselines should hover near zero."""
    fig = go.Figure()
    if sens is None or sens.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    display = {
        "FCOJ": "FCOJ (orange juice)", "milk_class_iii": "class III milk",
        "sugar_11": "sugar #11", "coffee": "coffee", "cotton": "cotton",
        "live_cattle": "live cattle", "soybeans": "soybeans (baseline)",
        "corn_baseline": "corn (baseline)",
    }
    colors = {
        "FCOJ":           "#e76f51", "milk_class_iii": "#2a9d8f",
        "sugar_11":       "#e9c46a", "coffee":         "#6f4e37",
        "cotton":         "#cbd5e8", "live_cattle":    "#8b5a2b",
        "soybeans":       "#aaaaaa", "corn_baseline":  "#888888",
    }

    for _, row in sens.iterrows():
        t = row["ticker"]
        fig.add_trace(go.Scatter(
            x=[row["labor_exposure"]], y=[row["corr_pearson"]],
            mode="markers+text",
            name=display.get(t, t),
            marker=dict(size=18, color=colors.get(t, "#888"), line=dict(color="#222", width=1)),
            text=[display.get(t, t)],
            textposition="top center",
            textfont=dict(size=10),
            hovertemplate=(
                f"{display.get(t, t)}<br>"
                f"labor exposure: {row['labor_exposure']:.2f}<br>"
                f"correlation: {row['corr_pearson']:+.3f}<br>"
                f"n days: {row['n_obs']:,}<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.add_hline(y=0, line_color="#999", line_width=1, line_dash="dash")
    fig.update_layout(
        title=title,
        xaxis=dict(title="migrant-labor exposure (0 = mechanized, 1 = all hand-picked)", range=[-0.05, 1.05]),
        yaxis=dict(title="correlation of enforcement framing with 60-day forward return"),
        height=500,
        margin=dict(t=60, b=60, l=60, r=40),
    )
    return fig


def regime_returns_chart(regime: pd.DataFrame, title: str) -> go.Figure:
    """grouped bar: for each ticker, annualized return in high-enforcement quarters vs low.
    commodities where the blue bar (low-enforcement) beats the red bar (high) are
    underperforming when enforcement talk is loud."""
    fig = go.Figure()
    if regime is None or regime.empty:
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    display = {
        "FCOJ": "FCOJ", "milk_class_iii": "class III milk",
        "sugar_11": "sugar #11", "coffee": "coffee", "cotton": "cotton",
        "live_cattle": "live cattle", "soybeans": "soybeans",
        "corn_baseline": "corn",
    }
    regime = regime.copy().sort_values("labor_exposure", ascending=False)
    labels = [display.get(t, t) for t in regime["ticker"]]

    fig.add_trace(go.Bar(
        x=labels, y=regime["annualized_return_high_enf"] * 100,
        name="high enforcement-framing quarters",
        marker_color="#c23b22",
        text=[f"{v*100:+.1f}%" for v in regime["annualized_return_high_enf"]],
        textposition="outside",
        hovertemplate="%{x}<br>high enf: %{y:.1f}% annualized<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=labels, y=regime["annualized_return_low_enf"] * 100,
        name="low enforcement-framing quarters",
        marker_color="#2e75b6",
        text=[f"{v*100:+.1f}%" for v in regime["annualized_return_low_enf"]],
        textposition="outside",
        hovertemplate="%{x}<br>low enf: %{y:.1f}% annualized<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        barmode="group",
        xaxis_title="commodity (sorted by labor exposure, highest on left)",
        yaxis=dict(title="annualized return (%)", ticksuffix="%"),
        height=440,
        margin=dict(t=60, b=60, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
    )
    fig.add_hline(y=0, line_color="#333", line_width=1)
    return fig


def fcoj_deep_dive(fcoj_daily: pd.DataFrame, enf_daily: pd.Series, events: list, title: str) -> go.Figure:
    """dual-axis time series for FCOJ (left axis, price) + enforcement-framing share (right axis, %).
    highlights the jan 2025 mass deportation event with a callout.
    fcoj_daily: df with date, close. enf_daily: series indexed by date."""
    fig = go.Figure()
    if fcoj_daily is None or fcoj_daily.empty:
        fig.add_annotation(text="no FCOJ data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    fd = fcoj_daily.copy()
    fd["date"] = pd.to_datetime(fd["date"])
    fd = fd.sort_values("date")
    fig.add_trace(go.Scatter(
        x=fd["date"], y=fd["close"],
        mode="lines", name="FCOJ close (USD/lb)",
        line=dict(color="#e76f51", width=2),
        yaxis="y1",
        hovertemplate="%{x|%Y-%m-%d} — FCOJ: $%{y:.2f}<extra></extra>",
    ))

    if enf_daily is not None and len(enf_daily) > 0:
        ed = enf_daily.copy()
        if not isinstance(ed.index, pd.DatetimeIndex):
            ed.index = pd.to_datetime(ed.index)
        fig.add_trace(go.Scatter(
            x=ed.index, y=ed.values * 100,
            mode="lines", name="news enforcement framing (%)",
            line=dict(color="#c23b22", width=1.2, dash="dash"),
            fill="tozeroy", fillcolor="rgba(194,59,34,0.12)",
            yaxis="y2",
            hovertemplate="%{x|%Y-%m-%d} — enforcement framing: %{y:.1f}%<extra></extra>",
        ))

    # overlay event markers (other events dimmed so jan 2025 pops)
    jan25 = datetime(2025, 1, 20)
    for ev in events:
        d = datetime.strptime(str(ev["date"])[:10], "%Y-%m-%d")
        if d == jan25:
            continue  # drawn separately below with heavy emphasis
        cat = ev.get("category", "policy")
        fig.add_vline(
            x=d, line_color=CATEGORY_COLORS.get(cat, "#555"),
            line_width=1.0,
            line_dash=CATEGORY_DASH.get(cat, "dash"),
            opacity=0.3,
        )

    # jan 2025 gets a fat scarlet band + solid vline so the eye lands there first
    fig.add_vrect(
        x0=datetime(2025, 1, 10), x1=datetime(2025, 2, 20),
        fillcolor="#c23b22", opacity=0.14, line_width=0, layer="below",
    )
    fig.add_vline(
        x=jan25, line_color="#bb0000", line_width=3, opacity=0.9,
    )

    # big, unmissable callout in scarlet fill with white bold text
    fig.add_annotation(
        x=jan25, y=1.02, yref="paper",
        text="<b>Jan 2025 — mass deportation ops begin</b><br>FCOJ -35% in 30 days",
        showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=2.5,
        arrowcolor="#bb0000",
        ax=-140, ay=-55,
        align="center",
        font=dict(size=15, color="#ffffff", family="DM Sans, Helvetica, sans-serif"),
        bgcolor="#bb0000", bordercolor="#7a0000", borderwidth=2,
        borderpad=8,
    )

    fig.update_layout(
        title=title,
        xaxis_title="year",
        yaxis=dict(title="FCOJ close price (USD/lb)", side="left"),
        yaxis2=dict(title="news enforcement framing (%)", overlaying="y", side="right", tickformat=".0f", ticksuffix="%"),
        hovermode="x unified",
        height=500,
        margin=dict(t=90, b=40, l=60, r=60),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0),
    )
    return fig


def subreddit_small_multiples(reddit_raw: pd.DataFrame, title: str, top_n: int = 6) -> go.Figure:
    """one mini stacked-bar per subreddit showing stance mix across eras.
    helps see whether the trump-era jump is universal or driven by a few subs."""
    if reddit_raw is None or reddit_raw.empty or "stance" not in reddit_raw.columns or "subreddit" not in reddit_raw.columns:
        fig = go.Figure()
        fig.add_annotation(text="no data", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    df = reddit_raw.copy()
    df = df.dropna(subset=["stance", "subreddit"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    eras = [
        ("Obama 2", "2010-01-01", "2016-10-31"),
        ("Trump 1", "2016-11-01", "2020-02-29"),
        ("COVID",   "2020-03-01", "2021-01-19"),
        ("Biden",   "2021-01-20", "2024-11-04"),
        ("Trump 2", "2024-11-05", "2026-12-31"),
    ]
    era_starts = {n: pd.Timestamp(s) for n, s, _ in eras}
    era_ends = {n: pd.Timestamp(e) for n, _, e in eras}

    def era_of(d):
        for name, s, e in eras:
            if pd.Timestamp(s) <= d <= pd.Timestamp(e):
                return name
        return None
    df["era"] = df["date"].map(era_of)
    df = df.dropna(subset=["era"])

    top_subs = df["subreddit"].value_counts().head(top_n).index.tolist()
    if not top_subs:
        fig = go.Figure()
        fig.add_annotation(text="no subs", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
        fig.update_layout(title=title)
        return fig

    rows = (len(top_subs) + 2) // 3
    cols = 3
    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[f"r/{s}" for s in top_subs],
        horizontal_spacing=0.08, vertical_spacing=0.18,
    )

    stance_order = ["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"]
    era_order = [n for n, _, _ in eras]
    for i, sub in enumerate(top_subs):
        r, c = i // cols + 1, i % cols + 1
        sd = df[df["subreddit"] == sub]
        ct = pd.crosstab(sd["era"], sd["stance"])
        ct = ct.reindex(index=era_order, columns=stance_order, fill_value=0)
        tot = ct.sum(axis=1).replace(0, 1)
        share = ct.div(tot, axis=0)
        for stance in stance_order:
            fig.add_trace(
                go.Bar(
                    x=share.index, y=share[stance],
                    name=stance.replace("_", " "),
                    marker_color=STANCE_COLORS[stance],
                    showlegend=(i == 0),
                    legendgroup=stance,
                    hovertemplate=f"r/{sub} — %{{x}}<br>{stance}: %{{y:.1%}}<extra></extra>",
                ),
                row=r, col=c,
            )

    fig.update_layout(
        title=title,
        barmode="stack",
        height=280 * rows + 80,
        margin=dict(t=80, b=60, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="left", x=0),
    )
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    return fig
