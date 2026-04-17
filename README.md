# discourse-shift

Three-panel analysis of public discourse on migrant farm labor, 2010-2026. Case study for AGRCOMM 2330.

## what it does

Three independent signals across the same event timeline:

- **Panel 1 — language:** keyword frequency over time. "illegal alien" vs "undocumented worker" vs "farmworker" etc, across news and reddit. stacked area chart.
- **Panel 2 — stance:** three-way classification of reddit posts (pro-enforcement / pro-immigrant-labor / neutral-mixed) via Claude Haiku 4.5. 100% stacked area.
- **Panel 3 — topic:** BERTopic clusters on the combined news + reddit corpus. heatmap of topic prevalence per year.

all three share the same overlay of policy events — Trump 2016, COVID/essential workers 2020, Biden 2021, Trump re-election 2024, mass deportation ops 2025. if all three panels break at the same hinge points, discourse is regime-driven. if they diverge, that tells us which part of public feeling is sticky vs reactive.

## quick start (demo mode, no creds needed)

```
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.make_samples   # generate synthetic demo data
python run.py                    # panels + combined figure + findings.md
```

outputs land in `output/`:
- `panel1_language.png`
- `panel2_stance.png`
- `panel3_topic.png`
- `three_panel.png`  ← the money shot for the presentation
- `findings.md`  ← data-driven writeup skeleton

## interactive dashboard

```
streamlit run app.py
```

opens an interactive plotly dashboard at http://localhost:8501 with:
- **overview** — combined three-panel figure
- **panel 1** — language tab with news / reddit / both toggle + era comparison table
- **panel 2** — stance tab with sample-posts viewer by classified label + rubric expander
- **panel 3** — topic tab with heatmap + topic-over-time line chart
- **data** — raw rows browser with year filter + CSV download
- year-range slider in the sidebar filters all tabs simultaneously

demo mode runs on synthetic samples with hand-tuned era shifts so the charts look legible. it is NOT a real finding.

## running on real data

copy `.env.example` to `.env` and fill in what you have. partial is fine — the pipeline skips collectors that lack creds.

```
cp .env.example .env
# edit .env ...
python run.py --collect          # pull live data into data/processed/
python run.py --live             # panel 2 calls haiku, panel 3 fits bertopic
```

what unlocks what:

| you set | unlocks |
|---|---|
| nothing | demo mode (synthetic samples, all panels render) |
| `ANTHROPIC_API_KEY` | panel 2 real stance classification via haiku |
| reddit client id/secret/UA | panel 2 real reddit posts (2023+) |
| `MEDIACLOUD_API_KEY` | panel 1 news 2010-2016 baseline |
| nothing (GDELT is free) | panel 1 news 2017+ |

## individual panels

```
python run.py --only panel1                  # panel 1 only
python run.py --only panel2 --live-stance    # panel 2 with real haiku calls
python run.py --only panel3 --live-topic     # panel 3 with real bertopic fit
python run.py --only combined                # just the combined figure
python run.py --limit 5000                   # subsample for speed
```

## validation (panel 2)

hand-label 200 reddit posts. david/ella/sydney each take 67 (ish).

```
python -m validation.make_hand_label_template   # writes validation/stance_labels.csv
# fill in the `human_label` column for the rows assigned to you
python run.py --only panel2 --live-stance        # classify full corpus
python -m validation.validate_stance             # cohen's kappa verdict
```

verdict:
- kappa >= 0.6 → ship
- kappa in [0.4, 0.6) → rewrite rubric + re-run
- kappa < 0.4 → stance is not reliably detectable with this method, say so honestly

## costs

panel 2 full run: claude haiku 4.5 at ~50k posts × ~500 input tokens + 5 output tokens ≈ $15-25 total. first run pays full cost; re-runs hit the sqlite cache and are free. the rubric is sent via prompt caching so repeated calls are ~90% cheaper than the list-price rate.

panel 3 fit: cpu-only bertopic on ~50k docs takes 5-10 min on apple silicon. gpu makes it faster but not needed.

gdelt + media cloud + reddit: free at the volumes we pull.

## repo layout

```
config/          yaml configs (events, keywords, rubric, sources)
collectors/      per-source data pulls (gdelt, mediacloud, reddit)
panels/          one module per analytical panel
validation/      kappa check for stance classifier + hand-label template
viz/             shared event overlay, combined figure
data/            raw / processed / samples / sqlite cache
output/          final PNGs and findings writeup (gitignored - regenerate via run.py)
scripts/         one-off helpers (make_samples, etc)
```

## how the 8-hour budget maps

session 1 (4h):
- [x] repo + configs + events.yaml
- [x] collectors (gdelt, media cloud, reddit)
- [x] panel 1 chart

session 2 (4h):
- [x] hand-label 200 posts
- [x] stance classification + kappa validation
- [x] panel 2 chart
- [x] bertopic + hand-labeling clusters
- [x] panel 3 chart
- [x] combined figure + findings writeup

