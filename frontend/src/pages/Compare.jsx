import React, { useMemo } from "react";
import {
  ArrowRight, BarChart3, Check, ChevronRight, CircleHelp, Database,
  ExternalLink, Flame, Layers3, Plus, Scale, ShieldCheck, X
} from "lucide-react";
import { PageTitle, Status } from "../components/Shared";

const fields = [
  { key: "program", label: "Research program", group: "CATALOGUE PROFILE" },
  { key: "type", label: "Research category", group: "CATALOGUE PROFILE" },
  { key: "year", label: "Year", group: "CATALOGUE PROFILE" },
  { key: "status", label: "FLAME AI availability", group: "CATALOGUE PROFILE" },
  { key: "objective", label: "Scientific objective", group: "RESEARCH SCOPE" },
  { key: "summary", label: "Catalogue summary", group: "RESEARCH SCOPE" },
  { key: "tags", label: "Research keywords", group: "RESEARCH SCOPE", format: value => value?.length ? value.join(" · ") : null },
  { key: "source", label: "Original source", group: "SOURCE & TRACEABILITY" },
  { key: "doi", label: "DOI", group: "SOURCE & TRACEABILITY" },
];

const displayValue = (record, field) => {
  const value = field.format ? field.format(record[field.key]) : record[field.key];
  if (value === undefined || value === null || value === "" || value === "Not listed" || value === "Not listed in this prototype") return "Not available in current catalogue";
  return String(value);
};

