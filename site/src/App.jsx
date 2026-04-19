import { useState, useEffect } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, ReferenceLine } from "recharts";
import { ArrowRight, ChevronDown, Play, Pause, RotateCcw, ExternalLink } from "lucide-react";

import fcojWeekly from "./data/fcoj_weekly.json";
import framingWeekly from "./data/framing_weekly.json";
import yieldVsDeportations from "./data/yield_vs_deportations.json";

// ============================================================
// DATA
// ============================================================

const STATS = [
  { num: "40–50%", label: "of US farmworkers are undocumented", src: "USDA ERS" },
  { num: "$3–7B", label: "crop losses, 2025 California ICE raids", src: "USDA FTS-382" },
  { num: "−35%", label: "FCOJ futures, 30 days post-raid", src: "Yahoo Finance OJ=F" },
  { num: "+10 pts", label: "pro-enforcement framing, Obama → Trump", src: "project scrape" },
  { num: "78%", label: "of US farmworkers self-identify as Hispanic", src: "NCFH 2023" },
  { num: "20%", label: "of farmworker families below poverty line", src: "NAWS 2019–20" },
];

const TIMELINE = [
  { date: "1940s–60s", title: "Bracero Program", desc: "4–5M Mexican workers brought to US farms and railways under a binational labor agreement." },
  { date: "1950s–60s", title: "Chavez & the NFWA", desc: "Cesar Chavez and the National Farm Workers Association push the first major farmworker civil rights reforms." },
  { date: "2002", title: "Homeland Security Act", desc: "Federal immigration enforcement restructured. INS dissolved, ICE created." },
  { date: "2016", title: "First Trump term", desc: "Immigration enforcement tightens nationwide. Start of our study period." },
  { date: "2020", title: "COVID-19", desc: "Farmworkers officially labeled essential. Public framing of migrant labor briefly shifts sympathetic." },
  { date: "Jan 2025", title: "Mass deportation operations", desc: "California ag labor drops 40%. FCOJ futures drop 35% in 30 days. Produce prices up 5–12%.", hot: true },
];

// FCOJ + framing data come from the agrcomm-discourse repo. see scripts/export_site_data.py.
// weekly samples Dec 1 2024 through Feb 23 2025, aligned on Sundays so the Jan 19 mark lines up with the policy event.
const FCOJ_DATA = fcojWeekly.map((r, i) => ({
  ...r,
  framing: framingWeekly[i]?.framing ?? null,
  mark: r.date === "Jan 19" ? "raids begin" : undefined,
}));

const YIELD_DATA = yieldVsDeportations;

const WORKFORCE = [
  { name: "Undocumented", value: 42, color: "#c8502b" },
  { name: "Documented immigrant", value: 19, color: "#6b4e2e" },
  { name: "US-born", value: 39, color: "#1a3a5c" },
];

const STAKEHOLDERS = [
  {
    name: "Farmers",
    short: "Running out of labor.",
    desc: "Median age 58. Mostly male (63.7%), mostly white (95.4%). Risk-averse. Care about yields, input costs, and reliable labor.",
    concern: "Every raid is a bet on whether the next harvest will have pickers.",
  },
  {
    name: "Immigrant Workers",
    short: "Living under pressure.",
    desc: "Mostly Hispanic (78%), majority from Mexico (63%). A mix of undocumented workers and H-2A visa holders. Family-oriented.",
    concern: "Wages, housing, mental health, and family stability are the daily variables.",
  },
  {
    name: "Legislators",
    short: "Caught between donors and voters.",
    desc: "Median age 57.5, mostly non-POC. Care about constituents, committee assignments, and whoever is backing them.",
    concern: "Immigration is more useful as a wedge than as a working problem to solve.",
  },
  {
    name: "Voting Citizens",
    short: "Learning it from social.",
    desc: "~174 million registered. Party-polarized. Increasingly informed by social media rather than traditional news.",
    concern: "What feels urgent online usually arrived in the grocery store weeks earlier.",
  },
];

const RECS = [
  {
    who: "Farmers",
    short: "Prepare for election-cycle labor volatility.",
    long: "The economic cost of enforcement starts priced-in weeks before the policy hits. Budget and workforce planning should now include political calendar risk, not just weather.",
    color: "#0f2540",
  },
  {
    who: "Policymakers",
    short: "Markets price raids before they happen.",
    long: "Ignoring that turns every enforcement action into a quiet tax on consumers. Labor policy written without market awareness is written for political theater, not economic outcome.",
    color: "#c8502b",
  },
  {
    who: "Voters",
    short: "Look past how platforms frame it.",
    long: "Ask what the underlying policy actually does to food supply, farm labor, and grocery prices. The framing shifts before the facts do.",
    color: "#6b4e2e",
  },
  {
    who: "Media",
    short: "Word choice compounds.",
    long: "Small vocabulary shifts (3.6% to 9% enforcement framing) reshape public opinion over a decade. Framing decisions aren't neutral just because they're small.",
    color: "#1a3a5c",
  },
];

