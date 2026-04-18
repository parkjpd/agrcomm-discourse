# future work

stuff we thought about but didn't have time to build out in the 8-hour budget.

## panel 4 (ag futures) — make it real

the current version is bonus / experimental. it works but there are only 8 policy events × 5 tickers, which is not enough to make causal claims. what we'd need to tighten it:

- daily news + reddit stance index instead of quarterly
- rolling correlations between enforcement framing and returns, not just pre/post event windows
- weather / citrus greening / avian flu as control variables (FCOJ is very sensitive to florida freezes)
- granger causality test on whether discourse leads prices or the other way
- out-of-sample backtest on 2024-2026 after training on 2010-2023

this probably becomes a senior-thesis-sized project rather than a class case study.

### candidate commodities if we extend

labor-intensive crops where enforcement risk would matter most:

- fresh produce (lettuce, strawberries, tomatoes, citrus) — no liquid futures though, would need USDA AMS spot prices
- dairy — class III milk futures (CME), dairy labor heavy
- sugar — sugar #11 (ICE)
- cattle — live + feeder cattle (CME), some labor exposure
- orange juice — FCOJ (ICE), already in the current panel
- cotton — some labor but mostly mechanized now
- wheat / corn / soy — skip, fully mechanized

cleanest signal will probably stay in FCOJ and class III milk.

## other things worth building

- **Reddit comments, not just posts.** Comments are 10-20x higher volume than submissions and give finer-grained stance per topic. Needs its own PRAW rate budget though.
- **Spanish-language press.** La Opinión, Univision, Telemundo are directly relevant and not in Media Cloud's default english collections. MC has spanish collections — worth a panel 1b.
- **State-level breakdown.** California, Florida, Texas, Ohio all have different migrant labor dynamics. Our reddit subs are already split by state, but we could also split news by source metadata.
- **Time-lag analysis.** Does news lead Reddit, or does Reddit lead news? Lagged cross-correlation between panel 1 language share and panel 2 stance share at the weekly level would tell us which platform is the leading indicator.
- **Validation on the new platforms.** Cohen's kappa check for the stance classifier on FB ads and YouTube comments, separate from reddit, since the text styles are very different.
