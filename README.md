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

## team

david, ella, sydney. AGRCOMM 2330.
