# future work

ideas captured during the initial build that are worth circling back to.

## panel 4 (extension) — discourse vs ag futures markets

hypothesis: spikes in enforcement-framed discourse (panel 1 right_loaded share, or panel 2 pro_enforcement share) precede or coincide with moves in agricultural commodity futures tied to labor-intensive crops. if enforcement rhetoric is predictive of crop-loss pricing, that's a meaningful economic signal.

### candidate commodities

labor-intensive crops most exposed to migrant-labor enforcement risk:
- **fresh produce / specialty crops** — lettuce, strawberries, tomatoes, citrus. no liquid futures market, use proxies.
- **dairy** — class III milk futures (CME), dairy labor heavy.
- **sugar** — sugar #11 (ICE).
- **cattle** — live cattle / feeder cattle (CME). some labor exposure.
- **cotton** — less manual but tracked.
- **orange juice** — FCOJ (ICE). florida citrus is H-2A heavy.
- **wheat / corn / soybeans** — probably low signal; mostly mechanized.

the cleanest signal will probably be in FCOJ and class III milk since those two tie directly to high-migrant-labor crops with liquid futures.

### data source

- yahoo finance (`yfinance` python package) — free, daily OHLCV for most futures tickers
- FRED — for agricultural price indices
- alternatives: quandl / nasdaq-data, tradingview api, CBOT / CME direct

### analysis

- align daily / weekly futures prices with the quarterly discourse series from panels 1-3
- compute rolling correlation between enforcement-framed share and price returns
- event study: what happens to FCOJ prices in the 10 trading days after a policy-event date (jan 2017 travel ban, march 2020 essential-worker designation, jan 2025 mass deportation)
- granger causality test: does discourse lead prices, or vice versa

### build estimate

~2-3 hours.
- collector: `collectors/futures.py` pulling yfinance close prices for 5-6 tickers (~30 min)
- `panels/panel4_futures.py` — overlay price chart on panel 1 timeline with 2nd y-axis (~60 min)
- event study analysis script (~60 min)
- writeup paragraph in findings.md (~30 min)

### caveats

- fresh produce has no futures market, so for lettuce / strawberries / tomatoes we'd need spot price data from USDA AMS (agricultural marketing service) — free but messier
- causality is hard. strong correlation just means "the same events drive both." panel findings already cover that qualitatively.
- 2026 futures data will be sparse since we're mid-year

## other ideas

- **social media comments, not just posts**: reddit comments per submission can be scraped via PRAW and give a finer-grained view of stance than posts alone. the volume is 10-20x higher than posts but dedicated comment scraping needs its own rate budget.
- **spanish-language press**: la opinión, univision, telemundo news are relevant and underrepresented in MC's english-only default collections. MC has spanish collections available — worth adding as a panel 1b.
- **state-level breakdown**: california / florida / texas / ohio all have different migrant-labor dynamics. the reddit subs are already split, but for news we could split MC results by source-location metadata.
- **time-lag analysis**: does news lead reddit or vice versa? lagged cross-correlation between news.language_share and reddit.language_share at the weekly level.
