import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

// ============================================================
// POSTER CONTENT
// ============================================================

const TITLE_LINE_1 = "Almost half the people feeding America";
const TITLE_LINE_2 = "could be deported tomorrow.";
const SUBTITLE = "How do migrant workers in the U.S. produce farming industry influence economic trends, shape immigration policy, and produce diverse perspectives on the role of immigrant labor in American agriculture?";
const AUTHORS = ["David Park", "Ella Russell", "Sydney Beiting"];

// Reddit stance by political era (project scrape, 3,000 posts, Haiku classification)
const STANCE_BY_ERA = [
  { era: "Pre-Trump",  proEnforce: 17.9, proLabor: 14.5, neutral: 67.6 },
  { era: "Trump I",    proEnforce: 27.2, proLabor: 9.0,  neutral: 63.8 },
  { era: "COVID",      proEnforce: 15.6, proLabor: 15.3, neutral: 69.1 },
  { era: "Biden",      proEnforce: 17.5, proLabor: 16.8, neutral: 65.7 },
  { era: "Trump II",   proEnforce: 26.4, proLabor: 13.2, neutral: 60.5 },
];

const STATS = [
  { num: "40–50%", label: "of US farmworkers are undocumented", src: "USDA ERS" },
  { num: "$3–7B", label: "crop losses, 2025 CA ICE raids", src: "USDA FTS-382" },
  { num: "5–12%", label: "produce price jump after the raids", src: "FreshFruitPortal" },
  { num: "8×", label: "farmworker families more food-insecure than the public", src: "UCS · NAWS" },
  { num: "$17.5k", label: "average farmworker family annual income", src: "Farmworker Justice" },
  { num: "1.9M", label: "farmworkers + kin unsure of their next meal", src: "UCS, 2023" },
];

const TIMELINE = [
  { date: "1940s–60s", t: "Bracero Program", d: "4–5M Mexican workers under a binational labor agreement." },
  { date: "1950s–60s", t: "Chavez & the NFWA", d: "First major farmworker civil rights reforms." },
  { date: "2002", t: "Homeland Security Act", d: "INS dissolved, ICE created." },
  { date: "2016", t: "First Trump term", d: "Enforcement tightens nationwide. Start of study period." },
  { date: "2020", t: "COVID-19", d: "Farmworkers labeled essential. Framing briefly sympathetic." },
  { date: "Jan 2025", t: "Mass deportation ops", d: "CA ag labor −40%. Produce prices +5–12%. Harvests rot.", hot: true },
];

const WORKFORCE = [
  { name: "Undocumented", value: 42, color: "#c8502b" },
  { name: "Documented immigrant", value: 19, color: "#6b4e2e" },
  { name: "US-born", value: 39, color: "#1a3a5c" },
];

const DOMINO = [
  { label: "Framing",  desc: "Enforcement language rises online.",                 ex: "Pro-enforcement share +10 pts" },
  { label: "Policy",   desc: "Federal enforcement escalates.",                      ex: "Jan 2025: mass deportation ops" },
  { label: "Labor",    desc: "Workforces collapse in weeks.",                       ex: "CA farm labor −40% overnight" },
  { label: "Farms",    desc: "Harvests rot. Family farms lose the season.",         ex: "$3–7B in crop losses" },
  { label: "Prices",   desc: "Cost gets passed to the register.",                   ex: "Produce +5–12% after raids" },
  { label: "Families", desc: "Working-class households absorb the hit, both ways.", ex: "The hands that pick go hungry" },
];

