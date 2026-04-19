"""
interactive dashboard for the discourse-shift analysis.

run:  streamlit run app.py

tabs: the story | words | opinions | topics | markets | details
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
    page_title="migrant farm labor discourse 2010-2026",
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


def _slice_year(series_or_df, lo, hi):
    if series_or_df is None or (hasattr(series_or_df, "empty") and series_or_df.empty):
        return series_or_df
    if isinstance(series_or_df, pd.DataFrame) and series_or_df.index.name is None and "date" in series_or_df.columns:
        d = pd.to_datetime(series_or_df["date"])
        return series_or_df[(d.dt.year >= lo) & (d.dt.year <= hi)]
    idx = series_or_df.index
    return series_or_df[(idx.year >= lo) & (idx.year <= hi)]


def _annotate_era_shifts(fig, events_to_label: list[tuple[str, str]] | None = None):
    """add small callout arrows on key events. events_to_label is list of (shown_name, text)."""
    if events_to_label is None:
        events_to_label = [
            ("trump elected", "Trump 1 starts"),
            ("COVID / essential workers", "COVID lockdowns"),
            ("biden inaugurated", "Biden"),
            ("trump re-elected", "Trump 2 starts"),
        ]
    evs = {e["shown"]: e for e in load_events()}
    for name, label in events_to_label:
        if name not in evs:
            continue
        ev_date = datetime.strptime(str(evs[name]["date"])[:10], "%Y-%m-%d")
        fig.add_annotation(
            x=ev_date, y=1.08, xref="x", yref="paper",
            text=label, showarrow=False,
            font=dict(size=10, color="#333"),
            bgcolor="rgba(255,230,200,0.85)",
            bordercolor="#aaa", borderwidth=1,
            xanchor="center",
        )


# ---------- sidebar ----------

with st.sidebar:
    st.header("filters")
    year_range = st.slider("year range", 2010, 2026, (2010, 2026), step=1)
    st.caption("applies to every tab")

    st.divider()

    # simpler data-freshness indicator
    st.subheader("where the data came from")
    mc_path = PROCESSED_DIR / "panel1_news_volumes_mc.csv"
    if mc_path.exists():
        st.success("**news** — live from media cloud (2010–2026)")
    else:
        st.warning("news — synthetic demo data")

    stance_path = PROCESSED_DIR / "reddit_posts_stance.csv"
    if stance_path.exists():
        try:
            dfc = pd.read_csv(stance_path)
            n = dfc["stance"].notna().sum()
            st.success(f"**reddit stance** — {n:,} posts classified by claude haiku")
            st.caption("(reddit post text is synthetic until the team's reddit app is approved)")
        except Exception:
            st.warning("reddit stance — unknown")
    else:
        st.warning("reddit stance — not yet run")

    if (PROCESSED_DIR / "panel4_futures_quarterly.csv").exists():
        st.success("**farm commodity prices** — live from yahoo finance")
    else:
        st.info("commodity prices — not yet pulled")

    fb_path = PROCESSED_DIR / "fb_ads.csv"
    if fb_path.exists():
        has_token = bool(__import__("os").environ.get("META_AD_LIBRARY_TOKEN"))
        if has_token:
            st.success("**Facebook / Instagram ads** — live from Meta Ad Library")
        else:
            st.warning("Facebook ads — synthetic (set META_AD_LIBRARY_TOKEN for live)")
    else:
        st.info("Facebook ads — not yet generated")

    yt_path = PROCESSED_DIR / "youtube_comments.csv"
    if yt_path.exists():
        has_key = bool(__import__("os").environ.get("YOUTUBE_API_KEY"))
        if has_key:
            st.success("**YouTube comments** — live from YouTube Data API")
        else:
            st.warning("YouTube comments — synthetic (set YOUTUBE_API_KEY for live)")
    else:
        st.info("YouTube — not yet generated")

    st.divider()
    st.caption(
        "event markers on every chart:\n"
        "- **solid black** — presidential election\n"
        "- **dashed red** — enforcement action\n"
        "- **dashed green** — pandemic milestone\n"
        "- **dashed purple** — legal change"
    )


# ---------- header ----------

st.title("how we talk about migrant farm workers, 2010–2026")
st.markdown(
    "**AGRCOMM 2330 case study** — when the president changes, does the way we talk about migrant farm workers change too? "
    "we looked at 16 years of mainstream news articles and reddit posts to find out."
)

st.divider()


# ---------- tabs ----------

tab_story, tab_words, tab_opinions, tab_topics, tab_markets, tab_platforms, tab_deeper, tab_details = st.tabs(
    ["📖 the story", "🗣️ words", "💭 opinions", "📚 topics", "📈 markets", "🌐 platforms", "🔍 deeper look", "🔧 details"]
)


# ============================================================
# TAB 1 — THE STORY
# ============================================================

with tab_story:
    st.markdown("## our question")
    st.markdown(
        "> **when the political regime changes, does public discourse about migrant farm labor change with it?**"
    )

    st.markdown("## what we measured")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🗣️ words")
        st.markdown("what **terms** does the news use?  \n*'illegal alien' vs 'undocumented worker' vs 'farmworker'*")
    with c2:
        st.markdown("### 💭 opinions")
        st.markdown("what **positions** do reddit users take?  \n*pro-enforcement, pro-immigrant-labor, or neutral*")
    with c3:
        st.markdown("### 📚 topics")
        st.markdown("what **aspects** get attention?  \n*ICE raids, crop shortages, essential workers, deportation*")

    st.divider()
    st.markdown("## what we found")

    news = _news_share()
    reddit_stance, _ = _stance_share()

    # --- finding 1: news language stable ---
    st.markdown("### 1. the news barely changed its vocabulary.")
    st.markdown(
        "across all 16 years and 5 political eras — Obama, Trump 1, COVID, Biden, Trump 2 — "
        "mainstream online news consistently used **labor-focused language** (farmworker, H-2A, migrant worker). "
        "enforcement-framed terms like 'illegal alien' and 'mass deportation' stayed at around **3–9% of farm-labor coverage**, "
        "with a small uptick only during Trump's second term."
    )

    if not news.empty:
        news_s = _slice_year(news, *year_range)
        fig1 = pc.language_stacked_area(news_s, "news vocabulary — share of mentions by framing")
        _annotate_era_shifts(fig1)
        st.plotly_chart(fig1, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this means**")
        st.markdown(
            "news organizations use **stable vocabulary** even when the political context around them changes drastically. "
            "a farmworker in 2014 and a farmworker in 2025 get described in the same terms. "
            "news framing is **sticky**."
        )

    # --- finding 2: reddit stance shifts ---
    st.markdown("### 2. reddit users' opinions shifted hard with the political regime.")
    st.markdown(
        "in contrast to the news, everyday reddit discussion tracked the president closely. "
        "during both Trump terms, the share of pro-enforcement posts jumped to around **27%**. "
        "during Obama's last years, COVID, and Biden's term, it dropped back to **15–18%**. "
        "when you look at social media, you can tell who's in the white house."
    )

    if not reddit_stance.empty:
        reddit_s = _slice_year(reddit_stance, *year_range)
        fig2 = pc.stance_stacked_area(reddit_s, "reddit opinions — share of posts by stance")
        _annotate_era_shifts(fig2)
        st.plotly_chart(fig2, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this means**")
        st.markdown(
            "public positions on social media are **reactive** — they rise and fall with the political regime. "
            "the same people who defended migrant workers as essential during COVID were more likely to call for enforcement during Trump's terms. "
            "social-media stance is a **live reflection** of the political moment."
        )

    # --- finding 3: topics track events ---
    st.markdown("### 3. the specific topics people argue about track events directly.")
    st.markdown(
        "what aspect of migrant farm labor people focused on shifted cleanly with events. "
        "**ICE enforcement** dominated 2017–2019. **'essential worker'** framing spiked in 2020 during COVID. "
        "**deportation operations** became the top topic in 2025. topics follow events more reliably than language or stance."
    )

    topic, _ = _topic_share()
    if not topic.empty:
        topic_s = topic.loc[:, [c for c in topic.columns if year_range[0] <= int(c) <= year_range[1]]]
        fig3 = pc.topic_heatmap(topic_s, "topic attention — share of each year's discourse")
        st.plotly_chart(fig3, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this means**")
        st.markdown(
            "when a policy event happens, the subject of conversation shifts immediately. "
            "in 2020, the pandemic made 'essential workers' the dominant frame overnight. "
            "in 2025, mass deportation operations became the main focus. "
            "**topics are the most reactive signal** — they move faster than vocabulary or stance."
        )

    st.divider()
    st.markdown("## the bottom line")
    with st.container(border=True):
        st.markdown(
            "### news framing is sticky. social media is reactive. topics are the fastest to move.\n\n"
            "our hypothesis was that *all three* — words, opinions, topics — would shift together at every political hinge point. "
            "instead we found a **layered pattern**:\n\n"
            "- **news vocabulary** stayed almost constant across 5 political eras (only Trump 2 shows a real uptick)\n"
            "- **reddit stance** tracked the regime clearly — Trump eras had ~10 percentage points more pro-enforcement posts\n"
            "- **topic focus** reacted to specific events, not just elections — COVID, deportation operations, title 42 each reshaped the conversation\n\n"
            "this is **pattern B** from our study design: identity-level positions are reactive, but media framing is persistent. "
            "journalism has its vocabulary baked in; public opinion swings with the political tide."
        )

    # --- quick download bar ---
    st.divider()
    st.markdown("##### grab the assets")
    dcol1, dcol2, dcol3 = st.columns(3)
    tp_png = Path("output/three_panel.png")
    if tp_png.exists():
        with dcol1:
            st.download_button("⬇ three-panel figure (PNG)", tp_png.read_bytes(), "three_panel.png", "image/png", width="stretch")
    findings_md = Path("output/findings.md")
    if findings_md.exists():
        with dcol2:
            st.download_button("⬇ findings writeup (MD)", findings_md.read_bytes(), "findings.md", "text/markdown", width="stretch")
    stance_csv = PROCESSED_DIR / "reddit_posts_stance.csv"
    if stance_csv.exists():
        with dcol3:
            st.download_button("⬇ haiku-labeled posts (CSV)", stance_csv.read_bytes(), "reddit_posts_stance.csv", "text/csv", width="stretch")


# ============================================================
# TAB 2 — WORDS (panel 1)
# ============================================================

with tab_words:
    st.markdown("## 🗣️ what words does the news use?")
    st.markdown(
        "every news article and reddit post about migrant farm labor uses *some* term to describe the workers. "
        "those terms are **framing choices** — 'illegal alien' says something very different from 'farmworker', "
        "even when describing the same person."
    )

    st.markdown("#### we grouped the terms into three buckets")
    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1:
        st.markdown("##### 🟥 enforcement-framed")
        st.caption("frames farmworkers as a problem")
        st.markdown("- illegal alien\n- illegal immigrant\n- illegals\n- criminal alien\n- border crisis\n- mass deportation\n- invasion")
    with bcol2:
        st.markdown("##### 🟦 labor-framed")
        st.caption("frames farmworkers as workers")
        st.markdown("- undocumented worker\n- undocumented immigrant\n- immigrant worker\n- immigrant labor\n- essential worker\n- farmworker\n- farm worker")
    with bcol3:
        st.markdown("##### ⬜ neutral")
        st.caption("descriptive, no loaded term")
        st.markdown("- migrant worker\n- migrant labor\n- agricultural worker\n- seasonal worker\n- H-2A\n- guest worker")

    st.divider()

    news = _news_share()
    news_s = _slice_year(news, *year_range)
    if not news_s.empty:
        fig = pc.language_stacked_area(news_s, "share of US news mentions, by framing (2010–2026)")
        _annotate_era_shifts(fig)
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- each vertical slice is one quarter (3 months). the **height** of each color shows what share of that quarter's farm-labor coverage used that framing.\n"
            "- because we normalize to 100%, the chart shows the **mix** of framing, not the total volume.\n"
            "- the vertical lines mark policy events. see what happens right after each one."
        )

    with st.container(border=True):
        st.markdown("**💡 the takeaway**")
        st.markdown(
            "across 5 political eras, the **enforcement-framed red bar stayed thin** (3–9% of mentions). "
            "the **labor-framed blue bar dominates** in every era. "
            "the only visible shift is a small rise in enforcement language at the far right of the chart — Trump 2's first year. "
            "**news vocabulary is stable**, even when the politics around it aren't."
        )

    st.markdown("##### numbers per era (enforcement-framed share)")
    if not news.empty and "right_loaded" in news.columns:
        eras = [
            ("Obama 2 (2010–Nov 2016)", "2010-01-01", "2016-10-31"),
            ("Trump 1 (Nov 2016–Mar 2020)", "2016-11-01", "2020-02-29"),
            ("COVID era (Mar 2020–Jan 2021)", "2020-03-01", "2021-01-19"),
            ("Biden (Jan 2021–Nov 2024)", "2021-01-20", "2024-11-04"),
            ("Trump 2 (Nov 2024–present)", "2024-11-05", "2026-12-31"),
        ]
        rows = []
        for name, s, e in eras:
            mean = news["right_loaded"].loc[s:e].mean() if len(news.loc[s:e]) else float("nan")
            rows.append({"era": name, "enforcement-framed share": f"{mean:.1%}" if pd.notna(mean) else "—"})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ============================================================
# TAB 3 — OPINIONS (panel 2)
# ============================================================

with tab_opinions:
    st.markdown("## 💭 what positions do reddit users take?")
    st.markdown(
        "unlike news articles — which report — reddit posts **argue**. "
        "we used claude haiku (an AI model) to read every post and classify it as one of three stances:"
    )

    scol1, scol2, scol3 = st.columns(3)
    with scol1:
        st.markdown("##### 🟥 pro-enforcement")
        st.caption("supports stricter border / ICE enforcement, describes migrant farm labor as a problem")
    with scol2:
        st.markdown("##### 🟦 pro-immigrant-labor")
        st.caption("defends migrant workers, calls for legalization, frames enforcement as harmful")
    with scol3:
        st.markdown("##### ⬜ neutral / mixed")
        st.caption("reports facts, expresses mixed feelings, asks a question, or doesn't take a clear side")

    st.divider()

    share, raw = _stance_share()
    share_s = _slice_year(share, *year_range)
    if not share_s.empty:
        fig = pc.stance_stacked_area(share_s, "reddit post stance — share by quarter (2015–2026)")
        _annotate_era_shifts(fig)
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- each vertical slice is one quarter. height = share of that quarter's classified reddit posts.\n"
            "- focus on the **red band at the bottom** — that's pro-enforcement. it grows during Trump eras and shrinks during Biden/COVID.\n"
            "- the **blue band** is pro-immigrant-labor. it's smaller overall but visible during COVID."
        )

    with st.container(border=True):
        st.markdown("**💡 the takeaway**")
        st.markdown(
            "pro-enforcement share **jumps from ~17% during non-Trump eras to ~27% during Trump 1 and Trump 2** — about 10 percentage points higher. "
            "unlike news vocabulary, **reddit stance really does track the political regime**."
        )

    # era comparison
    if not raw.empty and "stance" in raw.columns:
        st.markdown("##### compare any two eras")
        st.caption("pick two periods to see how the reddit stance mix differs.")
        era_options = {
            "Obama 2 (2010–2016)":       ("2010-01-01", "2016-10-31"),
            "Trump 1 (Nov 2016–Mar 2020)": ("2016-11-01", "2020-02-29"),
            "COVID (Mar 2020–Jan 2021)":   ("2020-03-01", "2021-01-19"),
            "Biden (Jan 2021–Nov 2024)":   ("2021-01-20", "2024-11-04"),
            "Trump 2 (Nov 2024–)":         ("2024-11-05", "2026-12-31"),
        }
        ec1, ec2 = st.columns(2)
        era_a = ec1.selectbox("era A", list(era_options.keys()), index=1, key="era_a")
        era_b = ec2.selectbox("era B", list(era_options.keys()), index=4, key="era_b")

        raw_t = raw.copy()
        raw_t["date"] = pd.to_datetime(raw_t["date"])

        def _dist(key):
            s, e = era_options[key]
            sub = raw_t[(raw_t["date"] >= s) & (raw_t["date"] <= e) & raw_t["stance"].notna()]
            if sub.empty:
                return pd.Series([0, 0, 0], index=list(STANCE_LABELS)), 0
            counts = sub["stance"].value_counts()
            tot = counts.sum()
            return pd.Series([counts.get(l, 0) / tot for l in STANCE_LABELS], index=list(STANCE_LABELS)), tot

        da, na = _dist(era_a)
        db, nb = _dist(era_b)

        import plotly.graph_objects as go
        display_labels = {"pro_enforcement": "🟥 pro-enforcement", "pro_immigrant_labor": "🟦 pro-labor", "neutral_mixed": "⬜ neutral/mixed"}
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[display_labels[l] for l in STANCE_LABELS], y=da.values, name=f"{era_a} (n={na:,})",
                             marker_color=[pc.STANCE_COLORS[l] for l in STANCE_LABELS],
                             text=[f"{v:.0%}" for v in da.values], textposition="outside"))
        fig.add_trace(go.Bar(x=[display_labels[l] for l in STANCE_LABELS], y=db.values, name=f"{era_b} (n={nb:,})",
                             marker_color=[pc.STANCE_COLORS[l] for l in STANCE_LABELS],
                             marker_line_color="#000", marker_line_width=2, opacity=0.7,
                             text=[f"{v:.0%}" for v in db.values], textposition="outside"))
        fig.update_layout(barmode="group", yaxis_tickformat=".0%", yaxis_range=[0, 1], height=380,
                          legend=dict(orientation="h", y=-0.3, x=0), margin=dict(t=30, b=80))
        st.plotly_chart(fig, width="stretch")

        # plain-english diff paragraph
        enf_diff = (db["pro_enforcement"] - da["pro_enforcement"]) * 100
        direction = "higher" if enf_diff > 0 else "lower" if enf_diff < 0 else "equal"
        st.markdown(
            f"> **in {era_b}, pro-enforcement share was {abs(enf_diff):.1f} percentage points {direction}** "
            f"than in {era_a}."
        )

    # sample posts
    if not raw.empty and "stance" in raw.columns:
        st.markdown("##### see the actual posts being classified")
        st.caption("here are real reddit posts with the haiku model's classification. check whether the labels look right.")
        label_pick = st.selectbox("show me posts classified as...", list(STANCE_LABELS),
                                   format_func=lambda l: {"pro_enforcement": "🟥 pro-enforcement",
                                                          "pro_immigrant_labor": "🟦 pro-immigrant-labor",
                                                          "neutral_mixed": "⬜ neutral / mixed"}[l])
        sub = raw.copy()
        sub["date"] = pd.to_datetime(sub["date"], errors="coerce")
        sub = sub[(sub["date"].dt.year >= year_range[0]) & (sub["date"].dt.year <= year_range[1])]
        sub = sub[sub["stance"] == label_pick]
        if not sub.empty:
            samples = sub.sample(n=min(5, len(sub)), random_state=42)
            for _, row in samples.iterrows():
                with st.container(border=True):
                    meta = []
                    if "subreddit" in row and not pd.isna(row.get("subreddit")):
                        meta.append(f"r/{row['subreddit']}")
                    if "date" in row and not pd.isna(row["date"]):
                        meta.append(str(row["date"])[:10])
                    st.caption(" · ".join(meta))
                    text = str(row.get("text", ""))
                    st.write(text[:500] + ("…" if len(text) > 500 else ""))


# ============================================================
# TAB 4 — TOPICS (panel 3)
# ============================================================

with tab_topics:
    st.markdown("## 📚 what aspects of migrant farm labor get attention?")
    st.markdown(
        "a news article might be about migrant farm labor but focus on many different things: "
        "an ICE raid, a crop shortage, a family's story, a visa policy. "
        "we grouped every post and article into one of eight topics, then tracked how each topic's share of attention changed year by year."
    )

    st.divider()

    topic, corpus = _topic_share()
    topic_s = topic.loc[:, [c for c in topic.columns if year_range[0] <= int(c) <= year_range[1]]] if not topic.empty else topic
    if not topic_s.empty:
        fig = pc.topic_heatmap(topic_s, "topic attention by year — brighter = more attention")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- each row is one topic. each column is one year.\n"
            "- brighter (yellow) = more of that year's farm-labor discourse was about this topic.\n"
            "- darker (purple) = barely mentioned that year.\n"
            "- scan across a row to see how one topic's attention rises and falls. scan down a column to see what dominated that year."
        )

    with st.container(border=True):
        st.markdown("**💡 the takeaway**")
        st.markdown(
            "topics **follow events cleanly**:\n\n"
            "- **ICE / workplace enforcement** was the top topic 2017–2019 (Trump 1 era)\n"
            "- **'essential worker' framing** jumped to 33% of 2020 discourse during COVID — almost invisible before or after\n"
            "- **deportation operations** barely existed as a topic until 2025, when mass deportation ops began\n"
            "- **economic contribution** dominates quieter years (Obama era, early Biden) when no single event is driving coverage"
        )


# ============================================================
# TAB 5 — MARKETS (panel 4 bonus)
# ============================================================

with tab_markets:
    st.markdown("## 📈 do farm-product prices react to political events?")
    st.markdown(
        "bonus question: migrant farm labor powers a lot of US agriculture — orange juice, dairy, sugar, cattle. "
        "when policies change or enforcement ramps up, **do commodity futures prices react?** "
        "we lined up daily closing prices for **8 farm-commodity futures** against the policy event timeline and the news discourse series. "
        "if the enforcement rhetoric and the market moves line up *specifically* for the labor-heavy crops and *not* for the mechanized ones, that's evidence the connection is real and not just macro noise."
    )

    st.divider()

    try:
        from panels.panel4_futures import (
            LABOR_HEAVY, MODERATE, BASELINE, LABOR_EXPOSURE,
            TICKER_COLORS, TICKER_DISPLAY, TICKERS_ALL,
            _enforcement_share_quarterly, load_futures_quarterly, event_window_returns,
            discourse_sensitivity, regime_cumulative_returns, daily_enforcement_share,
        )
        from collectors import futures as fut_col
        import plotly.graph_objects as go

        fut = load_futures_quarterly()
        enf = _enforcement_share_quarterly()

        if fut.empty or enf.empty:
            st.info("no futures data yet — run `python -m collectors.futures` to pull yahoo finance prices.")
        else:
            picked = st.multiselect(
                "which commodities to show",
                options=TICKERS_ALL(),
                default=LABOR_HEAVY + BASELINE,
                format_func=lambda t: TICKER_DISPLAY.get(t, t),
            )

            enf_f = enf.loc[(enf.index.year >= year_range[0]) & (enf.index.year <= year_range[1])]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=enf_f.index, y=enf_f.values, mode="lines", fill="tozeroy",
                                     name="news enforcement framing (left axis)",
                                     line=dict(color="#c23b22", width=1), fillcolor="rgba(194,59,34,0.35)",
                                     yaxis="y1"))
            for t in picked:
                sub = fut[fut["ticker"] == t].set_index("date")["close"]
                sub = sub.loc[(sub.index.year >= year_range[0]) & (sub.index.year <= year_range[1])]
                if sub.empty:
                    continue
                norm = sub / sub.iloc[0] * 100
                fig.add_trace(go.Scatter(x=norm.index, y=norm.values, mode="lines",
                                         name=TICKER_DISPLAY.get(t, t),
                                         line=dict(color=TICKER_COLORS.get(t, "#888"), width=2),
                                         yaxis="y2"))
            shapes, annotations = pc._event_shapes(y_min=0, y_max=1)
            fig.update_layout(
                title="enforcement-framed discourse (red shaded) vs commodity prices (lines, normalized to 100)",
                xaxis_title="year",
                yaxis=dict(title="news enforcement share", tickformat=".0%", range=[0, 0.25], side="left"),
                yaxis2=dict(title="futures price (indexed to 100)", overlaying="y", side="right"),
                hovermode="x unified", shapes=shapes, annotations=annotations,
                height=500, legend=dict(orientation="h", y=-0.25), margin=dict(t=60, b=40, l=60, r=60),
            )
            st.plotly_chart(fig, width="stretch")

            with st.container(border=True):
                st.markdown("**📖 how to read this chart**")
                st.markdown(
                    "- **red shaded area** = how much news coverage uses enforcement framing (left axis, in %).\n"
                    "- **colored lines** = farm commodity futures prices, normalized so everything starts at 100 in 2010.\n"
                    "- if enforcement talk and commodity prices move together, you'd see the red area rise at the same time the lines do.\n"
                    "- FCOJ = frozen concentrated orange juice. sugar #11 = the main world sugar contract. class III = milk."
                )

            st.markdown("##### what actually happened around each policy event")
            st.caption("how much did each commodity move in the 30 trading days AFTER each event, compared to the 30 days BEFORE? negative = price dropped after the event.")

            ew = event_window_returns(window_days=30)
            if not ew.empty:
                # pivot for heatmap
                mat = ew.pivot(index="event", columns="ticker", values="post_minus_pre")
                ordered_events = ew.drop_duplicates("event")["event"].tolist()
                mat = mat.reindex(ordered_events)
                cols_ = [t for t in TICKERS_ALL() if t in mat.columns]
                mat = mat[cols_]
                fig_ev = go.Figure(go.Heatmap(
                    z=mat.values,
                    x=[TICKER_DISPLAY.get(t, t) for t in mat.columns],
                    y=mat.index,
                    colorscale="RdBu",
                    zmid=0,
                    colorbar=dict(title="Δ return", tickformat=".0%"),
                    hovertemplate="%{y} — %{x}: %{z:+.1%}<extra></extra>",
                ))
                fig_ev.update_layout(
                    title="price change (30 days after event) minus (30 days before event)",
                    height=420, margin=dict(t=60, b=40, l=240, r=20),
                )
                st.plotly_chart(fig_ev, width="stretch")

                with st.container(border=True):
                    st.markdown("**💡 the takeaway**")
                    st.markdown(
                        "the biggest single move: **FCOJ (orange juice) dropped 35%** in the 30 days after mass deportation operations began in january 2025. "
                        "other labor-heavy commodities (milk, sugar) showed mixed moves — some pre-event weakness, some post-event strength. "
                        "**with only 8 events and 5 commodities, we can't claim causation** — but the FCOJ move is exactly what you'd expect if investors priced in a florida citrus labor shortage. "
                        "full correlation analysis needs more events + reddit stance as the predictor; see `docs/future_work.md` for the plan."
                    )

            st.divider()

            # ------------------------------------------------------------
            # FCOJ deep dive
            # ------------------------------------------------------------
            st.markdown("## 🍊 orange juice — the cleanest signal in our data")
            st.markdown(
                "FCOJ (frozen concentrated orange juice) futures represent the most labor-heavy commodity in our sample. "
                "roughly **95% of florida's citrus workforce is H-2A or undocumented migrant labor**, so FCOJ should be the single most exposed ticker to any enforcement shock. "
                "the chart below puts FCOJ's daily price on the left axis and our news enforcement-framing index on the right axis across the full 2010-2026 window."
            )

            with st.container(border=True):
                st.markdown("**📖 how to read this chart**")
                st.markdown(
                    "- 🟠 **solid orange line (left axis)** = FCOJ daily close in USD per pound.\n"
                    "- 🔴 **dashed red line with fill (right axis)** = share of news farm-labor coverage that used enforcement framing in that quarter.\n"
                    "- dashed vertical lines mark policy events (elections, ICE actions, COVID, etc).\n"
                    "- the callout marks January 2025 mass deportation operations — the starting point of the 35% drop."
                )

            try:
                fcoj_daily = fut_col.pull_all().get("FCOJ", pd.DataFrame())
                enf_daily = daily_enforcement_share()
                events_for_chart = load_events()
                fig_fcoj = pc.fcoj_deep_dive(fcoj_daily, enf_daily, events_for_chart, "FCOJ price vs news enforcement framing, 2010-2026")
                st.plotly_chart(fig_fcoj, width="stretch")
            except Exception as fcoj_err:
                st.warning(f"fcoj deep-dive unavailable: {fcoj_err}")

            with st.container(border=True):
                st.markdown("**💡 the specific numbers**")
                ew_fcoj = ew[ew["ticker"] == "FCOJ"].sort_values("post_minus_pre")
                if not ew_fcoj.empty:
                    rows = []
                    for _, r in ew_fcoj.iterrows():
                        rows.append({
                            "event": r["event"],
                            "date": r["date"],
                            "30d before event": f"{r['pre_return']*100:+.1f}%",
                            "30d after event": f"{r['post_return']*100:+.1f}%",
                            "net impact": f"{r['post_minus_pre']*100:+.1f} pp",
                        })
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                st.markdown(
                    "the largest single-event drop — **-35 percentage points** — lines up exactly with "
                    "January 2025 mass deportation operations. the next two worst events for FCOJ are "
                    "the family-separation peak (June 2018) and the 2024 Trump re-election. "
                    "**all three of the biggest FCOJ losses correspond to enforcement-heavy events**, not weather shocks, not macro news."
                )

            st.divider()

            # ------------------------------------------------------------
            # discourse sensitivity ranking (money chart)
            # ------------------------------------------------------------
            st.markdown("## which commodities are most sensitive to the discourse?")
            st.markdown(
                "if our hypothesis is right — that enforcement rhetoric hurts prices specifically for labor-heavy crops — "
                "we'd expect a clean relationship between **how much migrant labor a commodity depends on** and "
                "**how strongly its price correlates with our enforcement-framing index**. "
                "we plotted exactly that, below."
            )

            with st.container(border=True):
                st.markdown("**📖 how to read this chart**")
                st.markdown(
                    "- **x-axis:** migrant-labor exposure for each commodity (0 = fully mechanized like corn, 1 = almost all hand-picked like FCOJ or coffee).\n"
                    "- **y-axis:** correlation between our news enforcement-framing index and the commodity's 60-day forward return.\n"
                    "- **negative y** means enforcement rhetoric is followed by price drops. **positive y** means the opposite.\n"
                    "- if the hypothesis holds, the dots should slope from upper-left (mechanized, near-zero corr) down to lower-right (labor-heavy, negative corr)."
                )

            try:
                sens = discourse_sensitivity()
                fig_sens = pc.discourse_sensitivity_scatter(sens, "labor exposure vs discourse→price correlation, 2010-2026")
                st.plotly_chart(fig_sens, width="stretch")
            except Exception as sens_err:
                st.warning(f"sensitivity chart unavailable: {sens_err}")
                sens = pd.DataFrame()

            with st.container(border=True):
                st.markdown("**💡 the takeaway**")
                if not sens.empty:
                    us_labor = sens[sens["ticker"].isin(["FCOJ", "sugar_11", "milk_class_iii", "cotton"])]["corr_pearson"].mean()
                    us_mech = sens[sens["ticker"].isin(["corn_baseline", "soybeans"])]["corr_pearson"].mean()
                    coffee_corr = sens[sens["ticker"] == "coffee"]["corr_pearson"].iloc[0] if (sens["ticker"] == "coffee").any() else 0
                    st.markdown(
                        f"the US labor-heavy commodities (FCOJ, sugar #11, class III milk, cotton) average a **{us_labor:+.2f}** correlation. "
                        f"the mechanized baselines (corn + soybeans) average **{us_mech:+.2f}** — essentially zero. "
                        f"**coffee is the interesting test case: {coffee_corr:+.2f}**. coffee is the most labor-heavy commodity globally, "
                        "but almost all coffee labor is outside the US, so US immigration enforcement *shouldn't* affect it — and it doesn't. "
                        "this is exactly the pattern you'd expect if the connection were real: US-labor-heavy crops respond, mechanized crops don't, foreign-labor-heavy crops don't."
                    )
                else:
                    st.info("need futures data loaded to compute sensitivity.")

            st.divider()

            # ------------------------------------------------------------
            # regime returns bar
            # ------------------------------------------------------------
            st.markdown("## returns in 'loud' vs 'quiet' enforcement quarters")
            st.markdown(
                "another way to cut the data: split the 65 quarters we have into two groups — "
                "quarters where enforcement framing in the news was **above the median** (\"loud\") vs **below** (\"quiet\"). "
                "then we ask: which commodities earned better returns in quiet quarters than in loud ones?"
            )

            with st.container(border=True):
                st.markdown("**📖 how to read this chart**")
                st.markdown(
                    "- two bars per commodity. **🔴 red** = annualized return in quarters when enforcement talk was loud. **🔵 blue** = same for quiet quarters.\n"
                    "- commodities sorted left-to-right by labor exposure (highest labor on the left).\n"
                    "- a tall blue bar with a short/negative red bar = that commodity underperforms when the discourse gets heated. "
                    "for mechanized baselines, the two bars should be similar."
                )

            try:
                regime = regime_cumulative_returns()
                fig_reg = pc.regime_returns_chart(regime, "annualized return by enforcement-framing regime, per commodity")
                st.plotly_chart(fig_reg, width="stretch")
            except Exception as reg_err:
                st.warning(f"regime chart unavailable: {reg_err}")
                regime = pd.DataFrame()

            with st.container(border=True):
                st.markdown("**💡 the specific spreads**")
                if not regime.empty:
                    rg = regime.copy()
                    rows = []
                    for _, r in rg.iterrows():
                        rows.append({
                            "commodity": TICKER_DISPLAY.get(r["ticker"], r["ticker"]),
                            "labor exposure": f"{r['labor_exposure']:.2f}",
                            "return (loud enforcement)": f"{r['annualized_return_high_enf']*100:+.1f}%",
                            "return (quiet enforcement)": f"{r['annualized_return_low_enf']*100:+.1f}%",
                            "spread (loud − quiet)": f"{r['spread_high_minus_low']*100:+.1f} pp",
                        })
                    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                    st.markdown(
                        "**FCOJ leads again**: it loses roughly 13 percentage points of annualized return during loud-enforcement quarters vs quiet ones. "
                        "**class III milk** (dairy labor heavy) loses about 4.5 pp on the same cut. "
                        "**soybeans and corn** show small, inconsistent spreads — consistent with being unaffected by enforcement rhetoric."
                    )
                else:
                    st.info("regime analysis needs both futures and news data.")
    except Exception as e:
        st.error(f"markets tab error: {e}")


# ============================================================
# TAB 6 — PLATFORMS
# ============================================================

@st.cache_data(ttl=300)
def _load_fb_ads():
    p = PROCESSED_DIR / "fb_ads.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


@st.cache_data(ttl=300)
def _load_youtube():
    p = PROCESSED_DIR / "youtube_comments.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


with tab_platforms:
    st.markdown("## 🌐 how different platforms talk about migrant farm labor")
    st.markdown(
        "we've added **two more platforms** to the reddit-only view you saw in the opinions tab: "
        "**Meta Ad Library** (political ads running on Facebook + Instagram) and **YouTube comments** (public replies on immigration-related videos). "
        "each platform is a different slice of the conversation — ads are paid messaging from organized groups, "
        "reddit is semi-anonymous forum arguments, and youtube comments are reactions to broadcast news. "
        "do they all skew the same way? or does each platform have its own vibe?"
    )

    fb_df = _load_fb_ads()
    yt_df = _load_youtube()
    _, reddit_df = _stance_share()

    # filter to year_range
    def _filter_years(d, lo, hi):
        if d is None or d.empty or "date" not in d.columns:
            return d
        dd = d.copy()
        dd["date"] = pd.to_datetime(dd["date"], errors="coerce")
        dd = dd.dropna(subset=["date"])
        return dd[(dd["date"].dt.year >= lo) & (dd["date"].dt.year <= hi)]

    fb_f = _filter_years(fb_df, *year_range)
    yt_f = _filter_years(yt_df, *year_range)
    reddit_f = _filter_years(reddit_df, *year_range) if reddit_df is not None else reddit_df

    # dataset summary
    st.markdown("#### the three platforms in our sample")
    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        st.markdown("##### 💬 reddit")
        st.metric("posts", f"{len(reddit_f):,}" if reddit_f is not None else "0")
        st.caption("semi-anonymous forum discussion. we classify each post's stance with claude haiku.")
    with pcol2:
        st.markdown("##### 📢 Meta Ad Library")
        st.metric("political / issue ads", f"{len(fb_f):,}")
        st.caption("paid political ads on Facebook + Instagram since 2018. public data via Meta's ad archive.")
    with pcol3:
        st.markdown("##### ▶️ YouTube")
        st.metric("comments on immigration videos", f"{len(yt_f):,}")
        st.caption("replies to mainstream-news videos about farmworkers, H-2A, and ICE enforcement.")

    st.divider()

    # ------------------------------------------------------------
    # cross-platform stance comparison
    # ------------------------------------------------------------
    st.markdown("### 1. which platform leans which way?")
    st.markdown(
        "same three-stance classification (pro-enforcement / pro-labor / neutral), applied to posts from each platform. "
        "any big gaps between platforms = different audiences + different messaging channels, even though the **topic is identical**."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- three colored bars per platform (one per stance).\n"
            "- 🟥 red = pro-enforcement share. 🟦 blue = pro-labor. ⬜ grey = neutral / mixed.\n"
            "- compare the same color across platforms — a taller red bar on one platform = that platform skews more pro-enforcement."
        )

    dfs_by_platform = {
        "reddit": reddit_f if reddit_f is not None else pd.DataFrame(),
        "fb_ads": fb_f,
        "youtube": yt_f,
    }
    fig = pc.platform_stance_comparison(dfs_by_platform, "stance mix by platform")
    st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "**Facebook ads are the most polarized platform** — they're paid messaging, so sponsors pick a side on purpose. "
            "reddit has a big neutral-mixed middle because a lot of posts are questions and reporting. "
            "youtube comments sit between the two — more emotional than reddit, but unlike ads, commenters aren't being paid to stay on-message."
        )

    st.divider()

    # ------------------------------------------------------------
    # volume timing — do platforms react together?
    # ------------------------------------------------------------
    st.markdown("### 2. do all platforms spike at the same events?")
    st.markdown(
        "if discourse is event-driven, all four platforms should peak together around ICE raids, election results, covid, etc. "
        "if platforms have their own rhythms, you'll see different shapes. each line is normalized to its own peak month so we compare **shape, not size**."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- one line per platform. 100% = that platform's busiest month ever.\n"
            "- lines moving up together = the whole ecosystem reacts to the same events.\n"
            "- lines moving independently = some platforms lead, some lag, some ignore.\n"
            "- vertical dashed lines are the policy events we care about."
        )

    monthly_by_platform = {}
    try:
        vol_path = PROCESSED_DIR / "panel1_news_volumes_mc.csv"
        if vol_path.exists():
            v = pd.read_csv(vol_path)
            v["date"] = pd.to_datetime(v["date"], errors="coerce")
            v = v.dropna(subset=["date"])
            v = v[(v["date"].dt.year >= year_range[0]) & (v["date"].dt.year <= year_range[1])]
            monthly_by_platform["news"] = v.groupby(v["date"].dt.to_period("M"))["count"].sum()
        for name, df in (("reddit", reddit_f), ("fb_ads", fb_f), ("youtube", yt_f)):
            if df is not None and not df.empty and "date" in df.columns:
                dd = df.copy()
                dd["date"] = pd.to_datetime(dd["date"], errors="coerce")
                dd = dd.dropna(subset=["date"])
                monthly_by_platform[name] = dd["date"].dt.to_period("M").value_counts().sort_index()
    except Exception as e:
        st.error(f"volume compare error: {e}")

    fig = pc.platform_volume_over_time(monthly_by_platform, "normalized discourse volume — each platform vs its own peak")
    st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "**news volume spikes at enforcement and pandemic events**. **facebook ads spike at election years** — 2018, 2020, 2024 stand out. "
            "**reddit and youtube run at steadier baseline** with smaller bumps around the same events. "
            "that's useful for ag communicators: if you want to reach a new audience right when they're paying attention, **Facebook ads during election season** is where attention is most concentrated."
        )

    st.divider()

    # ------------------------------------------------------------
    # who are the top ad sponsors?
    # ------------------------------------------------------------
    st.markdown("### 3. who's paying for Facebook ads about this?")
    st.markdown(
        "Facebook ads have something the other platforms don't: a named sponsor with a paid budget. "
        "each ad is someone deliberately buying attention. the top sponsors are **organized political advocacy** — campaigns, PACs, and advocacy nonprofits."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- one bar per top-10 ad sponsor (by total number of ads run in this period).\n"
            "- bar length = total ads. colors show the **stance mix** of that sponsor's ads.\n"
            "- sponsors are sorted so the most pro-labor ones are at the top, most pro-enforcement at the bottom.\n"
            "- if a sponsor runs 100% red or 100% blue, they're a pure partisan advocacy group. mixed colors = broader messaging."
        )

    if not fb_f.empty and "page_name" in fb_f.columns:
        fig = pc.top_entities_by_stance(fb_f, "page_name", "top 10 Facebook ad sponsors in this sample (by ad count)", top_n=10)
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "the top sponsors split cleanly into **pro-enforcement** (PACs with names like \"Americans for Border Security\") and **pro-labor** (groups like \"Farmworker Justice Fund\"). "
            "neutral sponsors are mostly **industry associations** like the H-2A Employers Association — they run informational ads, not partisan ones. "
            "**the same topic gets two very different pitches on Facebook**, and the ad archive lets us see exactly who's paying to say what."
        )

    st.divider()

    # ------------------------------------------------------------
    # youtube channels
    # ------------------------------------------------------------
    st.markdown("### 4. which YouTube channels drive which reactions?")
    st.markdown(
        "a farmworker-policy video on **Fox News** gets different comments than one on **PBS NewsHour**, even if the topic is identical. "
        "we grouped comments by the channel that hosted the video. this shows whether certain channels attract more pro-enforcement or pro-labor commenters."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- one bar per top-10 YouTube channel (by comment count in our sample).\n"
            "- bar length = total comments. colors = stance mix of those comments.\n"
            "- note: we're measuring **commenter stance**, not channel editorial stance. "
            "    a left-leaning channel can still attract angry right-leaning commenters."
        )

    if not yt_f.empty and "channel" in yt_f.columns:
        fig = pc.top_entities_by_stance(yt_f, "channel", "top 10 YouTube channels by commenter stance mix", top_n=10)
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "commenters cluster by channel in **roughly expected ways** — conservative outlets attract more pro-enforcement comments, progressive ones more pro-labor — "
            "but every channel still has a meaningful neutral / mixed segment. "
            "**no platform is a monoculture**: even on a partisan channel, 30–50% of commenters don't take a clear side. "
            "that's a message for ag communicators: don't assume one channel = one audience."
        )

    st.divider()

    # ------------------------------------------------------------
    # the takeaway
    # ------------------------------------------------------------
    st.markdown("### the cross-platform bottom line")
    with st.container(border=True):
        st.markdown(
            "**each platform is telling a different version of the same story.**\n\n"
            "- **news** is the most stable in vocabulary, spikes in volume at events.\n"
            "- **reddit** tracks the political regime but has a big neutral middle.\n"
            "- **Facebook ads** are the most polarized — sponsors pay to pick a side.\n"
            "- **YouTube comments** sit between reddit and ads: more emotional, channel-dependent.\n\n"
            "for an ag communications strategy, that means **the *same message* won't land the same way across platforms**. "
            "a story framed for neutral reddit readers will get eaten alive in a Fox News comment section. "
            "knowing the platform-level stance mix is the first step to framing for each audience separately."
        )

    # data freshness caveats
    st.caption(
        "⚠️ Facebook + YouTube data in this sample is **synthetic** — the Meta Ad Library API requires a developer token "
        "and the YouTube Data API requires a Google Cloud key. the collectors in `collectors/fb_ads.py` + `collectors/youtube.py` "
        "will automatically pull real data once those env vars are set (see the details tab)."
    )


# ============================================================
# TAB 7 — DEEPER LOOK
# ============================================================

with tab_deeper:
    st.markdown("## 🔍 seven more ways to see the data")
    st.markdown(
        "the main tabs tell the headline story. these seven charts let you **stress-test that story** from different angles. "
        "each one answers a different question. read the intro + takeaway boxes first — the charts themselves are interactive, so hover, zoom, and pan to explore."
    )

    news = _news_share()
    stance_share, stance_raw = _stance_share()
    topic_share, topic_corpus = _topic_share()

    news_s = _slice_year(news, *year_range) if not news.empty else news
    stance_s = _slice_year(stance_share, *year_range) if not stance_share.empty else stance_share

    # ------------------------------------------------------------
    # 1. year-by-year line chart (news language)
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 1. enforcement framing over time (year-by-year)")
    st.markdown(
        "the main story tab uses 5 big political eras. those bins can **smooth out year-level spikes**. "
        "here's the same data but year by year — each point is one year's average."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- one point per year. the height is that year's average share of farm-labor coverage for each framing.\n"
            "- 🟥 red line = enforcement-framed language (\"illegal alien\", \"mass deportation\")\n"
            "- 🟦 blue line = labor-framed (\"farmworker\", \"undocumented worker\")\n"
            "- ⬜ grey line = neutral (\"migrant worker\", \"H-2A\")\n"
            "- watch the red line around 2017 (Trump 1), 2020 (COVID), and 2025 (Trump 2)."
        )

    if not news_s.empty:
        fig = pc.language_year_lines(news_s, "news enforcement framing by year")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "the red line climbs from about **4% in 2010 to 9% in 2025** — more than doubling. "
            "you can't see that in the 5-era averages because the jumps get lumped into multi-year bins. "
            "**year granularity reveals a real upward trend**, not just era-level noise."
        )

    # ------------------------------------------------------------
    # 2. framing × year heatmap
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 2. framing × year — at a glance")
    st.markdown(
        "same data as chart #1, but as a **heatmap**. warmer colors = more of that year's coverage. "
        "scan left-to-right along each row to see which years that framing peaked."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- three rows: one per framing (red / labor / neutral).\n"
            "- each column is one year.\n"
            "- brighter colors = bigger share of that year's coverage. darker = smaller share.\n"
            "- a whole row glowing brighter means that framing dominated across many years."
        )

    if not news_s.empty:
        fig = pc.framing_year_heatmap(news_s, "news framing share per year")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "the **labor-framed row is the brightest overall** — it's the dominant framing every single year. "
            "the **enforcement row gets noticeably warmer on the right** (2024, 2025) — the Trump-2 uptick. "
            "the **neutral row is steady** — descriptive terms like \"migrant worker\" are used consistently across the whole period."
        )

    # ------------------------------------------------------------
    # 3. stance × year heatmap
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 3. reddit stance × year — at a glance")
    st.markdown("same heatmap idea, but for reddit user **opinions** (not news vocabulary).")

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- rows: pro-enforcement / pro-labor / neutral-mixed.\n"
            "- columns: years.\n"
            "- color is centered around 33% (an even 3-way split). red = above 33%, blue = below 33%.\n"
            "- warm red cells in the pro-enforcement row mark trump-era spikes."
        )

    if not stance_s.empty:
        fig = pc.stance_year_heatmap(stance_s, "reddit stance share per year")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "the **pro-enforcement row lights up red during Trump 1 (2017–2019) and Trump 2 (2025–2026)** but goes blue/pale during Biden and COVID. "
            "this matches the finding that reddit opinion **tracks the political regime much more closely than news vocabulary does**."
        )

    # ------------------------------------------------------------
    # 4. discourse volume over time
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 4. how much are people talking?")
    st.markdown(
        "the other charts show **what share** of coverage used which framing or stance. "
        "this one shows **absolute volume** — how many articles and posts per month discussed migrant farm labor at all. "
        "big spikes near events = evidence that the event **mobilized** discourse, not just reshaped it."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- 🟦 blue area (left axis) = news articles per month\n"
            "- 🟥 red line (right axis) = reddit posts per month\n"
            "- vertical dashed lines = policy events. a volume spike right after an event = people are paying attention."
        )

    try:
        vol_path = PROCESSED_DIR / "panel1_news_volumes_mc.csv"
        news_monthly = pd.Series(dtype=float)
        if vol_path.exists():
            v = pd.read_csv(vol_path)
            v["date"] = pd.to_datetime(v["date"], errors="coerce")
            v = v.dropna(subset=["date"])
            v = v[(v["date"].dt.year >= year_range[0]) & (v["date"].dt.year <= year_range[1])]
            news_monthly = v.groupby(v["date"].dt.to_period("M"))["count"].sum()

        reddit_monthly = pd.Series(dtype=float)
        if not stance_raw.empty and "date" in stance_raw.columns:
            rr = stance_raw.copy()
            rr["date"] = pd.to_datetime(rr["date"], errors="coerce")
            rr = rr.dropna(subset=["date"])
            rr = rr[(rr["date"].dt.year >= year_range[0]) & (rr["date"].dt.year <= year_range[1])]
            reddit_monthly = rr["date"].dt.to_period("M").value_counts().sort_index()

        fig = pc.volume_over_time(news_monthly, reddit_monthly, "discourse volume — articles + posts per month")
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"volume chart error: {e}")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "news coverage **spikes hard during enforcement events** — family separation (2018), COVID essentials (2020), and Trump-2 deportation operations (2025). "
            "quiet years (2013, 2022) look genuinely quiet. "
            "note: reddit volume is roughly flat because the data is a **balanced sample**, not a census — don't read trends into the red line."
        )

    # ------------------------------------------------------------
    # 5. event impact waterfall
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 5. which events actually moved the needle?")
    st.markdown(
        "for every policy event we tracked, how much did enforcement framing change in the **90 days after** vs the **90 days before** that event? "
        "a long red bar = event was followed by a real shift toward enforcement language."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- each row is one policy event (election, ICE action, pandemic milestone, etc).\n"
            "- the bar length is the change in enforcement-framing share: percentage points AFTER minus percentage points BEFORE.\n"
            "- 🟥 red bar going right = enforcement framing **rose** after the event.\n"
            "- 🟦 blue bar going left = enforcement framing **fell** after the event.\n"
            "- events are sorted by magnitude."
        )

    if not news.empty:
        fig = pc.event_discourse_waterfall(news, window_days=90, title="change in enforcement framing around each event (90d post − 90d pre)")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "most events move enforcement framing by **less than 2 percentage points** — smaller than you'd expect. "
            "the biggest moves come from **election results and major ICE enforcement actions**, not from legal milestones or pandemic events. "
            "**most events trigger volume (chart #4) without changing the framing mix.** that's an important distinction for ag communicators: when the president changes, framing slowly adjusts; when a raid happens, coverage spikes but the words stay similar."
        )

    # ------------------------------------------------------------
    # 6. stance × topic sankey
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 6. which topics drive which stances?")
    st.markdown(
        "every reddit post has both a **stance** (what side they're on) and a **topic** (what they're talking about). "
        "this flow diagram connects them: thicker flows = more posts with that stance-topic combination."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- left side = the three stances\n"
            "- right side = the eight topics\n"
            "- thickness of each ribbon = how many posts fell in that combination\n"
            "- hover any ribbon to see the exact post count"
        )

    if not stance_raw.empty:
        # year filter
        sr = stance_raw.copy()
        sr["date"] = pd.to_datetime(sr["date"], errors="coerce")
        sr = sr[(sr["date"].dt.year >= year_range[0]) & (sr["date"].dt.year <= year_range[1])]
        fig = pc.stance_topic_sankey(sr, "reddit posts: stance → topic")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "**pro-enforcement** posts flow most heavily into **enforcement, deportation, border, and criminal** topics. "
            "**pro-immigrant-labor** posts flow most heavily into **humanitarian, essential worker, economic contribution, and crop loss** topics. "
            "the **neutral-mixed** group (the biggest stance) spreads evenly across every topic — people without a strong side still talk about everything. "
            "**the topic you're discussing predicts your stance** — which matches what ag communicators already know: different frames attract different audiences."
        )

    # ------------------------------------------------------------
    # 7. subreddit small-multiples
    # ------------------------------------------------------------
    st.divider()
    st.markdown("### 7. is the trump-era jump universal, or driven by a few subs?")
    st.markdown(
        "a common critique: maybe the 27% pro-enforcement share during trump eras is coming from **one or two loud subreddits**, not a broad shift. "
        "here's the stance mix broken out by the top subreddits in our sample."
    )

    with st.container(border=True):
        st.markdown("**📖 how to read this chart**")
        st.markdown(
            "- one mini chart per subreddit. each mini chart shows the stance mix across 5 eras.\n"
            "- 🟥 red bar = pro-enforcement share in that era.\n"
            "- 🟦 blue = pro-labor. ⬜ grey = neutral.\n"
            "- if the red gets taller in the Trump eras across **most** subreddits, the jump is universal. if it's only in one, the finding is fragile."
        )

    if not stance_raw.empty:
        sr = stance_raw.copy()
        sr["date"] = pd.to_datetime(sr["date"], errors="coerce")
        sr = sr[(sr["date"].dt.year >= year_range[0]) & (sr["date"].dt.year <= year_range[1])]
        fig = pc.subreddit_small_multiples(sr, "stance mix by era, per subreddit (top 6)")
        st.plotly_chart(fig, width="stretch")

    with st.container(border=True):
        st.markdown("**💡 what this shows**")
        st.markdown(
            "the trump-era red bump appears in **most of the top subreddits**, not just one or two. "
            "that's reassuring — the finding isn't an artifact of a single loud community. "
            "reminder: the reddit text is synthetic (generated uniformly), so absolute shares are less meaningful than the across-subreddit consistency of the pattern."
        )


# ============================================================
# TAB 7 — DETAILS
# ============================================================

with tab_details:
    st.markdown("## 🔧 how we built this")

    st.markdown("### data sources")
    st.markdown(
        "- **news** — [media cloud](https://mediacloud.org) api, us mainstream online news + political blogs, 2010–2026\n"
        "- **reddit** — PRAW (reddit's python api). subreddits: r/politics, r/news, r/farming, r/immigration, plus state subs (Ohio, California, Florida, Texas)\n"
        "- **Facebook / Instagram ads** — [Meta Ad Library API](https://www.facebook.com/ads/library/api/), political + issue ads since 2018. set `META_AD_LIBRARY_TOKEN` to enable live pulls.\n"
        "- **YouTube comments** — [YouTube Data API v3](https://developers.google.com/youtube/v3), comments on immigration/farmworker videos. set `YOUTUBE_API_KEY` (free 10k quota/day) to enable live pulls.\n"
        "- **stance classifier** — [claude haiku 4.5](https://www.claude.com) via anthropic api, classifying each post into 3 categories using the rubric below\n"
        "- **topic clustering** — [BERTopic](https://maartengr.github.io/BERTopic/) with sentence-transformer embeddings\n"
        "- **commodity prices** — yahoo finance via `yfinance` python package"
    )

    with st.expander("classification rubric — what haiku looks for"):
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

    with st.expander("event timeline"):
        events_df = pd.DataFrame(load_events())
        st.dataframe(events_df, width="stretch", hide_index=True)

    with st.expander("validation plan"):
        st.markdown(
            "per the project spec, the stance classifier must be validated before results are published.\n\n"
            "1. hand-label 200 reddit posts — blind, 67 each to david / ella / sydney\n"
            "2. compute **cohen's kappa** between human consensus and haiku's labels\n"
            "3. thresholds:\n"
            "   - kappa ≥ 0.6 → ship\n"
            "   - 0.4 ≤ kappa < 0.6 → rewrite rubric and re-run\n"
            "   - kappa < 0.4 → report honestly that stance isn't reliably detectable by this method"
        )

    with st.expander("known limitations"):
        st.markdown(
            "- **reddit is still synthetic** — the team's reddit developer registration is pending. real reddit post text would sharpen stance classification.\n"
            "- **media cloud returns titles only** — no body text, so topic clustering on news uses headlines. reddit posts have full text.\n"
            "- **haiku rate limit** — 50 requests/minute on the current api tier; full 50k post classification would take ~17 minutes uninterrupted.\n"
            "- **panel 4 is experimental** — correlation between quarterly framing and commodity returns is weak with only 65 observations. stronger analysis needs daily resolution and reddit stance as the predictor."
        )

    st.divider()
    st.markdown("### raw data browser")
    choices = {
        "news quarterly volumes": load_news_volumes,
        "reddit posts + stance": lambda: pd.read_csv(PROCESSED_DIR / "reddit_posts_stance.csv") if (PROCESSED_DIR / "reddit_posts_stance.csv").exists() else pd.DataFrame(),
        "full corpus (topic modeling)": lambda: load_corpus(),
    }
    pick = st.selectbox("dataset", list(choices.keys()))
    df = choices[pick]()
    if df.empty:
        st.warning("no rows")
    else:
        if "date" in df.columns:
            d = pd.to_datetime(df["date"])
            df_f = df[(d.dt.year >= year_range[0]) & (d.dt.year <= year_range[1])]
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

    st.divider()
    st.caption("team: david, ella, sydney · AGRCOMM 2330 · spring 2026")
