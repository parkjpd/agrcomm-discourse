import { useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from "recharts";

// ============================================================
// POSTER CONTENT
// ============================================================

const TITLE_LINE_1 = "The raids hit.";
const TITLE_LINE_2 = "The markets moved first.";
const SUBTITLE = "How migrant workers in the U.S. produce farming industry shape economic trends, immigration policy, and the discourse that moves both.";
const AUTHORS = ["David Park", "Ella Russell", "Sydney Beiting"];

const STATS = [
  { num: "40–50%", label: "US farmworkers undocumented", src: "USDA ERS" },
  { num: "$3–7B", label: "2025 CA raid crop losses", src: "FTS-382" },
  { num: "−35.4%", label: "FCOJ, 30 days post-raid", src: "Yahoo OJ=F" },
  { num: "+10 pt", label: "pro-enforcement framing Δ", src: "project scrape" },
  { num: "78%", label: "farmworkers Hispanic", src: "NCFH 2023" },
  { num: "20%", label: "families below poverty", src: "NAWS 2019" },
];

const TIMELINE = [
  { date: "1940s–60s", t: "Bracero Program", d: "4–5M Mexican workers under a binational labor agreement." },
  { date: "1950s–60s", t: "Chavez & the NFWA", d: "First major farmworker civil rights reforms." },
  { date: "2002", t: "Homeland Security Act", d: "INS dissolved, ICE created." },
  { date: "2016", t: "First Trump term", d: "Enforcement tightens nationwide. Start of study period." },
  { date: "2020", t: "COVID-19", d: "Farmworkers labeled essential. Framing briefly sympathetic." },
  { date: "Jan 2025", t: "Mass deportation ops", d: "CA ag labor −40%. FCOJ −35%. Produce prices +5–12%.", hot: true },
];

const WORKFORCE = [
  { name: "Undocumented", value: 42, color: "#c8502b" },
  { name: "Documented immigrant", value: 19, color: "#6b4e2e" },
  { name: "US-born", value: 39, color: "#1a3a5c" },
];

const RECS = [
  { who: "Farmers", short: "Plan for election-cycle labor volatility.", long: "Enforcement costs are priced in weeks before policy hits. Workforce planning needs political calendar risk, not just weather." },
  { who: "Policymakers", short: "Markets price raids before they happen.", long: "Ignoring that turns every enforcement action into a quiet tax on consumers." },
  { who: "Voters", short: "Look past how platforms frame it.", long: "Ask what the underlying policy does to food supply, labor, and grocery prices. Framing shifts before facts do." },
  { who: "Media", short: "Word choice compounds.", long: "Small vocabulary shifts (3.6% → 9% enforcement framing) reshape opinion over a decade." },
];

const SOURCES = [
  "USDA ERS. Farm labor (2025).",
  "USDA ERS. Fruit and Tree Nuts Outlook, FTS-382 (2025).",
  "USDA ERS. Legal status of hired crop farmworkers, 1991–2022.",
  "National Center for Farmworker Health. Facts about farmworkers (2023).",
  "KFF. Immigration restrictions on the U.S. agricultural workforce (2025).",
  "Kostandini, Mykerezi & Escalante. AJAE 96(1), 172–192 (2014).",
  "Martin, P. Immigration and farm labor. Giannini Foundation (2024).",
  "Hill & Scott. Foreign-born farm labor sensitivity. KC Fed (2025).",
  "Castillo et al. Annu. Rev. Public Health 42(1), 257–276 (2021).",
  "Pew Research Center. Views of Trump admin. immigration actions (2025).",
  "NBC News. U.S. immigration tracker (2025).",
  "Park, D. AGRCOMM discourse pipeline. github.com/parkjpd/agrcomm-discourse.",
];

// ============================================================
// STYLE TOKENS
// ============================================================

const C = {
  bg: "#ffffff",
  panel: "#faf6ec",
  ink: "#1f1f1f",
  navy: "#0f2540",
  navy2: "#1a3a5c",
  terra: "#c8502b",
  brown: "#6b4e2e",
  rule: "#d9cfba",
  muted: "#6b6b6b",
  scarlet: "#bb0000",
};

const serif = { fontFamily: 'Fraunces, "Iowan Old Style", Palatino, Georgia, serif' };
const sans = { fontFamily: 'DM Sans, "Helvetica Neue", system-ui, sans-serif' };
const mono = { fontFamily: 'JetBrains Mono, "SF Mono", Monaco, Consolas, monospace' };

// ============================================================
// PRIMITIVES
// ============================================================

function SectionHeading({ children, kicker }) {
  return (
    <div style={{ marginBottom: 10 }}>
      {kicker && (
        <div style={{ ...mono, fontSize: 8, letterSpacing: "0.2em", color: C.terra, marginBottom: 2 }}>
          {kicker.toUpperCase()}
        </div>
      )}
      <div style={{ ...serif, fontSize: 18, fontWeight: 600, color: C.navy, lineHeight: 1.1, letterSpacing: "-0.01em" }}>
        {children}
      </div>
      <div style={{ height: 2, width: 30, background: C.terra, marginTop: 6 }} />
    </div>
  );
}

function FigCaption({ num, title, src }) {
  return (
    <div style={{ ...mono, fontSize: 8, color: C.muted, letterSpacing: "0.04em", marginTop: 4, lineHeight: 1.3 }}>
      <span style={{ color: C.terra, fontWeight: 500 }}>Fig. {num}</span> · {title}
      {src && <span style={{ fontStyle: "italic" }}> · {src}</span>}
    </div>
  );
}

function Fig({ src, alt, num, title, source }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.rule}`, padding: 8, marginBottom: 10 }}>
      <img src={src} alt={alt} style={{ width: "100%", height: "auto", display: "block" }} />
      <FigCaption num={num} title={title} src={source} />
    </div>
  );
}

// ============================================================
// MAIN
// ============================================================

export default function App() {
  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=DM+Sans:opsz,wght@9..40,300..700&family=JetBrains+Mono:wght@400;500&display=swap";
    document.head.appendChild(link);
    return () => { try { document.head.removeChild(link); } catch(e){} };
  }, []);

  return (
    <div style={{ background: "#e8e2d4", minHeight: "100vh", padding: "24px 0", ...sans }}>
      <div className="poster" style={{
        background: C.bg,
        color: C.ink,
        width: "min(1600px, calc(100vw - 48px))",
        margin: "0 auto",
        boxShadow: "0 8px 40px -10px rgba(15,37,64,0.25)",
        position: "relative",
      }}>

        {/* ============ HEADER STRIP ============ */}
        <div style={{ background: C.scarlet, color: "#fff", padding: "10px 32px", display: "flex", justifyContent: "space-between", alignItems: "center", ...mono, fontSize: 11, letterSpacing: "0.08em" }}>
          <div style={{ textTransform: "uppercase" }}>
            The Ohio State University <span style={{ opacity: 0.7, margin: "0 10px" }}>·</span> College of Food, Agricultural, and Environmental Sciences <span style={{ opacity: 0.7, margin: "0 10px" }}>·</span> Dept. of ACEL
          </div>
          <div style={{ background: "#fff", color: C.scarlet, padding: "3px 10px", fontWeight: 600, letterSpacing: "0.12em" }}>
            AGRCOMM 2330
          </div>
        </div>

        {/* ============ TITLE BLOCK ============ */}
        <div style={{ padding: "28px 40px 24px", borderBottom: `1px solid ${C.rule}` }}>
          <div style={{ ...mono, fontSize: 10, letterSpacing: "0.2em", color: C.terra, textTransform: "uppercase", marginBottom: 10 }}>
            Issue Case Study · Spring 2026
          </div>
          <h1 style={{ ...serif, fontSize: 54, lineHeight: 0.98, letterSpacing: "-0.028em", color: C.navy, fontWeight: 500, margin: 0 }}>
            {TITLE_LINE_1}{" "}
            <em style={{ color: C.terra, fontWeight: 400 }}>{TITLE_LINE_2}</em>
          </h1>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 14, gap: 40 }}>
            <p style={{ ...serif, fontStyle: "italic", fontSize: 16, lineHeight: 1.4, color: C.ink, maxWidth: 820, margin: 0 }}>
              {SUBTITLE}
            </p>
            <div style={{ ...mono, fontSize: 11, color: C.ink, textAlign: "right", letterSpacing: "0.05em", lineHeight: 1.6, whiteSpace: "nowrap" }}>
              {AUTHORS.map((a, i) => (
                <div key={i}><span style={{ color: C.terra, marginRight: 6 }}>·</span>{a}</div>
              ))}
            </div>
          </div>
        </div>

        {/* ============ STATS STRIP ============ */}
        <div style={{ background: C.panel, borderBottom: `1px solid ${C.rule}`, padding: "14px 40px", display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 20 }}>
          {STATS.map((s, i) => (
            <div key={i} style={{ borderLeft: i > 0 ? `1px solid ${C.rule}` : "none", paddingLeft: i > 0 ? 16 : 0 }}>
              <div style={{ ...serif, fontSize: 26, fontWeight: 500, color: C.terra, lineHeight: 1, letterSpacing: "-0.02em" }}>{s.num}</div>
              <div style={{ fontSize: 10, lineHeight: 1.3, color: C.ink, marginTop: 4 }}>{s.label}</div>
              <div style={{ ...mono, fontSize: 8, letterSpacing: "0.12em", color: C.muted, marginTop: 3, textTransform: "uppercase" }}>{s.src}</div>
            </div>
          ))}
        </div>

        {/* ============ 4-COLUMN BODY ============ */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr 1.2fr 1fr", gap: 0, padding: "24px 40px", borderBottom: `1px solid ${C.rule}` }}>

          {/* ----- COLUMN 1 : SCOPE ----- */}
          <div style={{ paddingRight: 20, borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="01 · Scope">Project Scope</SectionHeading>
            <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 12px" }}>
              Three independent analyses of the same question: how U.S. migrant farm labor shapes economic trends, policy, and public discourse from 2010 to 2026.
              The team combined news framing from MediaCloud, Reddit/Facebook stance classification via Claude Haiku, and agricultural commodity futures event studies.
            </p>

            <SectionHeading kicker="02 · Methods">Methods</SectionHeading>
            <ul style={{ fontSize: 10.5, lineHeight: 1.45, color: C.ink, margin: "0 0 12px", paddingLeft: 14 }}>
              <li><b>News framing:</b> ~3k articles tagged pre-Trump → Trump II.</li>
              <li><b>Stance:</b> 3,000 Reddit posts classified pro-enforce / pro-labor / mixed.</li>
              <li><b>Topic prevalence:</b> 8 keyword cohorts, annual share 2010–2025.</li>
              <li><b>Markets:</b> event-window returns on FCOJ, sugar, milk, coffee, cattle, cotton.</li>
              <li><b>Sensitivity:</b> labor-exposure index × discourse correlation.</li>
            </ul>

            <SectionHeading kicker="03 · Context">A Century of Labor Policy</SectionHeading>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {TIMELINE.map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                  <div style={{
                    flexShrink: 0, width: 8, height: 8, borderRadius: "50%",
                    background: t.hot ? C.terra : C.navy2,
                    boxShadow: t.hot ? `0 0 0 3px rgba(200,80,43,0.2)` : "none",
                    marginTop: 5,
                  }} />
                  <div>
                    <div style={{ ...mono, fontSize: 9, color: C.terra, letterSpacing: "0.05em" }}>{t.date}</div>
                    <div style={{ ...serif, fontSize: 12, fontWeight: 600, color: C.navy, lineHeight: 1.15 }}>{t.t}</div>
                    <div style={{ fontSize: 10, lineHeight: 1.35, color: C.ink }}>{t.d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ----- COLUMN 2 : DISCOURSE (David) ----- */}
          <div style={{ padding: "0 20px", borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Finding 1 · David Park">Discourse shifted years before policy did.</SectionHeading>
            <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 12px" }}>
              News-side framing held steady from 2010 through early 2024 — enforcement-framed coverage ranged only 2.5% → 9% across five eras.
              Social media moved sharper and earlier: Reddit pro-enforcement stance jumped from 17.9% pre-Trump to 26–27% in both Trump terms.
              Topic prevalence tells the cleanest story: “deportation” peaked at <b>34.7% of 2025 discourse</b>, “essential” peaked at 33.4% in 2020 — the vocabulary tracks the political regime.
            </p>

            <Fig
              src="/figures/panel1_language.png"
              alt="News framing by era"
              num="1a"
              title="News framing, pre-Trump → Trump II"
              source="MediaCloud · n≈3k articles"
            />
            <Fig
              src="/figures/panel3_topic.png"
              alt="Topic prevalence timeline"
              num="1b"
              title="Topic prevalence, 2010–2025"
              source="project scrape"
            />
          </div>

          {/* ----- COLUMN 3 : MARKETS (David) ----- */}
          <div style={{ padding: "0 20px", borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Finding 2 · David Park">Markets priced it in before the news ran it.</SectionHeading>
            <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 12px" }}>
              FCOJ futures dropped <b>−35.4%</b> in the 30 days after Jan 2025 deportation ops — the largest single event-window shift in the dataset.
              The effect scales with labor exposure: FCOJ (exposure 0.95) shows the strongest negative correlation with enforcement framing; coffee (0.90 global, but US-policy-insensitive) shows zero correlation — a clean falsification check.
              Corn and soybeans, fully mechanized, move with macro noise only.
            </p>

            <Fig
              src="/figures/assignment_fcoj_deep_dive.png"
              alt="FCOJ deep dive"
              num="2a"
              title="FCOJ event-window returns, Dec 2024 – Feb 2025"
              source="Yahoo Finance OJ=F"
            />
            <Fig
              src="/figures/assignment_sensitivity_scatter.png"
              alt="Labor exposure vs discourse correlation"
              num="2b"
              title="Labor exposure × discourse sensitivity"
              source="project event study"
            />
          </div>

          {/* ----- COLUMN 4 : WORKFORCE (Sydney) + YIELDS (Ella) ----- */}
          <div style={{ paddingLeft: 20 }}>
            <SectionHeading kicker="Finding 3 · Sydney Beiting">Immigrants are the workforce, not a supplement.</SectionHeading>
            <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 10px" }}>
              USDA 2022 data shows <b>42%</b> undocumented + <b>19%</b> documented immigrants = 61% of the U.S. farm workforce. 78% self-identify as Hispanic, 63% from Mexico.
              20% of farmworker families live below the federal poverty line; a North Carolina housing study found 78% of farmworker households in crowded conditions regardless of whether the unit meets code.
            </p>

            <div style={{ background: C.panel, border: `1px solid ${C.rule}`, padding: 8, marginBottom: 10, height: 170 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={WORKFORCE} dataKey="value" cx="38%" cy="50%" innerRadius={35} outerRadius={65} paddingAngle={2} strokeWidth={2} stroke="#faf6ec">
                    {WORKFORCE.map((e, i) => <Cell key={i} fill={e.color}/>)}
                  </Pie>
                  <Legend
                    layout="vertical" verticalAlign="middle" align="right" iconType="square"
                    wrapperStyle={{ fontFamily: "DM Sans", fontSize: 10, paddingRight: 4 }}
                    formatter={(v, e) => <span style={{ color: C.ink }}>{v}: {e.payload.value}%</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <FigCaption num="3" title="US farm workforce composition, 2022" src="USDA ERS" />

            <div style={{ marginTop: 16 }}>
              <SectionHeading kicker="Finding 4 · Ella Russell">When deportations rise, yields fall.</SectionHeading>
              <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 10px" }}>
                With 40–50% of the produce workforce undocumented, 2025 California ICE raids cut farm labor up to 40% overnight. Outcome: <b>$3–7B</b> in crop losses and a 5–12% retail produce price jump. Farmers and consumers both absorb the cost.
              </p>
              <Fig
                src="/figures/assignment_event_waterfall.png"
                alt="Event-window returns by ticker"
                num="4"
                title="Event-window returns across commodities"
                source="project event study"
              />
            </div>
          </div>
        </div>

        {/* ============ CONCLUSIONS + RECS + BIBLIO STRIP ============ */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.2fr 1fr", gap: 0, padding: "20px 40px", borderBottom: `1px solid ${C.rule}` }}>

          <div style={{ paddingRight: 20, borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Conclusions">Not a political story. A chain reaction.</SectionHeading>
            <p style={{ fontSize: 11, lineHeight: 1.5, color: C.ink, margin: "0 0 8px" }}>
              Policy moves markets. Markets move framing. Framing moves opinion. Opinion moves the next policy.
              The chain is directional and, on this dataset, measurable: FCOJ drops within weeks of enforcement action; Reddit stance shifts lead mainstream news framing by 6–12 months; labor-exposed commodities move on labor-specific political news while mechanized ones do not.
            </p>
            <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
              {["Policy","Markets","Framing","News","Prices","People"].map((step, i, a) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{
                    ...mono, fontSize: 9, letterSpacing: "0.08em",
                    padding: "4px 8px",
                    background: i === a.length-1 ? C.terra : C.navy,
                    color: "#fff",
                    textTransform: "uppercase",
                  }}>{step}</span>
                  {i < a.length-1 && <span style={{ color: C.terra }}>→</span>}
                </div>
              ))}
            </div>
          </div>

          <div style={{ padding: "0 20px", borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Recommendations">What to do about it</SectionHeading>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {RECS.map((r, i) => (
                <div key={i} style={{ borderLeft: `2px solid ${C.terra}`, paddingLeft: 8 }}>
                  <div style={{ ...mono, fontSize: 8, letterSpacing: "0.15em", color: C.terra, textTransform: "uppercase" }}>For {r.who}</div>
                  <div style={{ ...serif, fontSize: 12, fontWeight: 600, color: C.navy, lineHeight: 1.2, margin: "2px 0 3px" }}>{r.short}</div>
                  <div style={{ fontSize: 9.5, lineHeight: 1.4, color: C.ink }}>{r.long}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ paddingLeft: 20 }}>
            <SectionHeading kicker="Bibliography">Bibliography</SectionHeading>
            <ol style={{ ...mono, fontSize: 8.5, lineHeight: 1.45, color: C.ink, margin: 0, paddingLeft: 18 }}>
              {SOURCES.map((s, i) => <li key={i} style={{ marginBottom: 3 }}>{s}</li>)}
            </ol>
          </div>
        </div>

        {/* ============ FOOTER / LOGO ============ */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 40px", background: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <OsuBlockO />
            <div style={{ ...sans, lineHeight: 1.2 }}>
              <div style={{ ...serif, fontSize: 15, fontWeight: 600, color: C.ink, letterSpacing: "0.02em" }}>THE OHIO STATE UNIVERSITY</div>
              <div style={{ fontSize: 10, color: C.muted }}>College of Food, Agricultural, and Environmental Sciences</div>
            </div>
          </div>
          <div style={{ ...mono, fontSize: 10, letterSpacing: "0.15em", color: C.muted, textTransform: "uppercase", textAlign: "right", lineHeight: 1.5 }}>
            <div>Acknowledgements: Dr. Annie Specht, instructor</div>
            <div>AGRCOMM 2330 · Issue Case Study · April 2026</div>
          </div>
        </div>

      </div>

      {/* print helpers */}
      <style>{`
        @media print {
          body { background: #fff !important; }
          .poster { box-shadow: none !important; width: 100% !important; }
          @page { size: 17in 11in; margin: 0.25in; }
        }
      `}</style>
    </div>
  );
}

// ============================================================
// OSU BLOCK O (SVG approximation)
// ============================================================

function OsuBlockO() {
  return (
    <svg width="50" height="40" viewBox="0 0 100 80" xmlns="http://www.w3.org/2000/svg" aria-label="OSU Block O">
      <rect x="2" y="14" width="96" height="52" rx="6" fill="#bb0000"/>
      <rect x="18" y="26" width="64" height="28" rx="3" fill="#ffffff"/>
    </svg>
  );
}