const RECS = [
  { who: "Farmers",      short: "A lost harvest isn't volatility — it's a closed farm.", long: "88% of US farms are family-owned, median operator age 58. Labor disruption isn't a line-item risk — it's existential. Planning needs to account for political cycles the way it already does for weather cycles." },
  { who: "Policymakers", short: "The cost of enforcement lands on the poorest households.", long: "When produce prices climb and farms fail, the hit doesn't fall on the people making the policy. It falls on the families picking the crops and the families buying the groceries — often the same families." },
  { who: "Voters",       short: "The food on your table was picked by someone going hungry.", long: "Up to 82% of farmworker families are food insecure. 1.1–1.9 million people who grow America's food don't know where their next meal will come from. Ask what a policy actually does to them." },
  { who: "Media",        short: "Small vocabulary shifts compound into decades of opinion.", long: "Terms like \u201Cmass deportation\u201D grew from 3.6% to 9% of farm coverage across five political eras. Framing doesn't just describe the story — it becomes the story for the readers who encounter it." },
];

const SOURCES = [
  "USDA ERS. Farm labor (2025).",
  "USDA ERS. Fruit and Tree Nuts Outlook, FTS-382 (2025).",
  "USDA ERS. Legal status of hired crop farmworkers, 1991–2022.",
  "National Center for Farmworker Health. Facts about farmworkers (2023).",
  "Reznickova, A. Union of Concerned Scientists. How Many Farmworkers Are Food Insecure? (2023).",
  "Farmworker Justice. Hunger amidst plenty: Food assistance in farmworker communities (2016).",
  "National Farm Worker Ministry. Harvest of Justice: Farm Workers & Food Justice (2021).",
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
// STYLE
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
const sans  = { fontFamily: 'DM Sans, "Helvetica Neue", system-ui, sans-serif' };
const mono  = { fontFamily: 'JetBrains Mono, "SF Mono", Monaco, Consolas, monospace' };

// ============================================================
// PRIMITIVES
// ============================================================

function SectionHeading({ children, kicker }) {
  return (
    <div style={{ marginBottom: 10 }}>
      {kicker && (
        <div style={{ ...mono, fontSize: 8, letterSpacing: "0.2em", color: C.terra, marginBottom: 2, textTransform: "uppercase" }}>
          {kicker}
        </div>
      )}
      <div style={{ ...serif, fontSize: 18, fontWeight: 600, color: C.navy, lineHeight: 1.1, letterSpacing: "-0.01em" }}>
        {children}
      </div>
      <div style={{ height: 2, width: 30, background: C.terra, marginTop: 6 }} />
    </div>
  );
}

function FigCaption({ num, title, source }) {
  return (
    <div style={{ ...mono, fontSize: 9, color: C.muted, letterSpacing: "0.04em", marginTop: 6, lineHeight: 1.35 }}>
      <span style={{ color: C.terra, fontWeight: 500 }}>Fig. {num}</span> · {title}
      {source && <span style={{ fontStyle: "italic" }}> · {source}</span>}
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{ background: "#1f1f1f", color: "#f5efe3", padding: "8px 12px", fontSize: 11, fontFamily: mono.fontFamily, border: `1px solid ${C.terra}` }}>
      <div style={{ color: C.terra, marginBottom: 4, fontWeight: 500 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.name}: <span style={{ color: "#f5efe3" }}>{p.value}%</span></div>
      ))}
    </div>
  );
}

