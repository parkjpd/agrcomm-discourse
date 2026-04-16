# discourse-shift

Three-panel analysis of public discourse on migrant farm labor, 2010-2026. Case study for AGRCOMM 2330.

## what it does

Three independent signals across the same timeline:

- **Panel 1 — language:** keyword frequency (illegal alien vs undocumented worker vs farmworker etc) across news + reddit
- **Panel 2 — stance:** three-way classification (pro-enforcement / pro-immigrant-labor / neutral-mixed) on reddit posts
- **Panel 3 — topic:** BERTopic clusters showing which sub-topics dominate each era

All three share the same event overlay (see `config/events.yaml`): Trump election 2016, COVID/essential workers 2020, Biden transition 2021, Trump re-election 2024, mass deportation ops 2025.

## setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in the keys you have
```

## run

```bash
# full pipeline (collectors -> panels -> combined figure)
python run.py

# just panel 1 (fastest, no LLM or heavy deps)
python run.py --only panel1

# demo mode - uses synthetic samples, no API calls
python run.py --demo
```

Output lands in `output/` as PNGs plus a findings writeup.

## what you need

- **Panel 1 only:** nothing. GDELT DOC 2.0 is free and no-auth. Covers 2017+.
- **Panel 1 with 2010-2016 baseline:** Media Cloud API key (free academic signup).
- **Panel 2:** `ANTHROPIC_API_KEY` for Haiku stance classification.
- **Reddit live:** create a Reddit app, fill in `REDDIT_CLIENT_ID` / `_SECRET` / `_USER_AGENT`.
- **Deep historical GDELT (pre-2017 or faster bulk):** GCP project with BigQuery enabled.

Demo mode runs without any of these using synthetic data in `data/samples/`.

## repo layout

```
config/          yaml configs (events, keywords, rubric, sources)
collectors/      per-source data pulls (gdelt, mediacloud, reddit)
panels/          one module per analytical panel
validation/      kappa check for stance classifier + hand-label template
viz/             shared event overlay, combined figure
data/            raw / processed / samples / sqlite cache
output/          final PNGs and findings writeup
scripts/         one-off helpers
```

## team

David, Ella, Sydney. AGRCOMM 2330.