if session 2 blows past 4h: ship panels 1+2, drop panel 3. still a strong finding.

## methodology

### keyword bucketing (panel 1)

every keyword term is pre-assigned to one of three buckets in `config/keywords.yaml`:

- **right_loaded / enforcement-framed:** `illegal alien`, `illegal immigrant`, `illegals`, `criminal alien`, `border crisis`, `mass deportation`, `invasion`
- **left_loaded / labor-framed:** `undocumented worker`, `undocumented immigrant`, `undocumented`, `immigrant worker`, `immigrant labor`, `essential worker`, `farmworker`, `farm worker`
- **neutral:** `migrant worker`, `migrant labor`, `agricultural worker`, `seasonal worker`, `H-2A`, `guest worker`

every term is required to co-occur with a topic anchor (`farmworker`, `farm worker`, `H-2A`, `agricultural worker`, `migrant worker`, `migrant labor`, `seasonal worker`) to count as "about migrant farm labor" rather than generic immigration coverage.

bucket design is deliberately **symmetric** per the project's bias-management rule (spec §10): each loaded right term has a loaded left counterpart. the neutral bucket exists so we can tell when coverage is just reporting vs actively framed.

### stance classification (panel 2)

three-way classification via claude haiku 4.5 against the rubric in `config/stance_rubric.yaml`:

- `pro_enforcement` — supports stricter enforcement / deportation / frames migrant labor as a problem
- `pro_immigrant_labor` — defends migrant workers / calls for legalization / frames enforcement as harmful
- `neutral_mixed` — reports without taking a side / mixed feelings / off-topic / spam

the rubric prompt is sent via anthropic prompt caching so repeated classifications share the same system prompt at a ~90% discount.

each post is classified independently; no context from other posts is used. the classifier is deliberately conservative — when indicators for both sides appear, or when stance is ambiguous, it returns `neutral_mixed` rather than guessing.

### topic modeling (panel 3)

BERTopic with `sentence-transformers/all-MiniLM-L6-v2` embeddings on the combined news + reddit corpus. clusters are hand-labeled after fitting, then mapped to eight canonical buckets:

- ICE / workplace enforcement
- border / migration flow
- deportation operations
- criminal framing
- economic contribution
- crop loss / labor shortage
- essential worker framing
- humanitarian / families

prevalence is reported as share-of-year: for each year, what fraction of the collected text belongs to each topic cluster.

### event overlay

all four panels share a single event timeline (`config/events.yaml`). hinge points:

- nov 2016 — trump elected (election)
- jan 2017 — travel ban / ICE enforcement expansion (enforcement)
- jun 2018 — family separation policy peak (enforcement)
- mar 2020 — COVID / farmworkers designated essential (pandemic)
- jan 2021 — biden inaugurated (election)
- may 2023 — title 42 ends (legal)
- nov 2024 — trump re-elected (election)
- jan 2025 — mass deportation ops begin (enforcement)

## validation

### panel 2 kappa protocol

per spec §6, panel 2 classifier must be validated before results are published:

1. `python -m validation.make_hand_label_template` → writes `validation/stance_labels.csv` with 200 stratified posts
2. team (david / ella / sydney) hand-labels 67ish posts each blind — no source or year visible
3. where any two disagree, discuss and resolve to a consensus human label
4. `python -m validation.validate_stance` computes cohen's kappa between consensus labels and haiku labels

thresholds:
- **kappa ≥ 0.6 → ship** the classifier as-is
- **kappa ∈ [0.4, 0.6) → rewrite** the rubric and re-run
- **kappa < 0.4 → stop and report honestly** that stance is not reliably detectable with this method

### bias management guardrails

- **symmetric keyword buckets** — every loaded right-coded term has a left-coded counterpart (spec §10)
- **symmetric rubric indicators** — same count of pro-enforcement and pro-immigrant-labor indicators
- **blind labeling** — hand-labelers see post text only, not source/year/subreddit

## limitations

- **reddit coverage gap:** pushshift public API was discontinued in 2023; historical 2010-2023 reddit access is via academic torrent dumps or arctic-shift. live data (2023+) is via PRAW with rate limits.
- **media cloud is metadata-only:** their v4 api returns article titles + URLs but not body text. panel 3 topic modeling on news uses titles only. body-text scraping from source URLs is possible but slow and rate-limited.
- **haiku rate limits:** free-tier anthropic accounts are limited to 50 requests/minute. classifying the full 50k reddit corpus takes ~17 minutes uninterrupted at this rate. spend estimate: ~$3-5 with prompt caching.
- **GDELT is currently disabled** due to aggressive rate limiting on the free DOC 2.0 API; media cloud covers the full 2010-2026 range reliably.
- **panel 4 (futures) is experimental:** correlation between quarterly news framing and quarterly commodity returns is weak (65 observations, low variance). see `docs/future_work.md` for a richer analysis plan.

## team

david, ella, sydney. AGRCOMM 2330.