export default function Compare({ records, compare, toggleCompare, onNavigate, onOpenRecord }) {
  const chosen = useMemo(() => compare.map(id => records.find(record => record.id === id)).filter(Boolean), [compare, records]);
  const groups = useMemo(() => fields.reduce((all, field) => {
    (all[field.group] ||= []).push(field);
    return all;
  }, {}), []);
  const differingCount = fields.filter(field => new Set(chosen.map(record => displayValue(record, field))).size > 1).length;
  const commonTags = chosen.length > 1
    ? chosen.map(record => record.tags || []).reduce((common, tags) => common.filter(tag => tags.includes(tag)))
    : [];

  return (
    <main className="inner-page compare-page">
      <PageTitle
        eyebrow="02 / RESEARCH ANALYSIS"
        title={<>COMPARISON <em>LAB</em></>}
        desc="Examine NASA investigation records side by side. Compare research scope, catalogue metadata and source availability before exploring the original evidence."
      />

      <section className="compare-intro-strip">
        <div className="compare-intro-icon"><Scale size={19}/></div>
        <div><span className="overline">EVIDENCE-FIRST ANALYSIS</span><p>Metadata comparisons are available now. Quantitative experiment comparisons will appear only when verified measurements and units are connected.</p></div>
        <div className="compare-capacity"><strong>{chosen.length}<span> / 3</span></strong><small>INVESTIGATIONS</small></div>
      </section>

      <div className="compare-section-heading">
        <div><span className="overline">YOUR COMPARISON SET</span><h2>SELECTED INVESTIGATIONS</h2><p>Select two or three records to reveal their differences.</p></div>
        <div className="compare-heading-actions">
          {chosen.length > 0 && <button className="text-link compare-clear" onClick={() => chosen.forEach(record => toggleCompare(record.id))}>CLEAR SELECTION <X size={13}/></button>}
          <button className="outline-button" onClick={() => onNavigate("explorer")}><Plus size={14}/> ADD INVESTIGATIONS</button>
        </div>
      </div>

      {chosen.length === 0 ? (
        <div className="compare-empty-state">
          <div className="compare-empty-art"><Layers3 size={36}/><span/><span/><span/></div>
          <span className="overline">COMPARISON WORKSPACE / EMPTY</span>
          <h2>Start with the research.</h2>
          <p>Open the Investigation Explorer and add the records you want to examine. You can compare up to three investigations at a time.</p>
          <button className="blue-button" onClick={() => onNavigate("explorer")}>BROWSE INVESTIGATIONS <ArrowRight size={14}/></button>
        </div>
      ) : (
        <>
          <div className={`compare-selected-grid count-${chosen.length}`}>
            {chosen.map((record, index) => (
              <article className="compare-selected-card" key={record.id}>
                <div className="compare-card-top"><span className="compare-index">0{index + 1} / SELECTED</span><button className="compare-remove" onClick={() => toggleCompare(record.id)} aria-label={`Remove ${record.id}`} title="Remove from comparison"><X size={14}/></button></div>
                <div className="compare-card-title-row"><span className="compare-flame-icon"><Flame size={17}/></span><div><span className="compare-record-id">{record.id} / {record.program}</span><h3>{record.title}</h3></div></div>
                <div className="compare-card-meta"><span>{record.year}</span><Status value={record.status}/></div>
                <button className="compare-view-record" onClick={() => onOpenRecord(record)}>VIEW INVESTIGATION <ChevronRight size={13}/></button>
              </article>
            ))}
            {chosen.length < 3 && <button className="compare-add-card" onClick={() => onNavigate("explorer")}><span><Plus size={20}/></span><strong>ADD ANOTHER INVESTIGATION</strong><small>{chosen.length === 1 ? "Add one more record to begin comparing" : "You can compare up to three records"}</small></button>}
          </div>

          {chosen.length < 2 ? (
            <div className="compare-next-step"><CircleHelp size={17}/><div><strong>ONE MORE RECORD NEEDED</strong><p>Add at least one more investigation to generate the side-by-side comparison.</p></div><button className="text-link" onClick={() => onNavigate("explorer")}>OPEN EXPLORER <ArrowRight size={13}/></button></div>
          ) : (
            <>
              <div className="compare-insight-row">
                <div className="compare-insight-card"><span className="overline">FIELDS COMPARED</span><strong>{fields.length}</strong><small>Catalogue attributes</small></div>
                <div className="compare-insight-card"><span className="overline">DIFFERING FIELDS</span><strong>{differingCount}</strong><small>Values differ or availability differs</small></div>
                <div className="compare-insight-card"><span className="overline">SHARED KEYWORDS</span><strong>{commonTags.length}</strong><small>{commonTags.length ? commonTags.join(", ") : "No shared tags recorded"}</small></div>
              </div>

              <div className="compare-table-heading"><div><span className="overline">SIDE-BY-SIDE REVIEW</span><h2>INVESTIGATION MATRIX</h2></div><span className="compare-diff-key"><i/> DIFFERING VALUES</span></div>
              <div className="compare-matrix-wrap">
                <table className="compare-matrix">
                  <thead><tr><th className="matrix-attribute">ATTRIBUTE</th>{chosen.map(record => <th key={record.id}><span>{record.id}</span><small>{record.program}</small></th>)}</tr></thead>
                  <tbody>
                    {Object.entries(groups).map(([group, groupFields]) => <React.Fragment key={group}>
                      <tr className="matrix-group-row"><td colSpan={chosen.length + 1}>{group}</td></tr>
                      {groupFields.map(field => {
                        const values = chosen.map(record => displayValue(record, field));
                        const differs = new Set(values).size > 1;
                        return <tr key={field.key} className={differs ? "is-different" : "is-same"}>
                          <td className="matrix-label">{field.label}{differs && <span className="difference-dot" title="Values differ"/>}</td>
                          {chosen.map((record, index) => <td key={record.id} className={differs ? "matrix-different-cell" : ""}>{field.key === "status" ? <Status value={record.status}/> : <span>{values[index]}</span>}</td>)}
                        </tr>;
                      })}
                    </React.Fragment>)}
                  </tbody>
                </table>
              </div>
              <div className="compare-integrity-note"><ShieldCheck size={17}/><div><strong>SCIENTIFIC INTEGRITY NOTE</strong><p>This view compares catalogue descriptions and metadata only. It does not establish that experiments used equivalent conditions or produced directly comparable outcomes. Missing values are shown explicitly and are never treated as zero.</p></div></div>
              <div className="compare-bottom-actions"><button className="outline-button" onClick={() => onNavigate("explorer")}>CHANGE SELECTION</button><button className="blue-button" onClick={() => onOpenRecord(chosen[0])}>OPEN FIRST INVESTIGATION <ArrowRight size={14}/></button></div>
            </>
          )}
        </>
      )}

      <section className="compare-data-readiness">
        <div className="readiness-icon"><Database size={17}/></div><div><span className="overline">NEXT DATA LAYER</span><h3>EXPERIMENTAL MEASUREMENTS</h3><p>Charts for flame spread, temperature, oxygen concentration, pressure and other measured variables can be enabled when the verified datasets are available with units, conditions and source references.</p></div><span className="readiness-status">AWAITING VERIFIED DATA</span>
      </section>
    </main>
  );
}
