
import React, { useMemo } from "react";
import {
  Flame,
  Waves,
  ShieldCheck,
  ArrowRight,
  BarChart3,
  Activity,
  Database
} from "lucide-react";
import { PageTitle } from "../components/Shared";

const colors = ["#55c5e5", "#438be0", "#8b78e8", "#e6a85c", "#58bd94", "#d878a0"];

const panel = {
  background: "#111923",
  border: "1px solid #293542",
  borderRadius: 14,
  padding: 20,
  minWidth: 0
};

const muted = { color: "#94a3b5", fontSize: 12 };

function countBy(records, field) {
  return records.reduce((result, record) => {
    const key = String(record[field] ?? "Unknown");
    result[key] = (result[key] || 0) + 1;
    return result;
  }, {});
}

function HorizontalChart({ title, data, onSelect }) {
  const max = Math.max(1, ...data.map(item => item.value));

  return (
    <section style={panel}>
      <h3 style={{ fontSize: 13, letterSpacing: 1, margin: "0 0 22px" }}>
        {title}
      </h3>

      <div style={{ display: "grid", gap: 16 }}>
        {data.map((item, index) => (
          <button
            key={item.label}
            onClick={() => onSelect?.(item.label)}
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(75px, 1fr) minmax(80px, 2fr) 25px",
              gap: 10,
              alignItems: "center",
              border: 0,
              background: "transparent",
              color: "#e6edf5",
              cursor: onSelect ? "pointer" : "default",
              padding: 0,
              textAlign: "left"
            }}
          >
            <span style={{ fontSize: 12 }}>{item.label}</span>

            <span style={{
              height: 10,
              background: "#27313c",
              borderRadius: 20,
              overflow: "hidden"
            }}>
              <span style={{
                display: "block",
                height: "100%",
                width: `${item.value / max * 100}%`,
                background: colors[index % colors.length],
                borderRadius: 20
              }} />
            </span>

            <strong style={{ fontSize: 12, textAlign: "right" }}>
              {item.value}
            </strong>
          </button>
        ))}
      </div>
    </section>
  );
}

