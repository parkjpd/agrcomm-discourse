"""
interactive dashboard for the discourse-shift analysis.

run:  streamlit run app.py

tabs:
  overview      combined three-panel plotly figure
  language      panel 1 interactive
  stance        panel 2 interactive + sample posts viewer
  topic         panel 3 interactive + cluster drill-down
  data          raw row explorer
  about         spec summary
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from common import PROCESSED_DIR, SAMPLES_DIR, load_events, load_keywords, load_stance_rubric
from panels.panel1_language import _normalize_to_share, load_news_volumes, load_reddit_volumes
from panels.panel2_stance import LABELS as STANCE_LABELS, aggregate_stance
from panels.panel3_topic import CANONICAL_TOPICS, _prevalence_per_year, load_corpus
from viz import plotly_charts as pc

st.set_page_config(
    page_title="discourse-shift — migrant farm labor 2010-2026",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- caching expensive loads ----------

@st.cache_data(ttl=300)
def _news_share():
    return _normalize_to_share(load_news_volumes())


@st.cache_data(ttl=300)
def _reddit_share_lang():
    return _normalize_to_share(load_reddit_volumes())


@st.cache_data(ttl=300)
def _stance_share():
    p = PROCESSED_DIR / "reddit_posts_stance.csv"
    if not p.exists():
        return pd.DataFrame(), pd.DataFrame()
    df = pd.read_csv(p)
    return aggregate_stance(df), df


@st.cache_data(ttl=300)
def _topic_share():
    corpus = load_corpus()
    if corpus.empty:
        return pd.DataFrame(), pd.DataFrame()
    if "true_topic" in corpus.columns and corpus["true_topic"].notna().any():
        share = _prevalence_per_year(corpus, "true_topic")
        return share, corpus
    from panels.panel3_topic import _rule_based_topic
    corpus = corpus.copy()
    corpus["topic"] = corpus["text"].astype(str).map(_rule_based_topic)
    return _prevalence_per_year(corpus, "topic"), corpus


def _filter_by_year(df, start_year: int, end_year: int, date_col: str = "date"):
    if df.empty or date_col not in df.columns:
        return df
    d = pd.to_datetime(df[date_col])
    return df[(d.dt.year >= start_year) & (d.dt.year <= end_year)]


# ---------- sidebar ----------

with st.sidebar:
    st.header("controls")
    year_range = st.slider("year range", 2010, 2026, (2010, 2026), step=1)
    st.caption("filters all four tabs")

    st.divider()
    st.subheader("data status")

    news_vols = load_news_volumes()
    if not news_vols.empty:
        srcs = news_vols["source"].value_counts().to_dict()
        for src, n in srcs.items():
            st.write(f"• news — **{src}**: {n:,} rows")
    reddit_vols = load_reddit_volumes()
    if not reddit_vols.empty:
        st.write(f"• reddit posts: {reddit_vols['count'].sum():,} matched")

    stance_path = PROCESSED_DIR / "reddit_posts_stance.csv"
    if stance_path.exists():
        n = sum(1 for _ in open(stance_path)) - 1
        st.write(f"• stance-labeled: {n:,} posts")

    st.divider()
    st.caption(
        "event colors:\n"
        "• ⬛ election (solid)\n"
        "• 🟥 enforcement (dashed)\n"
        "• 🟩 pandemic (dashed)\n"
        "• 🟪 legal (dashed)"
    )


# ---------- header ----------

st.title("public discourse on migrant farm labor, 2010–2026")
st.caption("AGRCOMM 2330 case study — language / stance / topic panels with policy event overlay")

# data-source badges showing what's real vs synthetic
def _data_badges():
    badges = []
    if (PROCESSED_DIR / "panel1_news_volumes_mc.csv").exists():
        badges.append(("news (panel 1)", "live media cloud · 2010-2026", True))
    else:
        badges.append(("news (panel 1)", "synthetic", False))

    stance_path = PROCESSED_DIR / "reddit_posts_stance.csv"
    if stance_path.exists():
        try:
            n = sum(1 for _ in open(stance_path)) - 1
            # check if any row was haiku-classified (vs truth labels)
            sample = pd.read_csv(stance_path, nrows=5)
            is_live = "stance" in sample.columns and sample["stance"].notna().any()
            badges.append(("stance (panel 2)", f"haiku · {n} posts" if is_live else f"synthetic · {n} posts", is_live))
        except Exception:
            badges.append(("stance (panel 2)", "unknown", False))
    else:
        badges.append(("stance (panel 2)", "synthetic", False))

    corpus = load_corpus()
    if not corpus.empty and "true_topic" in corpus.columns:
        badges.append(("topic (panel 3)", f"synthetic truth · {len(corpus):,} docs", False))
    else:
        badges.append(("topic (panel 3)", "—", False))

    if (PROCESSED_DIR / "panel4_futures_quarterly.csv").exists():
        badges.append(("futures (panel 4)", "live yfinance · 5 tickers", True))
    else:
        badges.append(("futures (panel 4)", "—", False))
    return badges

_badge_cols = st.columns(4)
for col, (label, detail, is_live) in zip(_badge_cols, _data_badges()):
    with col:
        icon = "🟢" if is_live else "🟡"
        st.markdown(f"**{icon} {label}**  \n`{detail}`")


# ---------- tabs ----------

tab_over, tab_lang, tab_stance, tab_topic, tab_futures, tab_data, tab_about = st.tabs(
    ["overview", "panel 1 — language", "panel 2 — stance", "panel 3 — topic", "panel 4 — futures (bonus)", "data", "about"]
)


# ===== overview =====

with tab_over:
    news = _news_share()
    reddit_stance, _ = _stance_share()
    topic, _ = _topic_share()

    # year-slice
    news_s = news.loc[(news.index.year >= year_range[0]) & (news.index.year <= year_range[1])] if not news.empty else news
    stance_s = reddit_stance.loc[(reddit_stance.index.year >= year_range[0]) & (reddit_stance.index.year <= year_range[1])] if not reddit_stance.empty else reddit_stance
    topic_s = topic.loc[:, [c for c in topic.columns if year_range[0] <= int(c) <= year_range[1]]] if not topic.empty else topic

    fig = pc.three_panel(news_s, stance_s, topic_s)
    st.plotly_chart(fig, width="stretch")

    # download buttons for the static presentation assets
    dcol1, dcol2, dcol3 = st.columns(3)
    from pathlib import Path as _P
    tp_png = _P("output/three_panel.png")
    if tp_png.exists():
        with dcol1:
            st.download_button(
                "⬇ combined figure (PNG)",
                data=tp_png.read_bytes(),
                file_name="three_panel.png",
                mime="image/png",
                width="stretch",
            )
    findings_md = _P("output/findings.md")
    if findings_md.exists():
        with dcol2:
            st.download_button(
                "⬇ findings writeup (MD)",
                data=findings_md.read_bytes(),
                file_name="findings.md",
                mime="text/markdown",
                width="stretch",
            )
    stance_csv = PROCESSED_DIR / "reddit_posts_stance.csv"
    if stance_csv.exists():
        with dcol3:
            st.download_button(
                "⬇ haiku-labeled posts (CSV)",
                data=stance_csv.read_bytes(),
                file_name="reddit_posts_stance.csv",
                mime="text/csv",
                width="stretch",
            )

    # --- findings at a glance ---
    st.markdown("##### findings at a glance")
    fc1, fc2, fc3 = st.columns(3)

    def _delta(series, start: str, end: str) -> float | None:
        if series.empty: return None
        sub = series.loc[start:end]
        return float(sub.mean()) if len(sub) else None

    with fc1:
        if not news.empty and "right_loaded" in news.columns:
            pre = _delta(news["right_loaded"], "2010-01-01", "2016-10-31")
            trump1 = _delta(news["right_loaded"], "2016-11-01", "2020-02-29")
            st.metric(
                "news — enforcement framing (trump 1 vs pre)",
                f"{(trump1 or 0):.1%}",
                f"{((trump1 or 0) - (pre or 0)) * 100:+.1f} pp",
                help="mean share of enforcement-framed terms during trump 1 era minus pre-trump era",
            )

    with fc2:
        if not reddit_stance.empty and "pro_enforcement" in reddit_stance.columns:
            covid = _delta(reddit_stance["pro_enforcement"], "2020-03-01", "2021-01-19")
            trump1_s = _delta(reddit_stance["pro_enforcement"], "2016-11-01", "2020-02-29")
            st.metric(
                "reddit — pro-enforcement share (covid vs trump 1)",
                f"{(covid or 0):.1%}",
                f"{((covid or 0) - (trump1_s or 0)) * 100:+.1f} pp",
                help="mean pro-enforcement share during covid era minus trump 1 era",
            )

    with fc3:
        if not topic.empty and "essential" in topic.index:
            essential_covid = float(topic.loc["essential", [c for c in topic.columns if 2020 <= int(c) <= 2020]].mean()) if any(2020 <= int(c) <= 2020 for c in topic.columns) else 0
            essential_pre = float(topic.loc["essential", [c for c in topic.columns if 2015 <= int(c) <= 2019]].mean()) if any(2015 <= int(c) <= 2019 for c in topic.columns) else 0
            st.metric(
                "topic — essential worker framing (2020 vs 2015-19)",
                f"{essential_covid:.1%}",
                f"{(essential_covid - essential_pre) * 100:+.1f} pp",
                help="essential-worker topic prevalence in 2020 minus pre-covid average",
            )

    st.markdown("##### reading the figure")
    st.markdown(
        "- **all three panels share the same x-axis** — event markers align vertically across panels\n"
        "- **panel 1** = what words news uses (news-side only in this view; switch to the panel 1 tab for reddit)\n"
        "- **panel 2** = what positions reddit posts take\n"
        "- **panel 3** = which sub-topics dominate each year\n"
        "- if all three break at the same events → regime-driven discourse. if only some break → mixed pattern."
    )


# ===== panel 1 language =====

with tab_lang:
    col1, col2 = st.columns([3, 1])
    with col2:
        source_choice = st.radio("source", ["news", "reddit", "both"], horizontal=False)
        view_mode = st.radio("view", ["share (%)", "volume (raw)"], horizontal=False, help="share normalizes by total quarterly coverage — use to see framing mix. volume shows raw article counts — use to see total attention.")

    news = _news_share()
    reddit = _reddit_share_lang()

    def _slice(s):
        if s.empty: return s
        return s.loc[(s.index.year >= year_range[0]) & (s.index.year <= year_range[1])]

    news_s = _slice(news)
    reddit_s = _slice(reddit)

    # volume mode: get raw counts (pre-normalization) from load fn
    news_vol = load_news_volumes() if view_mode == "volume (raw)" else None
    reddit_vol = load_reddit_volumes() if view_mode == "volume (raw)" else None

    def _pivot_volume(df):
        if df is None or df.empty:
            return pd.DataFrame()
        d = df.groupby(["date", "bucket"])["count"].sum().reset_index()
        piv = d.pivot(index="date", columns="bucket", values="count").fillna(0)
        for b in ("right_loaded", "left_loaded", "neutral"):
            if b not in piv.columns:
                piv[b] = 0
        piv.index = pd.to_datetime(piv.index)
        piv = piv.sort_index()
        return piv.loc[(piv.index.year >= year_range[0]) & (piv.index.year <= year_range[1])]

    with col1:
        mode_key = "volume" if view_mode.startswith("volume") else "share"
        if source_choice == "news":
            src = _pivot_volume(news_vol) if mode_key == "volume" else news_s
            st.plotly_chart(pc.language_stacked_area(src, f"language {mode_key} — news", mode=mode_key), width="stretch")
        elif source_choice == "reddit":
            src = _pivot_volume(reddit_vol) if mode_key == "volume" else reddit_s
            st.plotly_chart(pc.language_stacked_area(src, f"language {mode_key} — reddit", mode=mode_key), width="stretch")
        else:
            for label, shp, vp in [("news", news_s, news_vol), ("reddit", reddit_s, reddit_vol)]:
                src = _pivot_volume(vp) if mode_key == "volume" else shp
                st.plotly_chart(pc.language_stacked_area(src, f"language {mode_key} — {label}", mode=mode_key), width="stretch")

    # hinge-point table - compare pre vs post for each event
    st.markdown("##### era comparison: enforcement-framed share")
    if not news_s.empty and "right_loaded" in news_s.columns:
        era_rows = []
        eras = [
            ("pre-trump 2010-2016", news_s.loc[:"2016-10-31", "right_loaded"].mean() if len(news_s.loc[:"2016-10-31"]) else None),
            ("trump 1 (2017-2020Q1)", news_s.loc["2016-11-01":"2020-02-29", "right_loaded"].mean() if len(news_s.loc["2016-11-01":"2020-02-29"]) else None),
            ("covid (2020Q2-2020)", news_s.loc["2020-03-01":"2021-01-19", "right_loaded"].mean() if len(news_s.loc["2020-03-01":"2021-01-19"]) else None),
            ("biden (2021-2024Q3)", news_s.loc["2021-01-20":"2024-11-04", "right_loaded"].mean() if len(news_s.loc["2021-01-20":"2024-11-04"]) else None),
            ("trump 2 (2024Q4+)", news_s.loc["2024-11-05":, "right_loaded"].mean() if len(news_s.loc["2024-11-05":]) else None),
        ]
        for era, val in eras:
            era_rows.append({"era": era, "enforcement-framed share": f"{val:.1%}" if val is not None and not pd.isna(val) else "—"})
        st.dataframe(pd.DataFrame(era_rows), width="stretch", hide_index=True)


# ===== panel 2 stance =====

with tab_stance:
    share, raw = _stance_share()

    share_s = share.loc[(share.index.year >= year_range[0]) & (share.index.year <= year_range[1])] if not share.empty else share
    st.plotly_chart(pc.stance_stacked_area(share_s, "stance mix on reddit"), width="stretch")

    if raw.empty:
        st.info("no stance data yet — run `python run.py --only panel2` (demo) or `--live-stance` (haiku) to populate.")
    else:
        st.markdown("##### sample posts by classified stance")
        label_pick = st.selectbox("label", STANCE_LABELS, index=0)
        sub = raw.copy()
        if "date" in sub.columns:
            sub["date"] = pd.to_datetime(sub["date"])
            sub = sub[(sub["date"].dt.year >= year_range[0]) & (sub["date"].dt.year <= year_range[1])]
        sub = sub[sub["stance"] == label_pick].sample(n=min(5, len(sub)), random_state=42) if not sub.empty else sub
        for _, row in sub.iterrows():
            with st.container(border=True):
                meta = []
                if "subreddit" in row and not pd.isna(row["subreddit"]):
                    meta.append(f"r/{row['subreddit']}")
                if "date" in row:
                    meta.append(str(row["date"])[:10])
                st.caption(" · ".join(meta))
                text = str(row.get("text", ""))
                st.write(text[:600] + ("…" if len(text) > 600 else ""))

    # era comparison tool
    if not raw.empty and "stance" in raw.columns:
        st.markdown("##### era comparison")
        st.caption("pick two eras and see how the stance distribution differs — direct answer to 'did the mix shift?'")
        era_options = {
            "pre-trump (2010-2016)":  ("2010-01-01", "2016-10-31"),
            "trump 1 (2017-2020Q1)":  ("2016-11-01", "2020-02-29"),
            "covid (2020Q2-2020)":    ("2020-03-01", "2021-01-19"),
            "biden (2021-2024Q3)":    ("2021-01-20", "2024-11-04"),
            "trump 2 (2024Q4-)":      ("2024-11-05", "2026-12-31"),
        }
        ec1, ec2 = st.columns(2)
        era_a = ec1.selectbox("era A", list(era_options.keys()), index=1, key="era_a")
        era_b = ec2.selectbox("era B", list(era_options.keys()), index=4, key="era_b")

        raw_t = raw.copy()
        if "date" in raw_t.columns:
            raw_t["date"] = pd.to_datetime(raw_t["date"])

        def _dist(key):
            start, end = era_options[key]
            sub = raw_t[(raw_t["date"] >= start) & (raw_t["date"] <= end) & raw_t["stance"].notna()]
            if sub.empty:
                return pd.Series([0, 0, 0], index=list(STANCE_LABELS))
            counts = sub["stance"].value_counts()
            return pd.Series([counts.get(l, 0) for l in STANCE_LABELS], index=list(STANCE_LABELS))

        dist_a = _dist(era_a)
        dist_b = _dist(era_b)
        total_a, total_b = dist_a.sum(), dist_b.sum()
        share_a = (dist_a / total_a).fillna(0) if total_a else dist_a
        share_b = (dist_b / total_b).fillna(0) if total_b else dist_b

        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(STANCE_LABELS), y=share_a.values, name=era_a,
            marker_color=[pc.STANCE_COLORS[l] for l in STANCE_LABELS],
            marker_pattern_shape=".",
            text=[f"{v:.0%}" for v in share_a.values], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            x=list(STANCE_LABELS), y=share_b.values, name=era_b,
            marker_color=[pc.STANCE_COLORS[l] for l in STANCE_LABELS],
            marker_line_color="#000", marker_line_width=2,
            text=[f"{v:.0%}" for v in share_b.values], textposition="outside",
        ))
        fig.update_layout(
            barmode="group",
            yaxis_tickformat=".0%",
            yaxis_range=[0, 1],
            height=380,
            title=f"stance distribution — {era_a} ({total_a:,} posts) vs {era_b} ({total_b:,} posts)",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        )
        st.plotly_chart(fig, width="stretch")

        # delta table
        delta = pd.DataFrame({
            "label": list(STANCE_LABELS),
            f"{era_a}": [f"{v:.1%}" for v in share_a.values],
            f"{era_b}": [f"{v:.1%}" for v in share_b.values],
            "delta (B-A)": [f"{(share_b.values[i] - share_a.values[i]) * 100:+.1f} pp" for i in range(len(STANCE_LABELS))],
        })
        st.dataframe(delta, width="stretch", hide_index=True)

    with st.expander("rubric used by classifier"):
        rub = load_stance_rubric()
        st.write("**pro-enforcement indicators:**")
        for b in rub["pro_enforcement_indicators"]:
            st.markdown(f"- {b}")
        st.write("**pro-immigrant-labor indicators:**")
        for b in rub["pro_immigrant_labor_indicators"]:
            st.markdown(f"- {b}")
        st.write("**neutral / mixed:**")
        for b in rub["neutral_mixed_indicators"]:
            st.markdown(f"- {b}")


# ===== panel 3 topic =====

with tab_topic:
    share, corpus = _topic_share()
    if share.empty:
        st.info("no topic data yet — run `python run.py --only panel3` (demo) or `--live-topic` (bertopic) to populate.")
    else:
        share_s = share.loc[:, [c for c in share.columns if year_range[0] <= int(c) <= year_range[1]]]
        st.plotly_chart(pc.topic_heatmap(share_s, "topic prevalence by year"), width="stretch")

        st.markdown("##### topic over time (line form)")
        picked = st.multiselect(
            "topics",
            options=list(share_s.index),
            default=list(share_s.index)[:4],
        )
        if picked:
            import plotly.graph_objects as go
            fig = go.Figure()
            for t in picked:
                fig.add_trace(go.Scatter(x=share_s.columns.astype(int), y=share_s.loc[t], mode="lines+markers", name=pc.TOPIC_DISPLAY.get(t, t)))
            fig.update_layout(yaxis_tickformat=".0%", xaxis_title="year", yaxis_title="share of year", height=400)
            st.plotly_chart(fig, width="stretch")


# ===== panel 4 futures (bonus) =====

with tab_futures:
    st.markdown("##### bonus — discourse vs agricultural futures")
    st.caption(
        "experimental. overlays ag commodity futures on the enforcement-framed news-share series. "
        "hypothesis: labor-heavy crops (FCOJ, class III milk, sugar) should move with enforcement discourse more than low-labor corn. "
        "see docs/future_work.md for the full research plan."
    )

    try:
        from panels.panel4_futures import (
            LABOR_HEAVY, BASELINE, TICKER_COLORS, TICKER_DISPLAY, TICKERS_ALL,
            _enforcement_share_quarterly, load_futures_quarterly, correlation_table,
        )
        import plotly.graph_objects as go
        from datetime import datetime as _dt

        fut = load_futures_quarterly()
        enf = _enforcement_share_quarterly()

        if fut.empty or enf.empty:
            st.info("no futures data yet — run `python -m collectors.futures` to pull yfinance prices.")
        else:
            picked = st.multiselect(
                "commodities",
                options=TICKERS_ALL(),
                default=LABOR_HEAVY + BASELINE,
                format_func=lambda t: TICKER_DISPLAY.get(t, t),
            )

            # filter to year range
            enf_f = enf.loc[(enf.index.year >= year_range[0]) & (enf.index.year <= year_range[1])]
            fig = go.Figure()
            # enforcement share as filled area (left y)
            fig.add_trace(
                go.Scatter(
                    x=enf_f.index, y=enf_f.values,
                    mode="lines", fill="tozeroy", name="enforcement-framed share (news)",
                    line=dict(color="#c23b22", width=1),
                    fillcolor="rgba(194,59,34,0.35)",
                    yaxis="y1",
                )
            )
            # futures normalized to 100 at first value within the selected window
            for t in picked:
                sub = fut[fut["ticker"] == t].set_index("date")["close"]
                sub = sub.loc[(sub.index.year >= year_range[0]) & (sub.index.year <= year_range[1])]
                if sub.empty:
                    continue
                norm = sub / sub.iloc[0] * 100
                fig.add_trace(
                    go.Scatter(
                        x=norm.index, y=norm.values,
                        mode="lines",
                        name=TICKER_DISPLAY.get(t, t),
                        line=dict(color=TICKER_COLORS.get(t, "#888"), width=2),
                        yaxis="y2",
                    )
                )

            shapes, annotations = pc._event_shapes(y_min=0, y_max=1)
            fig.update_layout(
                title="enforcement-framed share vs ag futures (normalized)",
                xaxis_title="year",
                yaxis=dict(title="enforcement share", tickformat=".0%", range=[0, 0.25], side="left"),
                yaxis2=dict(title="ag futures (indexed to 100)", overlaying="y", side="right"),
                hovermode="x unified",
                shapes=shapes,
                annotations=annotations,
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25),
                margin=dict(t=80, b=40, l=60, r=60),
            )
            st.plotly_chart(fig, width="stretch")

            st.markdown("##### correlation (news enforcement share vs quarterly returns)")
            st.dataframe(correlation_table(), width="stretch", hide_index=True)
            st.caption(
                "with only ~65 quarterly observations and a relatively stable news framing series, "
                "current correlations are weak. reddit stance share (more variable) is the better candidate for future work."
            )

            st.markdown("##### event-window returns")
            st.caption(
                "30-trading-day cumulative return for each ticker in the window before and after each policy event. "
                "`post_minus_pre` isolates the event-specific move. negative on labor-heavy tickers suggests enforcement priced in."
            )
            from panels.panel4_futures import event_window_returns
            ew_window = st.slider("window (trading days)", 10, 60, 30, step=5)
            ew = event_window_returns(window_days=ew_window)
            if ew.empty:
                st.info("no event-window data.")
            else:
                display = ew.copy()
                display["pre_return"] = display["pre_return"].map(lambda v: f"{v:+.1%}" if pd.notna(v) else "—")
                display["post_return"] = display["post_return"].map(lambda v: f"{v:+.1%}" if pd.notna(v) else "—")
                display["post_minus_pre"] = display["post_minus_pre"].map(lambda v: f"{v:+.1%}" if pd.notna(v) else "—")
                st.dataframe(display, width="stretch", hide_index=True)

                # pivot to matrix event x ticker for heatmap
                import plotly.graph_objects as go
                mat = ew.pivot(index="event", columns="ticker", values="post_minus_pre")
                ordered_events = ew.drop_duplicates("event")["event"].tolist()
                mat = mat.reindex(ordered_events)
                ticker_cols = [t for t in TICKERS_ALL() if t in mat.columns]
                mat = mat[ticker_cols]
                fig_ev = go.Figure(
                    go.Heatmap(
                        z=mat.values,
                        x=[TICKER_DISPLAY.get(t, t) for t in mat.columns],
                        y=mat.index,
                        colorscale="RdBu",
                        zmid=0,
                        colorbar=dict(title="Δ return", tickformat=".0%"),
                        hovertemplate="%{y} — %{x}: %{z:+.1%}<extra></extra>",
                    )
                )
                fig_ev.update_layout(
                    title=f"event-window return shift (post−pre, ±{ew_window} trading days)",
                    height=420,
                    margin=dict(t=60, b=40, l=240, r=20),
                )
                st.plotly_chart(fig_ev, width="stretch")
    except Exception as e:
        st.error(f"panel 4 error: {e}")
        import traceback
        st.code(traceback.format_exc())


# ===== data =====

with tab_data:
    st.markdown("##### raw data browser")
    choices = {
        "news volumes (panel 1)": load_news_volumes,
        "reddit posts (stance)": lambda: pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv") if (PROCESSED_DIR / "reddit_posts_stance.csv").exists() else pd.DataFrame(),
        "full corpus (panel 3)": lambda: load_corpus(),
    }
    pick = st.selectbox("dataset", list(choices.keys()))
    df = choices[pick]()
    if df.empty:
        st.warning("no rows")
    else:
        if "date" in df.columns:
            df_f = _filter_by_year(df, *year_range)
        else:
            df_f = df
        st.caption(f"{len(df_f):,} rows (of {len(df):,} total)")
        st.dataframe(df_f.head(1000), width="stretch")
        st.download_button(
            "download filtered CSV",
            df_f.to_csv(index=False).encode(),
            file_name=f"{pick.replace(' ', '_')}.csv",
            mime="text/csv",
        )


# ===== about =====

with tab_about:
    st.markdown(
        """
### about

case study for **AGRCOMM 2330**, investigating whether public discourse on US migrant farm labor shifts measurably at political regime changes between 2010 and 2026.

three independent signals, all anchored to the same policy event timeline:

1. **language** — keyword frequency (enforcement-framed vs labor-framed vs neutral)
2. **stance** — pro-enforcement / pro-immigrant-labor / neutral (three-way LLM classification via claude haiku 4.5)
3. **topic** — BERTopic clusters on the combined news + reddit corpus

**if all three panels break at the same hinge points → discourse is regime-driven.**
if they diverge → some parts of public feeling are sticky, others reactive.

### event timeline
        """
    )
    events_df = pd.DataFrame(load_events())
    st.dataframe(events_df, width="stretch", hide_index=True)

    st.markdown(
        """
### data sources

- **media cloud** — US mainstream political blogs + online news, 2010-present
- **reddit** via PRAW — r/politics, r/news, r/farming, r/immigration, state subs (Ohio, California, Florida, Texas)
- **GDELT** DOC 2.0 — secondary news source (currently disabled due to rate limits; media cloud covers the full range)

### team

david, ella, sydney
        """
    )
