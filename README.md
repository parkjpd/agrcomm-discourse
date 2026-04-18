# agrcomm-discourse

AGRCOMM 2330 case study. How have the ways we talk about migrant farm labor in the US changed 2010-2026? Team: David, Ella, Sydney.

## the questions we wanted to answer

1. Does mainstream news vocabulary change when the president changes?
2. Do Reddit users' opinions shift the same way news does?
3. Do the specific topics people argue about track specific events?

Plus one bonus: when the conversation gets loud about enforcement, do farm commodity prices move?

## quick start

```
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.make_samples   # synthetic demo data
python run.py                    # runs all panels
streamlit run app.py             # opens dashboard at localhost:8501
```

Demo mode runs on synthetic data so the dashboard always renders. Those are not real findings, they're just there so the charts aren't broken. Plug in API keys for the real thing (see below).

## running with real data

Copy `.env.example` to `.env`, fill in what you have, and add `--live` to run.py. Whatever isn't set falls back to synthetic.

| key | what it unlocks |
|---|---|
| `ANTHROPIC_API_KEY` | panel 2 stance classification via Claude Haiku |
| `MEDIACLOUD_API_KEY` | real news 2010-2026 |
| `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | real Reddit posts |
| `META_AD_LIBRARY_TOKEN` | real Facebook + Instagram political ads since 2018 |
| `YOUTUBE_API_KEY` | real YouTube comments |

## repo layout

```
config/       yaml configs (events, keywords, rubric, sources)
collectors/   one module per data source
panels/       one module per analytical panel
viz/          shared plotly builders + event overlay
app.py        streamlit dashboard
run.py        pipeline entry point
validation/   hand-label template + kappa check for panel 2
scripts/      helpers (synthetic data, chart export)
data/         raw / processed / samples / sqlite cache
output/       PNGs + findings.md (regenerated every run)
```

## methodology, short version

**Panel 1 (news language).** Every keyword in `config/keywords.yaml` is sorted into right-loaded ("illegal alien", "mass deportation"), left-loaded ("farmworker", "undocumented worker"), or neutral ("H-2A", "migrant worker"). Each term has to co-occur with a farm-labor anchor or it doesn't count — otherwise we'd just be measuring generic immigration coverage. We kept the same number of terms on each loaded side so the chart isn't rigged.

**Panel 2 (Reddit stance).** Each post goes through Claude Haiku 4.5 with the rubric in `config/stance_rubric.yaml`. Three labels: pro-enforcement, pro-immigrant-labor, neutral-mixed. Same indicator count on each side.

Validation: we each hand-label ~67 out of 200 stratified posts, then compute Cohen's kappa between the three-way human consensus and Haiku. Ship at kappa ≥ 0.6, revise below that.

**Panel 3 (topics).** BERTopic on the combined news + Reddit corpus, then we hand-labeled the resulting clusters into 8 buckets: enforcement, border, deportation, criminal, economic, crop loss, essential worker, humanitarian.

**Events timeline.** One file (`config/events.yaml`), same vertical lines on every chart. The hinge points we care about: Trump elected 2016, travel ban + ICE expansion Jan 2017, family separation peak 2018, COVID / essential-worker designation March 2020, Biden inaugurated 2021, Title 42 ends May 2023, Trump re-elected Nov 2024, mass deportation ops Jan 2025.

## what we found

Full writeup in `output/findings.md` (auto-generated each run). Short version:

- News vocabulary is sticky. Enforcement-framed language only grew from 3.6% to 9% of farm-labor coverage across 5 political eras.
- Reddit opinion is reactive. Pro-enforcement share jumped from ~17% during Obama/Biden/COVID to ~27% during both Trump terms. About a 10 percentage point swing.
- Topics respond fastest. "Essential worker" framing was 33% of all 2020 discourse during COVID. "Deportation operations" was 34.7% of 2025 after ICE raids began.
- Markets reacted too. FCOJ (orange juice futures) dropped 35% in the 30 days after January 2025 mass deportation ops kicked off.

## limitations to be honest about

- Our Reddit, FB ads, and YouTube data is synthetic until our developer tokens come through. The Haiku classifier runs on top of synthetic text, so the Reddit stance numbers are directional, not authoritative.
- Media Cloud returns article titles only, so our topic modeling on news is headlines-only.
- The futures panel has only 8 policy events × 5 tickers. That's correlation, not causation.

## for the class presentation

```
python -m scripts.export_assignment_charts
```

Drops three slide-ready PNGs into `output/assignment_*.png` that map onto David's row of the evidence table. The dashboard itself also has a camera icon on every plotly chart that saves a PNG.

## team

David, Ella, Sydney. AGRCOMM 2330, spring 2026.