function YearChart({ data, onSelect }) {
  const max = Math.max(1, ...data.map(item => item.value));

  return (
    <section style={panel}>
      <h3 style={{ fontSize: 13, letterSpacing: 1, margin: "0 0 20px" }}>
        INVESTIGATIONS OVER TIME
      </h3>

      <div style={{
        height: 210,
        display: "flex",
        alignItems: "end",
        gap: 10,
        padding: "10px 2px 0",
        borderBottom: "1px solid #35414e"
      }}>
        {data.map((item, index) => (
          <button
            key={item.label}
            onClick={() => onSelect?.(item.label)}
            title={`${item.value} records in ${item.label}`}
            style={{
              flex: 1,
              height: "100%",
              display: "flex",
              flexDirection: "column",
              justifyContent: "end",
              alignItems: "center",
              gap: 7,
              border: 0,
              padding: 0,
              background: "transparent",
              color: "#dce5ef",
              cursor: "pointer",
              minWidth: 0
            }}
          >
            <strong style={{ fontSize: 11 }}>{item.value}</strong>

            <span style={{
              width: "75%",
              maxWidth: 42,
              height: `${Math.max(5, item.value / max * 145)}px`,
              background: `linear-gradient(180deg, #61c8e4, #3979d3)`,
              borderRadius: "5px 5px 0 0"
            }} />

            <span style={{ fontSize: 10, color: "#9baabc" }}>
              {item.label}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

function StatusDonut({ data }) {
  const total = data.reduce((sum, item) => sum + item.value, 0) || 1;
  const radius = 65;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  return (
    <section style={panel}>
      <h3 style={{ fontSize: 13, letterSpacing: 1, margin: "0 0 16px" }}>
        INDEXING STATUS DISTRIBUTION
      </h3>

      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-around",
        gap: 20,
        flexWrap: "wrap"
      }}>
        <svg viewBox="0 0 180 180" width="175" role="img"
          aria-label="Donut chart showing catalogue indexing status">
          <circle
            cx="90" cy="90" r={radius}
            fill="none" stroke="#283441" strokeWidth="19"
          />

          {data.map((item, index) => {
            const length = item.value / total * circumference;
            const currentOffset = offset;
            offset += length;

            return (
              <circle
                key={item.label}
                cx="90"
                cy="90"
                r={radius}
                fill="none"
                stroke={colors[index % colors.length]}
                strokeWidth="19"
                strokeDasharray={`${length} ${circumference - length}`}
                strokeDashoffset={-currentOffset}
                transform="rotate(-90 90 90)"
              />
            );
          })}

          <text x="90" y="85" textAnchor="middle"
            fill="#f1f5f9" fontSize="25" fontWeight="700">
            {total}
          </text>
          <text x="90" y="105" textAnchor="middle"
            fill="#94a3b5" fontSize="10">
            RECORDS
          </text>
        </svg>

        <div style={{ display: "grid", gap: 15 }}>
          {data.map((item, index) => (
            <div key={item.label}
              style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <span style={{
                width: 10,
                height: 10,
                borderRadius: 3,
                background: colors[index % colors.length]
              }} />
              <span style={{ fontSize: 12, color: "#cbd5e1" }}>
                {item.label}
              </span>
              <strong style={{ fontSize: 12, marginLeft: "auto" }}>
                {item.value}
              </strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Insights({
  records = [],
  onNavigate,
  setQuery,
  setProgram
}) {
  const byProgram = useMemo(
    () => Object.entries(countBy(records, "program"))
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value),
    [records]
  );

  const byType = useMemo(
    () => Object.entries(countBy(records, "type"))
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value),
    [records]
  );

  const byYear = useMemo(
    () => Object.entries(countBy(records, "year"))
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => Number(a.label) - Number(b.label)),
    [records]
  );

  const byStatus = useMemo(
    () => Object.entries(countBy(records, "status"))
      .map(([label, value]) => ({ label, value })),
    [records]
  );

  const indexed = records.filter(r => r.status === "Indexed").length;
  const metadata = records.filter(r => r.status === "Metadata only").length;
  const processing = records.filter(r => r.status === "Processing").length;

  const openProgram = value => {
    setProgram(value);
    onNavigate("explorer");
  };

  const cards = [
    {
      I: Flame,
      title: "Flame behavior",
      text: "Explore how flame shape, spread, and stability vary across microgravity investigations.",
      refs: "SAFFIRE · FLEX · ACME",
      q: "flame"
    },
    {
      I: Waves,
      title: "Smoke & aerosols",
      text: "Review research records focused on smoke formation, particle behavior, and measurement.",
      refs: "PSI-101 · PSI-102 · PSI-107",
      q: "smoke"
    },
    {
      I: ShieldCheck,
      title: "Suppression & materials",
      text: "Investigate records related to material flammability, burning, and suppression.",
      refs: "BASS · SAFFIRE",
      q: "material"
    }
  ];

  return (
    <main className="inner-page">

      <PageTitle
        eyebrow="04 / FLAME AI DATA INTELLIGENCE"
        title={<>EXPLORE <em>ANALYTICS</em></>}
        desc="Explore the distribution, history, categories and indexing status of the NASA combustion research records in the FLAME AI catalogue."
      />

      {/* SUMMARY */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(145px,1fr))",
        gap: 12,
        marginBottom: 25
      }}>
        {[
          ["TOTAL RECORDS", records.length, Database],
          ["RESEARCH PROGRAMS", byProgram.length, Flame],
          ["INDEXED RECORDS", indexed, Activity],
          ["RESEARCH CATEGORIES", byType.length, BarChart3]
        ].map(([label, value, Icon]) => (
          <div key={label} style={panel}>
            <Icon size={18} color="#57c5e4" />
            <div style={{ fontSize: 27, fontWeight: 750, marginTop: 10 }}>
              {value}
            </div>
            <div style={muted}>{label}</div>
          </div>
        ))}
      </div>

      {/* CHARTS */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,390px),1fr))",
        gap: 15
      }}>
        <HorizontalChart
          title="RECORDS BY RESEARCH PROGRAM"
          data={byProgram}
          onSelect={openProgram}
        />

        <StatusDonut data={byStatus} />

        <YearChart
          data={byYear}
          onSelect={year => {
            setQuery(year);
            onNavigate("explorer");
          }}
        />

        <HorizontalChart
          title="RESEARCH CATEGORIES"
          data={byType}
          onSelect={type => {
            setQuery(type);
            onNavigate("explorer");
          }}
        />
      </div>

      {/* STATUS BREAKDOWN */}
      <section style={{ ...panel, marginTop: 15 }}>
        <h3 style={{ fontSize: 13, letterSpacing: 1 }}>
          CATALOGUE INDEXING OVERVIEW
        </h3>

        <div style={{
          height: 16,
          display: "flex",
          borderRadius: 20,
          overflow: "hidden",
          background: "#27313c",
          margin: "18px 0"
        }}>
          {[
            [indexed, "#55c5e5"],
            [metadata, "#438be0"],
            [processing, "#e6a85c"]
          ].map(([value, color], index) => (
            <div key={index}
              style={{ width: `${value / (records.length || 1) * 100}%`, background: color }}
            />
          ))}
        </div>

        <div style={{
          display: "flex",
          gap: 22,
          flexWrap: "wrap",
          ...muted
        }}>
          <span>Indexed: <b>{indexed}</b></span>
          <span>Metadata only: <b>{metadata}</b></span>
          <span>Processing: <b>{processing}</b></span>
        </div>
      </section>

      {/* FIRE SAFETY INSIGHTS */}
      <div style={{ marginTop: 55 }}>
        <PageTitle
          eyebrow="05 / APPLICATION & SAFETY"
          title={<>FIRE SAFETY <em>INSIGHTS</em></>}
          desc="Research themes that connect microgravity combustion investigations to spacecraft fire-safety questions."
        />

        <section className="safety-hero">
          <div>
            <span className="overline">WHY THIS RESEARCH MATTERS</span>
            <h2>SPACECRAFT FIRE<br /><em>SAFETY IS DIFFERENT.</em></h2>
            <p>
              In microgravity, buoyancy-driven convection is greatly reduced.
              This changes how flames and combustion products behave compared
              with many Earth-based conditions. Specific safety conclusions
              must be grounded in individual experiments.
            </p>
          </div>
        </section>

        <div className="insight-grid">
          {cards.map(({ I, title, text, refs, q }) => (
            <article className="insight-card" key={title}>
              <I />
              <h3>{title}</h3>
              <p>{text}</p>
              <small>{refs}</small>

              <button
                className="text-link"
                onClick={() => {
                  setQuery(q);
                  setProgram("All");
                  onNavigate("explorer");
                }}
              >
                VIEW RELATED RECORDS <ArrowRight size={13} />
              </button>
            </article>
          ))}
        </div>

        <div className="notice">
          <ShieldCheck />
          <p>
            <b>Evidence standard:</b> This prototype does not calculate fire
            risk or issue operational safety recommendations. Future insights
            must distinguish measured observations, researcher conclusions,
            and AI interpretation, with traceable sources.
          </p>
        </div>
      </div>

      {/* DATA LIMITATION */}
      <section style={{ ...panel, marginTop: 25 }}>
        <h3 style={{ fontSize: 13 }}>DATA SCOPE & INTERPRETATION</h3>
        <p style={{ ...muted, lineHeight: 1.7 }}>
          Charts are calculated from the {records.length} catalogue records
          currently loaded in FLAME AI. They show metadata distributions,
          not measured flame temperature, pressure, oxygen concentration,
          or combustion time-series measurements.
        </p>
      </section>

    </main>
  );
}