const DOMINO_CHAIN = [
  { label: "Policy", desc: "Enforcement action announced or escalated.", example: "Jan 2025: mass deportation ops begin" },
  { label: "Markets", desc: "Futures traders price in a labor shortage.", example: "FCOJ −35% within 30 days" },
  { label: "Framing", desc: "Social media vocabulary shifts toward enforcement language.", example: "Pro-enforcement share jumps 10 pts" },
  { label: "News", desc: "Traditional media catches up and amplifies the new framing.", example: "\"Deportation ops\" = 34.7% of 2025 coverage" },
  { label: "Prices", desc: "Grocery prices rise as supply tightens.", example: "Produce prices up 5–12%" },
  { label: "People", desc: "Workers, farmers, and families at the grocery store pay the cost.", example: "The end of the chain" },
];

const SOURCES = [
  { cite: "USDA ERS. Farm labor (2025).", url: "https://www.ers.usda.gov/topics/farm-economy/farm-labor" },
  { cite: "USDA ERS. Fruit and Tree Nuts Outlook, FTS-382 (2025).", url: "https://esmis.nal.usda.gov/sites/default/release-files/h989r3203/js958f26z/5999q355s/FTS-382.pdf" },
  { cite: "USDA ERS. Legal status of hired crop farmworkers, 1991–2022." },
  { cite: "National Center for Farmworker Health. Facts about farmworkers (2023).", url: "https://www.ncfh.org/wp-content/uploads/2025/04/facts_about_farmworkers_fact_sheet_1.10.23-1.pdf" },
  { cite: "KFF. Potential implications of immigration restrictions on the US agricultural workforce (2025).", url: "https://www.kff.org/racial-equity-and-health-policy/potential-implications-of-immigration-restrictions-on-the-u-s-agricultural-workforce/" },
  { cite: "Kostandini, Mykerezi & Escalante. AJAE 96(1), 172–192 (2014)." },
  { cite: "Martin, P. Immigration and farm labor. Giannini Foundation (2024)." },
  { cite: "Hill & Scott. Foreign-born farm labor sensitivity. Kansas City Fed (2025)." },
  { cite: "Castillo et al. Annu. Rev. Public Health 42(1), 257–276 (2021)." },
  { cite: "Pew Research Center. Views of Trump administration immigration actions (2025).", url: "https://www.pewresearch.org/politics/2025/06/17/americans-have-mixed-to-negative-views-of-trump-administration-immigration-actions/" },
  { cite: "NBC News. US immigration tracker (arrests, detentions, border crossings).", url: "https://www.nbcnews.com/data-graphics/us-immigration-tracker-follow-arrests-detentions-border-crossings-rcna189148" },
  { cite: "Park, D. AGRCOMM discourse pipeline.", url: "https://github.com/parkjpd/agrcomm-discourse" },
];

// ============================================================
// TOOLTIP
// ============================================================

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: "#1f1f1f",
      color: "#f5efe3",
      padding: "8px 12px",
      fontSize: "11px",
      fontFamily: "JetBrains Mono, monospace",
      border: "1px solid #c8502b",
      letterSpacing: "0.02em",
    }}>
      <div style={{ color: "#c8502b", marginBottom: "4px", fontWeight: 500 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: <span style={{ color: "#f5efe3" }}>{p.value}{p.unit || ""}</span>
        </div>
      ))}
    </div>
  );
};

// ============================================================
// MAIN
// ============================================================