function Fig({ src, alt, num, title, source }) {
  return (
    <div style={{ background: C.panel, border: `1px solid ${C.rule}`, padding: 10, marginBottom: 12 }}>
      <img
        src={src}
        alt={alt}
        style={{ width: "100%", height: "auto", display: "block", objectFit: "contain" }}
      />
      <FigCaption num={num} title={title} source={source} />
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

        {/* ============ 3-COLUMN BODY ============ */}
        <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.5fr 1.2fr", gap: 0, padding: "24px 40px", borderBottom: `1px solid ${C.rule}` }}>

          {/* ----- COLUMN 1 : SCOPE / METHODS / TIMELINE ----- */}
          <div style={{ paddingRight: 24, borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="01 · Scope">Project Scope</SectionHeading>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 14px" }}>
              Three independent analyses of one question: how U.S. migrant farm labor shapes the food supply, the policy that moves around it, and the cost that hits working-class families.
              Methods combined news framing from MediaCloud, Reddit/Facebook stance classification via Claude Haiku, and commodity event studies from 2010 to 2026.
            </p>

            <SectionHeading kicker="02 · Methods">Methods</SectionHeading>
            <ul style={{ fontSize: 10.5, lineHeight: 1.5, color: C.ink, margin: "0 0 14px", paddingLeft: 14 }}>
              <li><b>News framing:</b> ~3k articles tagged pre-Trump → Trump II.</li>
              <li><b>Stance:</b> 3,000 Reddit posts classified pro-enforcement / pro-labor / mixed.</li>
              <li><b>Topic prevalence:</b> 8 keyword cohorts, annual share 2010–2025.</li>
              <li><b>Markets:</b> event-window returns on FCOJ, sugar, milk, coffee, cattle, cotton.</li>
              <li><b>Human impact:</b> triangulated USDA ERS, NCFH, NAWS, UCS, Farmworker Justice.</li>
            </ul>

            <SectionHeading kicker="03 · Context">A Century of Labor Policy</SectionHeading>
            <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
              {TIMELINE.map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <div style={{
                    flexShrink: 0, width: 8, height: 8, borderRadius: "50%",
                    background: t.hot ? C.terra : C.navy2,
                    boxShadow: t.hot ? `0 0 0 3px rgba(200,80,43,0.2)` : "none",
                    marginTop: 6,
                  }} />
                  <div>
                    <div style={{ ...mono, fontSize: 9, color: C.terra, letterSpacing: "0.05em" }}>{t.date}</div>
                    <div style={{ ...serif, fontSize: 12, fontWeight: 600, color: C.navy, lineHeight: 1.15 }}>{t.t}</div>
                    <div style={{ fontSize: 10, lineHeight: 1.4, color: C.ink }}>{t.d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ----- COLUMN 2 : DISCOURSE + MARKETS (David) ----- */}
          <div style={{ padding: "0 24px", borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Finding 1 · David Park">The narrative shifts. Working families pay the bill.</SectionHeading>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 10px" }}>
              Pro-enforcement framing on social platforms jumped 10 points between Obama and Trump. Reddit pro-enforcement stance moved from 17.9% pre-Trump to 26–27% in both Trump terms. Terms like <b>"mass deportation"</b> grew from 3.6% to 9% of farm coverage. The story changed online before the policy did.
            </p>

            <div style={{ background: C.panel, border: `1px solid ${C.rule}`, padding: 12, marginBottom: 12 }}>
              <div style={{ ...serif, fontSize: 13, fontWeight: 600, color: C.navy, marginBottom: 2 }}>
                Pro-enforcement stance doubled under both Trump terms.
              </div>
              <div style={{ fontSize: 10.5, color: C.muted, marginBottom: 8, lineHeight: 1.4 }}>
                Reddit posts about migrant farm labor, grouped by political era. Hover any bar for the exact share.
              </div>
              <div style={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={STANCE_BY_ERA} margin={{ top: 8, right: 12, left: -14, bottom: 4 }} barCategoryGap="18%">
                    <CartesianGrid strokeDasharray="2 2" stroke={C.rule} vertical={false}/>
                    <XAxis dataKey="era" stroke={C.muted} tick={{ fontSize: 10, fontFamily: mono.fontFamily }} axisLine={{ stroke: C.rule }} tickLine={false}/>
                    <YAxis stroke={C.muted} tick={{ fontSize: 9, fontFamily: mono.fontFamily }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} domain={[0, 35]}/>
                    <Tooltip content={<ChartTooltip/>} cursor={{ fill: "rgba(15,37,64,0.05)" }}/>
                    <Bar dataKey="proEnforce" name="Pro-enforcement" fill={C.terra} radius={[2,2,0,0]}/>
                    <Bar dataKey="proLabor"   name="Pro-labor"       fill={C.navy2} radius={[2,2,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <FigCaption
                num="1"
                title="Reddit stance on migrant farm labor, by political era"
                source="project scrape · Claude Haiku classification, n=3,000 posts"
              />
            </div>

            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "14px 0 10px" }}>
              Markets moved too. Orange juice futures dropped 35% that same winter — most of that was Brazilian supply recovery, not U.S. enforcement. But that's the point: <b>hedge funds can price in a coming shock. A family at the grocery store can't.</b> When produce prices climbed after the raids, working-class households ate the cost. When family farms lost harvests, no one covered the loss.
            </p>

            <Fig
              src="/figures/assignment_fcoj_deep_dive.png"
              alt="FCOJ vs news enforcement framing 2010–2026"
              num="2"
              title="FCOJ (orange juice) vs U.S. news enforcement framing, 2010–2026"
              source="Yahoo Finance OJ=F + MediaCloud · honest read: correlation, not causation"
            />
          </div>

          {/* ----- COLUMN 3 : WORKFORCE + YIELDS (Sydney + Ella) ----- */}
          <div style={{ paddingLeft: 24 }}>
            <SectionHeading kicker="Finding 2 · Sydney Beiting">The hands that pick America's food can't afford to buy it.</SectionHeading>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 8px" }}>
              <b>61%</b> of the U.S. farm workforce is immigrant. 78% self-identify as Hispanic; 63% are from Mexico. Average farmworker family income sits between <b>$17.5–20k</b> — below the federal poverty line for a family of four.
            </p>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 12px" }}>
              Between <b>1.1 and 1.9 million</b> farmworkers and their children don't know where their next meal will come from. They die from heat-related illness at rates 20% higher than workers in other industries. 78% live in crowded housing regardless of whether the unit meets code.
            </p>

            <div style={{ background: C.panel, border: `1px solid ${C.rule}`, padding: 10, marginBottom: 8, height: 210 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={WORKFORCE} dataKey="value" cx="38%" cy="50%" innerRadius={44} outerRadius={82} paddingAngle={2} strokeWidth={2} stroke="#faf6ec">
                    {WORKFORCE.map((e, i) => <Cell key={i} fill={e.color}/>)}
                  </Pie>
                  <Legend
                    layout="vertical" verticalAlign="middle" align="right" iconType="square"
                    wrapperStyle={{ fontFamily: "DM Sans", fontSize: 11, paddingRight: 8 }}
                    formatter={(v, e) => <span style={{ color: C.ink }}>{v}: {e.payload.value}%</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ ...mono, fontSize: 9, color: C.muted, letterSpacing: "0.04em", marginBottom: 18 }}>
              <span style={{ color: C.terra, fontWeight: 500 }}>Fig. 3</span> · U.S. farm workforce composition, 2022 · <span style={{ fontStyle: "italic" }}>USDA ERS</span>
            </div>

            <SectionHeading kicker="Finding 3 · Ella Russell">When deportations rise, harvests rot.</SectionHeading>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 8px" }}>
              You can't pick produce without pickers. The 2025 California raids cut farm labor up to <b>40%</b> overnight: strawberries stayed on vines, citrus fell unpicked, <b>$3–7B</b> in crop losses within a single quarter, produce prices jumped <b>5–12%</b> at the register.
            </p>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: 0 }}>
              For family farms — 88% of U.S. farms, median operator age 58 — this isn't volatility. It's existential. A single lost harvest can end a generational operation. And the 5–12% produce price jump lands on working-class grocery shoppers who had nothing to do with the policy.
            </p>
          </div>
        </div>

        {/* ============ CONCLUSIONS + RECS + BIBLIO STRIP ============ */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.2fr 1fr", gap: 0, padding: "20px 40px", borderBottom: `1px solid ${C.rule}` }}>

          <div style={{ paddingRight: 24, borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Conclusions">Six steps. Same people at the bottom.</SectionHeading>
            <p style={{ fontSize: 11.5, lineHeight: 1.55, color: C.ink, margin: "0 0 10px" }}>
              A framing shift online becomes an enforcement policy, becomes a rotting harvest, becomes a grocery-bill increase — and every step lands on the same working-class households. Policy, markets, and media circle back. The bill does not.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 6, marginTop: 8 }}>
              {DOMINO.map((d, i) => (
                <div key={i} style={{
                  background: i === DOMINO.length - 1 ? C.terra : C.navy,
                  color: "#fff",
                  padding: "8px 10px",
                  position: "relative",
                }}>
                  <div style={{ ...mono, fontSize: 8, letterSpacing: "0.15em", opacity: 0.6, textTransform: "uppercase" }}>Step {i+1}</div>
                  <div style={{ ...serif, fontSize: 14, fontWeight: 600, marginTop: 2, marginBottom: 4 }}>{d.label}</div>
                  <div style={{ fontSize: 9.5, lineHeight: 1.35, opacity: 0.92 }}>{d.desc}</div>
                  <div style={{ ...mono, fontSize: 8, color: i === DOMINO.length - 1 ? "#fff" : C.terra, marginTop: 5, letterSpacing: "0.03em" }}>{d.ex}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ padding: "0 24px", borderRight: `1px solid ${C.rule}` }}>
            <SectionHeading kicker="Recommendations">What to do about it</SectionHeading>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {RECS.map((r, i) => (
                <div key={i} style={{ borderLeft: `2px solid ${C.terra}`, paddingLeft: 10 }}>
                  <div style={{ ...mono, fontSize: 8, letterSpacing: "0.15em", color: C.terra, textTransform: "uppercase" }}>For {r.who}</div>
                  <div style={{ ...serif, fontSize: 12, fontWeight: 600, color: C.navy, lineHeight: 1.2, margin: "2px 0 3px" }}>{r.short}</div>
                  <div style={{ fontSize: 9.5, lineHeight: 1.45, color: C.ink }}>{r.long}</div>
                </div>
              ))}
            </div>
            <p style={{ ...serif, fontStyle: "italic", fontSize: 13, lineHeight: 1.4, color: C.navy, margin: "14px 0 0", paddingTop: 10, borderTop: `1px solid ${C.rule}` }}>
              Policy moves markets. Markets move framing. Framing moves opinion. Opinion moves the next policy. But the bill lands in one place — <span style={{ fontStyle: "normal", color: C.terra }}>on the families who pick America's food, grow America's food, and can't afford to buy it.</span>
            </p>
          </div>

          <div style={{ paddingLeft: 24 }}>
            <SectionHeading kicker="Bibliography">Bibliography</SectionHeading>
            <ol style={{ ...mono, fontSize: 8.5, lineHeight: 1.5, color: C.ink, margin: 0, paddingLeft: 18 }}>
              {SOURCES.map((s, i) => <li key={i} style={{ marginBottom: 3 }}>{s}</li>)}
            </ol>
          </div>
        </div>

        {/* ============ FOOTER / LOGO ============ */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 40px", background: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <img src="/osu-logo.png" alt="The Ohio State University" style={{ height: 44, width: "auto", display: "block" }} />
            <div style={{ fontSize: 10, color: C.muted, lineHeight: 1.4, borderLeft: `1px solid ${C.rule}`, paddingLeft: 14 }}>
              College of Food, Agricultural,<br/>and Environmental Sciences
            </div>
          </div>
          <div style={{ ...mono, fontSize: 10, letterSpacing: "0.15em", color: C.muted, textTransform: "uppercase", textAlign: "right", lineHeight: 1.5 }}>
            <div>Acknowledgements: Dr. Annie Specht, instructor</div>
            <div>AGRCOMM 2330 · Issue Case Study · April 2026</div>
          </div>
        </div>

      </div>

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

