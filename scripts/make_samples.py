"""
generate synthetic news + reddit datasets for demo mode.

this is DEMO DATA. it is not a real finding. the generator biases the era-level
keyword / stance / topic mix so the panels look legible when running without creds.
swap in real collectors for actual analysis.

run: python -m scripts.make_samples
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta

from common import SAMPLES_DIR, ensure_dirs

random.seed(42)

# ---------- era tuning ----------
# each era has:
#   weights: keyword-bucket mix for news + reddit
#   stance:  stance-label mix on reddit
#   topics:  topic-cluster mix

ERAS = [
    # name,             start,        end,          kw_right, kw_left, kw_neutral, stance_pro_enf, stance_pro_lab, stance_neutral, topic_mix
    ("pre_trump",       date(2010,1,1),  date(2016,10,31), 0.25, 0.35, 0.40, 0.30, 0.35, 0.35, "enforcement=0.35,economic=0.25,humanitarian=0.20,cropLoss=0.10,border=0.05,criminal=0.05"),
    ("trump_1",         date(2016,11,1), date(2020,2,29),  0.55, 0.20, 0.25, 0.45, 0.30, 0.25, "enforcement=0.40,border=0.25,criminal=0.15,economic=0.10,humanitarian=0.07,cropLoss=0.03"),
    ("covid",           date(2020,3,1),  date(2021,1,19),  0.25, 0.50, 0.25, 0.20, 0.50, 0.30, "essential=0.40,cropLoss=0.20,humanitarian=0.15,economic=0.15,enforcement=0.07,border=0.03"),
    ("biden",           date(2021,1,20), date(2024,11,4),  0.30, 0.40, 0.30, 0.30, 0.40, 0.30, "economic=0.25,humanitarian=0.20,enforcement=0.15,cropLoss=0.15,essential=0.15,border=0.10"),
    ("trump_2",         date(2024,11,5), date(2026,6,30),  0.60, 0.25, 0.15, 0.45, 0.35, 0.20, "deportation=0.35,cropLoss=0.20,enforcement=0.15,economic=0.12,humanitarian=0.10,criminal=0.08"),
]

# ---------- templates ----------
# sentences are assembled from: topic anchor + keyword term + stance cue + topic cue.
# we keep them plausible-looking but clearly synthetic if read closely.

KW_TERMS = {
    "right_loaded": [
        "illegal alien", "illegal immigrant", "illegals", "criminal alien",
        "border crisis", "mass deportation", "invasion",
    ],
    "left_loaded": [
        "undocumented worker", "undocumented immigrant", "undocumented",
        "immigrant worker", "immigrant labor", "essential worker",
        "farmworker", "farm worker",
    ],
    "neutral": [
        "migrant worker", "migrant labor", "agricultural worker",
        "seasonal worker", "H-2A worker", "guest worker",
    ],
}

STANCE_CUES = {
    "pro_enforcement": [
        "we need stricter enforcement at the border",
        "ICE should be doing more raids on these farms",
        "they're taking jobs from american workers",
        "this is a drain on our public services",
        "deport them all, even if it means higher food prices",
        "illegal is illegal, no matter the industry",
        "the wages stay low because of this cheap labor",
    ],
    "pro_immigrant_labor": [
        "our food system would collapse without these workers",
        "these are essential workers keeping america fed",
        "we need a real path to citizenship for farm labor",
        "the families being separated are human beings",
        "employers exploit them because of their legal status",
        "crop losses this year show how much we depend on them",
        "give them the visas they deserve",
    ],
    "neutral_mixed": [
        "complicated issue with no easy answers",
        "i see both sides of this",
        "what does the H-2A visa actually cover",
        "curious what the research says",
        "reporting here is from the associated press",
        "depends on the state and the crop",
    ],
}

TOPIC_CUES = {
    "enforcement":    ["ICE raids", "workplace audits", "e-verify", "border patrol"],
    "border":         ["southern border", "crossings", "migration surge", "border wall"],
    "criminal":       ["criminal record", "smuggling charges", "prosecution", "detention"],
    "economic":       ["wages", "labor costs", "economic contribution", "tax revenue"],
    "humanitarian":   ["family separation", "human rights", "detention conditions", "dreamers"],
    "cropLoss":       ["rotting crops", "harvest shortfall", "fields unpicked", "labor shortage"],
    "essential":      ["essential worker designation", "pandemic frontline", "critical infrastructure"],
    "deportation":    ["mass deportation", "removal operations", "deportation flights", "self-deport"],
}

FARM_ANCHORS = [
    "farm", "farmworkers on", "california farm", "florida citrus", "ohio dairy",
    "texas produce", "orchard", "field hands", "harvest crew", "H-2A visa program",
    "agricultural labor", "crop yields", "produce aisle",
]

SUBREDDITS = ["politics", "news", "farming", "immigration", "Ohio", "California", "Florida", "Texas"]

NEWS_DOMAINS = [
    "apnews.com", "reuters.com", "nytimes.com", "wsj.com", "foxnews.com",
    "npr.org", "washingtonpost.com", "cbsnews.com", "usatoday.com",
    "latimes.com", "miamiherald.com", "cleveland.com", "houstonchronicle.com",
]

# ---------- facebook ad sponsors ----------
# names mimic the kinds of PACs / advocacy groups that actually run immigration ads.
# the right-leaning vs left-leaning names map loosely onto stance — but not perfectly,
# because real sponsors sometimes run mixed-message buys.

FB_SPONSORS_RIGHT = [
    "Americans for Border Security", "Secure Our Nation PAC", "Enforcement First Coalition",
    "Stop The Invasion Fund", "American Workers First", "Border Patrol Support Committee",
    "Citizens for Immigration Reform", "Heartland Values PAC",
]
FB_SPONSORS_LEFT = [
    "Farmworker Justice Fund", "United We Dream Action", "Essential Workers Coalition",
    "Immigrant Rights Now", "Dignity for Dairy Workers", "Defend Families Together",
    "Agricultural Workers Alliance", "New Americans PAC",
]
FB_SPONSORS_NEUTRAL = [
    "Ag Policy Institute", "Rural America Forum", "US Farm Coalition",
    "H-2A Employers Association", "Food System Facts", "National Agricultural Outlook",
]

FB_CTA = ["DONATE NOW", "LEARN MORE", "SIGN THE PETITION", "JOIN US", "WATCH THE AD", "CHIP IN $5"]

FB_HEADLINE_TEMPLATES = {
    "pro_enforcement": [
        "Stop the {topic_cue}", "End the {kw_term} Crisis Now",
        "Secure Our Borders. Protect Our Jobs.", "Tell Congress: No More {kw_term}",
        "Enough is Enough: {topic_cue} Must End",
    ],
    "pro_immigrant_labor": [
        "These Workers Feed America", "Protect {kw_term} — Protect Our Food Supply",
        "Families, Not Felons", "Our Farms Can't Run Without Them",
        "Defend {kw_term} Rights Today",
    ],
    "neutral_mixed": [
        "What You Need to Know About the H-2A Program",
        "The Facts About {topic_cue}", "Inside the Ag Labor Debate",
        "Understanding {kw_term} in US Agriculture",
    ],
}

# ---------- youtube video topics + commenter styles ----------
# youtube comments skew shorter, more reactive, more emoji. stance cues are blunter.

YT_CHANNELS = [
    "PBS NewsHour", "Vice News", "Fox News", "CBS Evening News",
    "Farm Bureau Today", "Modern Farmer", "Univision News", "NowThis",
    "The Young Turks", "Daily Wire", "AP Archive", "Frontline PBS",
]

YT_VIDEO_HOOKS = [
    "ICE raids at {anchor}", "life for farmworkers at {anchor}",
    "inside a {anchor} deportation case", "why {anchor} can't find workers",
    "how H-2A actually works at {anchor}", "{anchor}: the human cost of enforcement",
    "Congress debates {kw_term} impact on {anchor}",
]

YT_COMMENT_STYLES = {
    "pro_enforcement": [
        "Finally someone saying it 👏", "This is exactly the problem!!",
        "Deport them all. No exceptions.", "Taking jobs from Americans is not OK.",
        "Enforce the law or we don't have a country.", "How is this even controversial",
    ],
    "pro_immigrant_labor": [
        "These people work harder than anyone I know ❤️",
        "Without them your grocery bill doubles. Period.",
        "Humans are not illegal.", "Path to citizenship NOW",
        "My grandpa came here this way. Give them a chance.",
        "This is heartbreaking to watch 💔",
    ],
    "neutral_mixed": [
        "Complicated issue. Not a simple fix.", "What's the actual H-2A cap right now?",
        "Both sides make points here.", "Interesting reporting, thanks for posting",
        "Would love to hear from an actual farmer on this",
        "Source on that stat?",
    ],
}

# ---------- era helpers ----------

def _era_for(d: date):
    for row in ERAS:
        name, start, end = row[0], row[1], row[2]
        if start <= d <= end:
            return row
    return ERAS[-1]


def _parse_topic_mix(s: str) -> list[tuple[str, float]]:
    out = []
    for chunk in s.split(","):
        name, w = chunk.split("=")
        out.append((name.strip(), float(w)))
    return out


def _weighted_pick(items: list[tuple[str, float]]) -> str:
    names, weights = zip(*items)
    return random.choices(names, weights=weights, k=1)[0]


# ---------- generators ----------

def _assemble_post(d: date, for_reddit: bool) -> tuple[str, str, str, str, str]:
    """returns (title, text, kw_bucket, stance, topic)."""
    era = _era_for(d)
    kw_bucket = random.choices(
        ["right_loaded", "left_loaded", "neutral"],
        weights=[era[3], era[4], era[5]],
        k=1,
    )[0]
    stance = random.choices(
        ["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"],
        weights=[era[6], era[7], era[8]],
        k=1,
    )[0]
    topic = _weighted_pick(_parse_topic_mix(era[9]))

    anchor = random.choice(FARM_ANCHORS)
    kw_term = random.choice(KW_TERMS[kw_bucket])
    stance_cue = random.choice(STANCE_CUES[stance])
    topic_cue = random.choice(TOPIC_CUES[topic])

    if for_reddit:
        title = f"{kw_term} and the {anchor} situation"
        body_bits = [
            f"The {kw_term} question keeps coming up around {anchor}.",
            f"Story about {topic_cue} - {stance_cue}.",
            random.choice([
                "thoughts?", "what do y'all think?", "this is nuts.",
                "been following this for a while.", "not sure how i feel tbh.",
            ]),
        ]
        text = " ".join(body_bits)
    else:
        # news headline + excerpt
        title_templates = [
            f"{topic_cue.title()} reported as {kw_term} debate intensifies",
            f"{anchor.title()} faces {topic_cue}; advocates cite {kw_term} concerns",
            f"Officials weigh {topic_cue} amid {kw_term} discussion",
        ]
        title = random.choice(title_templates)
        text = (
            f"{anchor.capitalize()} operators reported {topic_cue} this quarter. "
            f"Industry groups argue the {kw_term} framing misses key context. "
            f"{stance_cue.capitalize()}."
        )
    return title, text, kw_bucket, stance, topic


def generate_news(
    start: date = date(2010, 1, 1),
    end: date = date(2026, 6, 30),
    per_year: int = 500,
) -> list[dict]:
    rows = []
    year = start.year
    while year <= end.year:
        for _ in range(per_year):
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d < start or d > end:
                continue
            title, text, kw, stance, topic = _assemble_post(d, for_reddit=False)
            rows.append(
                {
                    "source": "synthetic_news",
                    "date": d.isoformat(),
                    "title": title,
                    "text": text,
                    "url": f"https://{random.choice(NEWS_DOMAINS)}/{d.year}/{d.month:02d}/{random.randint(1000,9999)}",
                    "true_bucket": kw,
                    "true_stance": stance,
                    "true_topic": topic,
                }
            )
        year += 1
    return rows


def generate_reddit(
    start: date = date(2015, 1, 1),
    end: date = date(2026, 6, 30),
    per_year: int = 4000,
) -> list[dict]:
    rows = []
    year = start.year
    while year <= end.year:
        # weight more recent years heavier to match the spec's sampling guidance
        multiplier = 1.0
        if year in (2024, 2025, 2026):
            multiplier = 2.0
        n = int(per_year * multiplier)
        for _ in range(n):
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d < start or d > end:
                continue
            title, text, kw, stance, topic = _assemble_post(d, for_reddit=True)
            rows.append(
                {
                    "source": "synthetic_reddit",
                    "date": d.isoformat(),
                    "subreddit": random.choice(SUBREDDITS),
                    "title": title,
                    "text": f"{title}\n{text}",
                    "url": f"https://reddit.com/r/{random.choice(SUBREDDITS)}/comments/{random.randint(100000,999999)}",
                    "score": random.randint(1, 500),
                    "true_bucket": kw,
                    "true_stance": stance,
                    "true_topic": topic,
                }
            )
        year += 1
    return rows


def generate_fb_ads(
    start: date = date(2018, 5, 1),  # meta ad library starts ~may 2018
    end: date = date(2026, 6, 30),
    per_year: int = 180,
) -> list[dict]:
    """synthetic political/issue ads about immigration + farm labor.
    ads are short, sponsor-driven, and run in bursts around election cycles."""
    rows = []
    year = start.year
    while year <= end.year:
        # election years get more ads (mirrors real ad-library volume pattern)
        multiplier = 2.2 if year in (2018, 2020, 2022, 2024, 2026) else 1.0
        n = int(per_year * multiplier)
        for _ in range(n):
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d < start or d > end:
                continue
            era = _era_for(d)
            kw_bucket = random.choices(
                ["right_loaded", "left_loaded", "neutral"],
                weights=[era[3], era[4], era[5]],
                k=1,
            )[0]
            stance = random.choices(
                ["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"],
                weights=[era[6], era[7], era[8]],
                k=1,
            )[0]
            topic = _weighted_pick(_parse_topic_mix(era[9]))
            kw_term = random.choice(KW_TERMS[kw_bucket])
            topic_cue = random.choice(TOPIC_CUES[topic])

            if stance == "pro_enforcement":
                sponsor = random.choice(FB_SPONSORS_RIGHT)
            elif stance == "pro_immigrant_labor":
                sponsor = random.choice(FB_SPONSORS_LEFT)
            else:
                sponsor = random.choice(FB_SPONSORS_NEUTRAL)

            headline = random.choice(FB_HEADLINE_TEMPLATES[stance]).format(
                kw_term=kw_term.title(), topic_cue=topic_cue.title()
            )
            body_cue = random.choice(STANCE_CUES[stance])
            text = f"{headline}\n\n{body_cue.capitalize()}. This {topic_cue} is why we're asking you to act. {random.choice(FB_CTA)}."

            # spend + impressions are reported as ranges in the real api
            spend_low = random.choice([100, 500, 1000, 5000, 10000, 50000])
            impr_low = spend_low * random.choice([30, 50, 80, 120])
            rows.append({
                "source": "synthetic_fb_ads",
                "date": d.isoformat(),
                "page_name": sponsor,
                "title": headline,
                "text": text,
                "spend_lower": spend_low,
                "spend_upper": spend_low * 5,
                "impressions_lower": impr_low,
                "impressions_upper": impr_low * 5,
                "url": f"https://www.facebook.com/ads/library/?id={random.randint(100000000000, 999999999999)}",
                "true_bucket": kw_bucket,
                "true_stance": stance,
                "true_topic": topic,
            })
        year += 1
    return rows


def generate_youtube_comments(
    start: date = date(2012, 1, 1),  # youtube api coverage practical floor
    end: date = date(2026, 6, 30),
    per_year: int = 600,
) -> list[dict]:
    """synthetic youtube comments on immigration / farmworker videos.
    shorter + more reactive than reddit. grouped under plausible video titles."""
    rows = []
    year = start.year
    while year <= end.year:
        # one 'video' every few weeks, each with a burst of comments
        n = per_year
        for _ in range(n):
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d < start or d > end:
                continue
            era = _era_for(d)
            kw_bucket = random.choices(
                ["right_loaded", "left_loaded", "neutral"],
                weights=[era[3], era[4], era[5]],
                k=1,
            )[0]
            stance = random.choices(
                ["pro_enforcement", "pro_immigrant_labor", "neutral_mixed"],
                weights=[era[6], era[7], era[8]],
                k=1,
            )[0]
            topic = _weighted_pick(_parse_topic_mix(era[9]))
            anchor = random.choice(FARM_ANCHORS)
            kw_term = random.choice(KW_TERMS[kw_bucket])

            video_title = random.choice(YT_VIDEO_HOOKS).format(anchor=anchor, kw_term=kw_term)
            channel = random.choice(YT_CHANNELS)
            comment = random.choice(YT_COMMENT_STYLES[stance])

            video_id = f"vid_{year}_{random.randint(100000, 999999)}"
            likes = random.randint(0, 2500)
            rows.append({
                "source": "synthetic_youtube",
                "date": d.isoformat(),
                "channel": channel,
                "video_title": video_title,
                "video_id": video_id,
                "title": video_title,
                "text": comment,
                "likes": likes,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "true_bucket": kw_bucket,
                "true_stance": stance,
                "true_topic": topic,
            })
        year += 1
    return rows


def _write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    ensure_dirs()
    news = generate_news()
    reddit = generate_reddit()
    fb_ads = generate_fb_ads()
    youtube = generate_youtube_comments()
    _write_csv(SAMPLES_DIR / "news.csv", news)
    _write_csv(SAMPLES_DIR / "reddit.csv", reddit)
    _write_csv(SAMPLES_DIR / "fb_ads.csv", fb_ads)
    _write_csv(SAMPLES_DIR / "youtube.csv", youtube)
    readme = SAMPLES_DIR / "README.md"
    readme.write_text(
        "# synthetic sample data\n\n"
        "these files are generated by `scripts/make_samples.py` for demo mode.\n"
        "they are NOT a real finding. era-level mix is hand-tuned so the panels look legible.\n"
        "swap in the real collectors for actual analysis.\n\n"
        f"- news.csv: {len(news)} rows, 2010-2026\n"
        f"- reddit.csv: {len(reddit)} rows, 2015-2026\n"
        f"- fb_ads.csv: {len(fb_ads)} rows, 2018-2026 (meta ad library starts 2018)\n"
        f"- youtube.csv: {len(youtube)} rows, 2012-2026\n"
    )
    print(f"wrote {len(news)} news, {len(reddit)} reddit, {len(fb_ads)} fb_ads, {len(youtube)} youtube to {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