export default function App() {
  const [activeTab, setActiveTab] = useState("ella");
  const [expandedTL, setExpandedTL] = useState(null);
  const [flippedCard, setFlippedCard] = useState(null);
  const [expandedRec, setExpandedRec] = useState(null);
  const [dominoStep, setDominoStep] = useState(-1);
  const [dominoPlaying, setDominoPlaying] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400..700;1,9..144,400..700&family=DM+Sans:opsz,wght@9..40,300..700&family=JetBrains+Mono:wght@400;500&display=swap";
    document.head.appendChild(link);
    return () => { try { document.head.removeChild(link); } catch(e){} };
  }, []);

  useEffect(() => {
    if (!dominoPlaying) return;
    if (dominoStep >= DOMINO_CHAIN.length - 1) {
      setDominoPlaying(false);
      return;
    }
    const t = setTimeout(() => setDominoStep(s => s + 1), 1400);
    return () => clearTimeout(t);
  }, [dominoPlaying, dominoStep]);

  const playDomino = () => { setDominoStep(0); setDominoPlaying(true); };
  const resetDomino = () => { setDominoStep(-1); setDominoPlaying(false); };
  const scroll = (id) => { document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }); };

  const serif = { fontFamily: 'Fraunces, "Iowan Old Style", Palatino, Georgia, serif' };
  const sans = { fontFamily: 'DM Sans, "Helvetica Neue", system-ui, sans-serif' };
  const mono = { fontFamily: 'JetBrains Mono, "SF Mono", Monaco, Consolas, monospace' };

  return (
    <div style={{ background: "#f5efe3", color: "#1f1f1f", ...sans, minHeight: "100vh" }}>

      <nav className="sticky top-0 z-50 backdrop-blur" style={{
        background: "rgba(245,239,227,0.88)",
        borderBottom: "1px solid #d9cfba",
        ...mono,
      }}>
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between text-xs">
          <div style={{ color: "#c8502b", letterSpacing: "0.15em" }} className="uppercase font-medium">
            AGRCOMM 2330
          </div>
          <div className="hidden md:flex gap-5 text-[10px] uppercase tracking-widest" style={{ color: "#6b6b6b" }}>
            {[
              ["Context", "context"],
              ["Findings", "findings"],
              ["Chain", "chain"],
              ["Stakeholders", "stakeholders"],
              ["Recommendations", "recs"],
              ["Sources", "sources"],
            ].map(([label, id]) => (
              <button key={id} onClick={() => scroll(id)} className="hover:text-[#c8502b] transition">
                {label}
              </button>
            ))}
          </div>
          <div style={{ color: "#6b6b6b", fontSize: "10px" }} className="uppercase tracking-widest">
            Spring 2026
          </div>
        </div>
      </nav>

      <section className="max-w-6xl mx-auto px-6 pt-16 pb-20">
        <div style={mono} className="text-xs uppercase tracking-widest mb-8 flex items-center gap-4">
          <span style={{ color: "#c8502b" }}>Issue Case Study</span>
          <span style={{ flex: 1, height: 1, background: "#d9cfba" }}></span>
          <span style={{ color: "#6b6b6b" }}>April 2026</span>
        </div>
        <h1 style={{ ...serif, fontSize: "clamp(44px, 7vw, 88px)", lineHeight: 0.98, letterSpacing: "-0.025em", color: "#0f2540", fontWeight: 500 }}>
          The raids hit.<br/>
          The markets <em style={{ color: "#c8502b", fontWeight: 400 }}>moved first.</em>
        </h1>
        <p style={{ ...serif, fontStyle: "italic", fontSize: "clamp(16px, 2vw, 22px)", lineHeight: 1.4, color: "#1f1f1f", maxWidth: "720px" }} className="mt-8">
          How migrant workers in the U.S. produce farming industry shape economic trends, immigration policy, and the discourse that moves both.
        </p>
        <div style={mono} className="mt-10 text-xs uppercase tracking-widest">
          <span style={{ color: "#1f1f1f", fontWeight: 500 }}>David Park</span>
          <span style={{ color: "#6b6b6b", margin: "0 10px" }}>·</span>
          <span style={{ color: "#1f1f1f", fontWeight: 500 }}>Ella Russell</span>
          <span style={{ color: "#6b6b6b", margin: "0 10px" }}>·</span>
          <span style={{ color: "#1f1f1f", fontWeight: 500 }}>Sydney Beiting</span>
          <span style={{ color: "#6b6b6b", margin: "0 14px" }}>|</span>
          <span style={{ color: "#6b6b6b" }}>The Ohio State University</span>
        </div>
        <button onClick={() => scroll("context")}
          className="mt-14 flex items-center gap-2 text-xs uppercase tracking-widest hover:gap-3 transition-all"
          style={{ ...mono, color: "#c8502b" }}>
          Start reading <ArrowRight size={14}/>
        </button>
      </section>

      <section id="context" style={{ borderTop: "1px solid #d9cfba", borderBottom: "1px solid #d9cfba", background: "#faf6ec" }}>
        <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-8">
          {STATS.map((s, i) => (
            <div key={i} style={{ borderLeft: i > 0 ? "1px solid #d9cfba" : "none" }} className={i > 0 ? "md:pl-6" : ""}>
              <div style={{ ...serif, fontSize: "34px", fontWeight: 500, color: "#c8502b", lineHeight: 1, letterSpacing: "-0.02em" }}>
                {s.num}
              </div>
              <div style={{ fontSize: "11px", lineHeight: 1.4, color: "#1f1f1f", marginTop: 8 }}>
                {s.label}
              </div>
              <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.12em", color: "#6b6b6b", marginTop: 6 }} className="uppercase">
                {s.src}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <div style={mono} className="text-[10px] uppercase tracking-widest mb-6 flex items-center">
          <span style={{ color: "#1a3a5c" }}>A century of labor, shaped by policy</span>
          <span style={{ flex: 1, height: 1, background: "#d9cfba", marginLeft: 12 }}></span>
          <span style={{ color: "#6b6b6b" }}>Click any node</span>
        </div>

        <div className="relative">
          <div style={{ position: "absolute", top: 11, left: "4%", right: "4%", height: 1, background: "linear-gradient(90deg, #1a3a5c 0%, #1a3a5c 80%, #c8502b 80%, #c8502b 100%)", opacity: 0.35 }}/>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4 relative">
            {TIMELINE.map((t, i) => (
              <button
                key={i}
                onClick={() => setExpandedTL(expandedTL === i ? null : i)}
                className="text-left group relative pt-8 pr-2"
              >
                <div style={{
                  position: "absolute",
                  top: t.hot ? 4 : 6,
                  left: 0,
                  width: t.hot ? 14 : 10,
                  height: t.hot ? 14 : 10,
                  background: t.hot ? "#c8502b" : "#1a3a5c",
                  borderRadius: "50%",
                  border: "2px solid #f5efe3",
                  boxShadow: t.hot ? "0 0 0 4px rgba(200,80,43,0.15)" : "none",
                  transition: "transform 0.2s",
                  transform: expandedTL === i ? "scale(1.3)" : "scale(1)",
                }}/>
                <div style={{ ...mono, fontSize: "10px", fontWeight: 500, color: "#c8502b", letterSpacing: "0.05em" }}>
                  {t.date}
                </div>
                <div style={{ ...serif, fontSize: "13px", fontWeight: 500, color: "#0f2540", marginTop: 4, lineHeight: 1.2 }}>
                  {t.title}
                </div>
              </button>
            ))}
          </div>
          {expandedTL !== null && (
            <div style={{
              marginTop: 32,
              padding: "20px 24px",
              background: "#0f2540",
              color: "#f5efe3",
              borderLeft: "3px solid #c8502b",
              transition: "all 0.3s",
            }}>
              <div style={{ ...mono, fontSize: "10px", color: "#c8502b", letterSpacing: "0.15em", marginBottom: 6 }} className="uppercase">
                {TIMELINE[expandedTL].date}
              </div>
              <div style={{ ...serif, fontSize: "20px", fontWeight: 500, marginBottom: 8 }}>
                {TIMELINE[expandedTL].title}
              </div>
              <div style={{ fontSize: "13px", lineHeight: 1.5, color: "#d9cfba" }}>
                {TIMELINE[expandedTL].desc}
              </div>
            </div>
          )}
        </div>
      </section>

      <section id="findings" style={{ background: "#eae4d5" }}>
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div style={{ ...mono, color: "#1a3a5c" }} className="text-[10px] uppercase tracking-widest mb-4">
            What we found
          </div>
          <h2 style={{ ...serif, fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 500, letterSpacing: "-0.015em", color: "#0f2540", lineHeight: 1.05 }}>
            Three angles on the same question.
          </h2>

          <div className="mt-10 flex flex-wrap gap-2 md:gap-4 border-b" style={{ borderColor: "#d9cfba" }}>
            {[
              { id: "ella", name: "Ella Russell", topic: "Yields" },
              { id: "david", name: "David Park", topic: "Discourse & markets" },
              { id: "sydney", name: "Sydney Beiting", topic: "Who feeds us" },
            ].map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                style={{
                  padding: "12px 16px",
                  borderBottom: activeTab === t.id ? "2px solid #c8502b" : "2px solid transparent",
                  marginBottom: -1,
                  transition: "all 0.2s",
                }}
                className="text-left group"
              >
                <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.2em", color: activeTab === t.id ? "#c8502b" : "#6b6b6b" }} className="uppercase">
                  {t.topic}
                </div>
                <div style={{ ...serif, fontSize: "15px", fontWeight: 500, color: activeTab === t.id ? "#0f2540" : "#6b6b6b", marginTop: 2 }}>
                  {t.name}
                </div>
              </button>
            ))}
          </div>

          <div className="mt-10">
            {activeTab === "ella" && <EllaPanel serif={serif} mono={mono}/>}
            {activeTab === "david" && <DavidPanel serif={serif} mono={mono}/>}
            {activeTab === "sydney" && <SydneyPanel serif={serif} mono={mono}/>}
          </div>
        </div>
      </section>

      <section id="chain" className="max-w-6xl mx-auto px-6 py-20">
        <div style={{ ...mono, color: "#1a3a5c" }} className="text-[10px] uppercase tracking-widest mb-4">
          The takeaway
        </div>
        <h2 style={{ ...serif, fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 500, letterSpacing: "-0.015em", color: "#0f2540", lineHeight: 1.05, marginBottom: 16 }}>
          Not a political story. <em style={{ color: "#c8502b" }}>A chain reaction.</em>
        </h2>
        <p style={{ ...serif, fontStyle: "italic", fontSize: "17px", lineHeight: 1.5, color: "#1f1f1f", maxWidth: "720px", marginBottom: 32 }}>
          Policy moves markets. Markets move framing. Framing moves opinion. Opinion moves the next policy. Click through to see how fast it cascades.
        </p>

        <div className="flex gap-3 mb-8">
          <button
            onClick={dominoPlaying ? () => setDominoPlaying(false) : playDomino}
            className="flex items-center gap-2 px-4 py-2 text-xs uppercase tracking-widest"
            style={{ ...mono, background: "#0f2540", color: "#f5efe3" }}
          >
            {dominoPlaying ? <Pause size={14}/> : <Play size={14}/>}
            {dominoPlaying ? "Pause" : dominoStep >= DOMINO_CHAIN.length - 1 ? "Replay" : "Play chain"}
          </button>
          <button
            onClick={resetDomino}
            className="flex items-center gap-2 px-4 py-2 text-xs uppercase tracking-widest"
            style={{ ...mono, background: "transparent", color: "#1f1f1f", border: "1px solid #d9cfba" }}
          >
            <RotateCcw size={14}/> Reset
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {DOMINO_CHAIN.map((d, i) => {
            const active = i <= dominoStep;
            return (
              <button
                key={i}
                onClick={() => { setDominoPlaying(false); setDominoStep(i); }}
                style={{
                  padding: "16px 14px",
                  background: active ? (i === DOMINO_CHAIN.length - 1 ? "#c8502b" : "#0f2540") : "#faf6ec",
                  color: active ? "#f5efe3" : "#1f1f1f",
                  border: active ? "1px solid transparent" : "1px solid #d9cfba",
                  textAlign: "left",
                  transition: "all 0.4s cubic-bezier(.2,.8,.2,1)",
                  transform: active ? "translateY(-4px)" : "translateY(0)",
                  boxShadow: active ? "0 8px 20px -8px rgba(15,37,64,0.3)" : "none",
                  position: "relative",
                }}
              >
                <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.2em", opacity: 0.6 }} className="uppercase">
                  Step {i + 1}
                </div>
                <div style={{ ...serif, fontSize: "18px", fontWeight: 600, marginTop: 6, marginBottom: 8 }}>
                  {d.label}
                </div>
                <div style={{ fontSize: "11px", lineHeight: 1.4, opacity: active ? 1 : 0.7 }}>
                  {d.desc}
                </div>
                {active && (
                  <div style={{ ...mono, fontSize: "9px", marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(245,239,227,0.2)", color: i === DOMINO_CHAIN.length - 1 ? "#fff" : "#c8502b", letterSpacing: "0.05em" }}>
                    {d.example}
                  </div>
                )}
                {i < DOMINO_CHAIN.length - 1 && (
                  <ArrowRight size={12} style={{ position: "absolute", right: -10, top: "50%", transform: "translateY(-50%)", color: active ? "#c8502b" : "#d9cfba", opacity: 0.6 }} className="hidden lg:block"/>
                )}
              </button>
            );
          })}
        </div>
      </section>

      <section id="stakeholders" style={{ background: "#0f2540", color: "#f5efe3" }}>
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div style={{ ...mono, color: "#c8502b" }} className="text-[10px] uppercase tracking-widest mb-4">
            Who this touches
          </div>
          <h2 style={{ ...serif, fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 500, letterSpacing: "-0.015em", color: "#f5efe3", lineHeight: 1.05, marginBottom: 12 }}>
            Four groups. <em style={{ color: "#c8502b" }}>Different stakes.</em>
          </h2>
          <p style={{ fontSize: "13px", color: "#d9cfba", marginBottom: 32 }}>
            Click any card to see what they actually worry about.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {STAKEHOLDERS.map((s, i) => {
              const flipped = flippedCard === i;
              return (
                <button
                  key={i}
                  onClick={() => setFlippedCard(flipped ? null : i)}
                  style={{
                    perspective: "1000px",
                    height: "260px",
                    position: "relative",
                    textAlign: "left",
                  }}
                >
                  <div style={{
                    position: "absolute",
                    inset: 0,
                    transformStyle: "preserve-3d",
                    transition: "transform 0.6s",
                    transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
                  }}>
                    <div style={{
                      position: "absolute",
                      inset: 0,
                      backfaceVisibility: "hidden",
                      background: "#1a3a5c",
                      padding: "24px 20px",
                      border: "1px solid rgba(245,239,227,0.1)",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}>
                      <div>
                        <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.2em", color: "#c8502b" }} className="uppercase">
                          Stakeholder
                        </div>
                        <div style={{ ...serif, fontSize: "22px", fontWeight: 600, color: "#f5efe3", marginTop: 8, lineHeight: 1.1 }}>
                          {s.name}
                        </div>
                        <div style={{ ...serif, fontStyle: "italic", fontSize: "14px", color: "#c8502b", marginTop: 14 }}>
                          {s.short}
                        </div>
                      </div>
                      <div style={{ ...mono, fontSize: "9px", color: "#d9cfba", opacity: 0.6 }} className="uppercase tracking-widest">
                        Click →
                      </div>
                    </div>
                    <div style={{
                      position: "absolute",
                      inset: 0,
                      backfaceVisibility: "hidden",
                      background: "#c8502b",
                      padding: "24px 20px",
                      transform: "rotateY(180deg)",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                      color: "#faf6ec",
                    }}>
                      <div>
                        <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.2em", opacity: 0.8 }} className="uppercase">
                          {s.name}
                        </div>
                        <div style={{ fontSize: "12px", lineHeight: 1.5, marginTop: 10 }}>
                          {s.desc}
                        </div>
                      </div>
                      <div style={{ ...serif, fontStyle: "italic", fontSize: "13px", lineHeight: 1.4, paddingTop: 12, borderTop: "1px solid rgba(250,246,236,0.3)" }}>
                        {s.concern}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <section id="recs" className="max-w-6xl mx-auto px-6 py-20">
        <div style={{ ...mono, color: "#1a3a5c" }} className="text-[10px] uppercase tracking-widest mb-4">
          What to do about it
        </div>
        <h2 style={{ ...serif, fontSize: "clamp(28px, 4vw, 44px)", fontWeight: 500, letterSpacing: "-0.015em", color: "#0f2540", lineHeight: 1.05, marginBottom: 32 }}>
          Four recommendations.
        </h2>

        <div className="space-y-3">
          {RECS.map((r, i) => (
            <button
              key={i}
              onClick={() => setExpandedRec(expandedRec === i ? null : i)}
              className="w-full text-left"
              style={{
                background: r.color,
                color: "#f5efe3",
                padding: "20px 24px",
                transition: "all 0.3s",
              }}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div style={{ ...mono, fontSize: "10px", letterSpacing: "0.2em", opacity: 0.7 }} className="uppercase">
                    For {r.who}
                  </div>
                  <div style={{ ...serif, fontSize: "20px", fontWeight: 500, marginTop: 6 }}>
                    {r.short}
                  </div>
                  {expandedRec === i && (
                    <div style={{ fontSize: "13px", lineHeight: 1.5, marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(245,239,227,0.25)", opacity: 0.92 }}>
                      {r.long}
                    </div>
                  )}
                </div>
                <ChevronDown size={18} style={{ transform: expandedRec === i ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.3s", flexShrink: 0, marginTop: 2, opacity: 0.6 }}/>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section style={{ borderTop: "1px solid #d9cfba", borderBottom: "1px solid #d9cfba", background: "#faf6ec" }}>
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <div style={{ ...mono, fontSize: "10px", letterSpacing: "0.25em", color: "#c8502b", marginBottom: 20 }} className="uppercase">
            In one sentence
          </div>
          <p style={{ ...serif, fontStyle: "italic", fontSize: "clamp(22px, 3.2vw, 34px)", lineHeight: 1.3, color: "#0f2540", letterSpacing: "-0.005em" }}>
            The people at the end of the chain — <span style={{ fontStyle: "normal", color: "#c8502b" }}>workers, farmers, families at the grocery store</span> — are the ones who pay for all of it.
          </p>
        </div>
      </section>

      <section id="sources" style={{ background: "#1f1f1f", color: "#d9cfba" }}>
        <div className="max-w-6xl mx-auto px-6 py-12">
          <button
            onClick={() => setSourcesOpen(!sourcesOpen)}
            className="flex items-center justify-between w-full"
            style={{ ...mono, fontSize: "10px", letterSpacing: "0.25em", color: "#c8502b" }}
          >
            <span className="uppercase">Sources ({SOURCES.length})</span>
            <ChevronDown size={14} style={{ transform: sourcesOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.3s" }}/>
          </button>
          {sourcesOpen && (
            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-3" style={{ ...mono, fontSize: "11px", lineHeight: 1.5 }}>
              {SOURCES.map((s, i) => (
                <div key={i} className="flex gap-2">
                  <span style={{ color: "#c8502b", flexShrink: 0 }}>{String(i + 1).padStart(2, "0")}</span>
                  <span>
                    {s.cite}
                    {s.url && (
                      <a href={s.url} target="_blank" rel="noopener noreferrer" style={{ color: "#c8502b", marginLeft: 6, display: "inline-flex", alignItems: "center", gap: 3 }}>
                        link <ExternalLink size={10}/>
                      </a>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div style={{ ...mono, fontSize: "9px", letterSpacing: "0.2em", color: "#6b6b6b", marginTop: 32, paddingTop: 16, borderTop: "1px solid #333" }} className="uppercase flex flex-wrap justify-between gap-3">
            <span>AGRCOMM 2330 · Issue Case Study · April 2026</span>
            <span>The Ohio State University</span>
          </div>
        </div>
      </section>

    </div>
  );
}

// ============================================================
// PANELS
// ============================================================

function EllaPanel({ serif, mono }) {
  return (
    <div className="grid md:grid-cols-5 gap-10 items-start">
      <div className="md:col-span-2">
        <div style={{ ...mono, color: "#c8502b" }} className="text-[10px] uppercase tracking-widest mb-3">
          Hero stat
        </div>
        <div style={{ ...serif, fontSize: "56px", fontWeight: 500, color: "#c8502b", lineHeight: 1, letterSpacing: "-0.02em" }}>
          $3–7B
        </div>
        <div style={{ fontSize: "13px", color: "#1f1f1f", marginTop: 8, marginBottom: 32 }}>
          crop losses after the 2025 California ICE raids
        </div>

        <h3 style={{ ...serif, fontSize: "28px", fontWeight: 500, color: "#0f2540", lineHeight: 1.1, letterSpacing: "-0.01em" }}>
          When deportations rise, yields fall.
        </h3>
        <p style={{ fontSize: "14px", lineHeight: 1.65, color: "#1f1f1f", marginTop: 16 }}>
          You can't pick produce without pickers. With 40–50% of US farmworkers undocumented, the 2025 California ICE raids cut farm labor by up to 40% overnight. The result was billions in crop losses and a 5–12% price jump at the grocery store. Farmers and consumers both pay the cost.
        </p>
        <div style={{ ...mono, fontSize: "10px", color: "#6b6b6b", marginTop: 20 }}>
          Sources: USDA ERS · FreshFruitPortal · NBC News
        </div>
      </div>

      <div className="md:col-span-3">
        <div style={{ background: "#faf6ec", border: "1px solid #d9cfba", padding: "20px 16px 8px 0", height: 340 }}>
          <div style={{ ...mono, color: "#6b6b6b" }} className="text-[9px] uppercase tracking-wider pl-4 mb-1.5">
            Fig. 1 · Crop yield index vs deportations, 2016–2025
          </div>
          <ResponsiveContainer width="100%" height="92%">
            <LineChart data={YIELD_DATA} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="2 2" stroke="#d9cfba"/>
              <XAxis dataKey="year" stroke="#6b6b6b" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}/>
              <YAxis yAxisId="left" stroke="#1a3a5c" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} label={{ value: "Yield idx", angle: -90, position: "insideLeft", fontSize: 9, fill: "#1a3a5c" }}/>
              <YAxis yAxisId="right" orientation="right" stroke="#c8502b" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} label={{ value: "Deport. (k)", angle: 90, position: "insideRight", fontSize: 9, fill: "#c8502b" }}/>
              <Tooltip content={<ChartTooltip/>}/>
              <Line yAxisId="left" type="monotone" dataKey="yieldIdx" stroke="#1a3a5c" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Yield index"/>
              <Line yAxisId="right" type="monotone" dataKey="deportations" stroke="#c8502b" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Deportations"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={{ ...mono, fontSize: "9px", color: "#6b6b6b", marginTop: 10, fontStyle: "italic" }}>
          Representative series built from USDA ERS yield indices and DHS/ICE removals. Hover any point for values.
        </div>
      </div>
    </div>
  );
}

function DavidPanel({ serif, mono }) {
  return (
    <div className="grid md:grid-cols-5 gap-10 items-start">
      <div className="md:col-span-2">
        <div style={{ ...mono, color: "#c8502b" }} className="text-[10px] uppercase tracking-widest mb-3">
          Hero stat
        </div>
        <div style={{ ...serif, fontSize: "56px", fontWeight: 500, color: "#c8502b", lineHeight: 1, letterSpacing: "-0.02em" }}>
          −35%
        </div>
        <div style={{ fontSize: "13px", color: "#1f1f1f", marginTop: 8, marginBottom: 32 }}>
          FCOJ futures in the 30 days after mass deportation ops began
        </div>

        <h3 style={{ ...serif, fontSize: "28px", fontWeight: 500, color: "#0f2540", lineHeight: 1.1, letterSpacing: "-0.01em" }}>
          The market priced it in before the news ran it.
        </h3>
        <p style={{ fontSize: "14px", lineHeight: 1.65, color: "#1f1f1f", marginTop: 16 }}>
          Enforcement framing on Reddit and Facebook jumped from about 17% under Obama to 27% under Trump. A 10-point swing, too clean to be noise. News moved slower. But FCOJ futures dropped 35% in the 30 days after January's deportation ops began. Wall Street priced in the labor shortage the same week social media framing shifted.
        </p>
        <div style={{ ...mono, fontSize: "10px", color: "#6b6b6b", marginTop: 20 }}>
          Source: <a href="https://github.com/parkjpd/agrcomm-discourse" target="_blank" rel="noopener noreferrer" style={{ color: "#c8502b" }}>github.com/parkjpd/agrcomm-discourse</a>
        </div>
      </div>

      <div className="md:col-span-3">
        <div style={{ background: "#faf6ec", border: "1px solid #d9cfba", padding: "20px 16px 8px 0", height: 340 }}>
          <div style={{ ...mono, color: "#6b6b6b" }} className="text-[9px] uppercase tracking-wider pl-4 mb-1.5">
            Fig. 2 · FCOJ futures vs enforcement framing, Dec 2024 – Feb 2025
          </div>
          <ResponsiveContainer width="100%" height="92%">
            <LineChart data={FCOJ_DATA} margin={{ top: 10, right: 30, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="2 2" stroke="#d9cfba"/>
              <XAxis dataKey="date" stroke="#6b6b6b" tick={{ fontSize: 9, fontFamily: "JetBrains Mono" }} interval={1}/>
              <YAxis yAxisId="left" stroke="#1a3a5c" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} domain={["auto", "auto"]} label={{ value: "FCOJ ¢/lb", angle: -90, position: "insideLeft", fontSize: 9, fill: "#1a3a5c" }}/>
              <YAxis yAxisId="right" orientation="right" stroke="#c8502b" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} domain={[0, "auto"]} label={{ value: "Framing %", angle: 90, position: "insideRight", fontSize: 9, fill: "#c8502b" }}/>
              <Tooltip content={<ChartTooltip/>}/>
              <ReferenceLine yAxisId="left" x="Jan 19" stroke="#c8502b" strokeDasharray="3 3" label={{ value: "raids", fontSize: 9, fill: "#c8502b", position: "top" }}/>
              <Line yAxisId="left" type="monotone" dataKey="fcoj" stroke="#1a3a5c" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} name="FCOJ close"/>
              <Line yAxisId="right" type="monotone" dataKey="framing" stroke="#c8502b" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} name="Pro-enforcement framing"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={{ ...mono, fontSize: "9px", color: "#6b6b6b", marginTop: 10, fontStyle: "italic" }}>
          FCOJ: Yahoo Finance OJ=F weekly closes. Framing: project scrape, quarterly news series interpolated to weekly.
        </div>
      </div>
    </div>
  );
}

function SydneyPanel({ serif, mono }) {
  return (
    <div className="grid md:grid-cols-5 gap-10 items-start">
      <div className="md:col-span-2">
        <div style={{ ...mono, color: "#c8502b" }} className="text-[10px] uppercase tracking-widest mb-3">
          Hero stat
        </div>
        <div style={{ ...serif, fontSize: "56px", fontWeight: 500, color: "#c8502b", lineHeight: 1, letterSpacing: "-0.02em" }}>
          61%
        </div>
        <div style={{ fontSize: "13px", color: "#1f1f1f", marginTop: 8, marginBottom: 32 }}>
          of the US farm workforce is immigrant (documented or undocumented)
        </div>

        <h3 style={{ ...serif, fontSize: "28px", fontWeight: 500, color: "#0f2540", lineHeight: 1.1, letterSpacing: "-0.01em" }}>
          Immigrants aren't a supplement. They are the workforce.
        </h3>
        <p style={{ fontSize: "14px", lineHeight: 1.65, color: "#1f1f1f", marginTop: 16 }}>
          USDA data from 2022 shows 42% of US farmworkers are undocumented and another 19% are documented immigrants. 78% self-identify as Hispanic; 63% are from Mexico. The quality-of-life side is rough: 20% of farmworker families are below the federal poverty line, and a North Carolina study found 78% live in crowded housing regardless of whether the space meets code.
        </p>
        <div style={{ ...mono, fontSize: "10px", color: "#6b6b6b", marginTop: 20 }}>
          Sources: USDA ERS · NCFH · NAWS 2019–2020
        </div>
      </div>

      <div className="md:col-span-3">
        <div style={{ background: "#faf6ec", border: "1px solid #d9cfba", padding: "20px 0", height: 340 }}>
          <div style={{ ...mono, color: "#6b6b6b" }} className="text-[9px] uppercase tracking-wider pl-5 mb-1.5">
            Fig. 3 · US farm workforce composition, 2022
          </div>
          <ResponsiveContainer width="100%" height="88%">
            <PieChart>
              <Pie
                data={WORKFORCE}
                dataKey="value"
                cx="40%"
                cy="50%"
                innerRadius={60}
                outerRadius={110}
                paddingAngle={2}
                strokeWidth={3}
                stroke="#faf6ec"
              >
                {WORKFORCE.map((entry, i) => (
                  <Cell key={i} fill={entry.color}/>
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip/>}/>
              <Legend
                layout="vertical"
                verticalAlign="middle"
                align="right"
                iconType="square"
                wrapperStyle={{ fontFamily: "DM Sans", fontSize: "12px", paddingRight: 20 }}
                formatter={(v, e) => <span style={{ color: "#1f1f1f" }}>{v}: {e.payload.value}%</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div style={{ ...mono, fontSize: "9px", color: "#6b6b6b", marginTop: 10, fontStyle: "italic" }}>
          USDA Economic Research Service, 2022. Hover any segment for the exact value.
        </div>
      </div>
    </div>
  );
}
