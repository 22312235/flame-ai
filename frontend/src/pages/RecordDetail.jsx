
import React from "react";
import {
  ArrowLeft,
  ExternalLink,
  FileText,
  Flame,
  Database,
  Target,
  Tags,
  CalendarDays,
  ArrowUpRight,
  BookOpen,
  FlaskConical,
  ChartNoAxesCombined,
  Info,
  ShieldCheck
} from "lucide-react";

import { Status } from "../components/Shared";

const available = value =>
  value !== undefined &&
  value !== null &&
  String(value).trim() !== "" &&
  value !== "Not listed" &&
  value !== "Not listed in this prototype";

const fallback = value =>
  available(value) ? String(value) : "Not available in current catalogue";

export default function RecordDetail({
  record,
  onBack,
  onCompare,
  selected
}) {
  if (!record) {
    return (
      <main className="inner-page detail-page">
        <button className="back-link" onClick={onBack}>
          <ArrowLeft size={14} />
          BACK TO INVESTIGATION EXPLORER
        </button>

        <div className="empty large">
          <h2>Investigation not selected</h2>
          <p>
            Open an investigation from the catalogue to view its details.
          </p>

          <button className="blue-button" onClick={onBack}>
            RETURN TO EXPLORER
          </button>
        </div>
      </main>
    );
  }

  const nasaUrl =
    `https://psi.nasa.gov/physci/repo/search?q=${encodeURIComponent(record.id)}&data_source=psi&data_type=investigation`;

  const tags = Array.isArray(record.tags) ? record.tags : [];

  const approachAvailable = available(record.approach);
  const findingsAvailable = available(record.findings);

  const statusTitle =
    record.status === "Indexed"
      ? "Marked as indexed in FLAME AI"
      : record.status === "Processing"
        ? "Record processing"
        : "Catalogue metadata available";

  const statusDescription =
    record.status === "Indexed"
      ? "The prototype marks this record as indexed. Specific files and measurements still need to be verified against the original source."
      : record.status === "Processing"
        ? "This record is marked as processing in the prototype. Indexed documents and measurements are not yet confirmed."
        : "The current prototype contains catalogue metadata only. Experimental files and structured measurements have not been confirmed here.";

  return (
    <main className="inner-page detail-page">

      {/* BACK NAVIGATION */}
      <button className="back-link" onClick={onBack}>
        <ArrowLeft size={14} />
        BACK TO INVESTIGATION EXPLORER
      </button>

      {/* INVESTIGATION HEADER */}
      <section className="detail-hero">

        <div className="detail-hero-copy">

          <div className="overline">
            NASA PSI INVESTIGATION / {record.id}
          </div>

          <div className="detail-program">
            {fallback(record.program)}
            <span>·</span>
            {fallback(record.type)}
          </div>

          <h1>{fallback(record.title)}</h1>

          <p>{fallback(record.summary)}</p>

          <div className="detail-hero-actions">

            <a
              className="blue-button"
              href={nasaUrl}
              target="_blank"
              rel="noreferrer"
            >
              OPEN NASA PSI SOURCE
              <ExternalLink size={14} />
            </a>

            <button
              className={"outline-button " + (selected ? "selected" : "")}
              onClick={() => onCompare(record.id)}
              aria-pressed={Boolean(selected)}
            >
              {selected
                ? "ADDED TO COMPARISON ✓"
                : "ADD TO COMPARISON +"
              }
            </button>

          </div>
        </div>

        <div className="detail-hero-mark">
          <Flame size={54} />
          <span>{record.id}</span>
          <small>PHYSICAL SCIENCES INFORMATICS</small>
        </div>

      </section>

      {/* METADATA STRIP */}
      <section className="detail-status-strip">

        <div>
          <small>FLAME AI INDEXING</small>
          <Status value={record.status} />
        </div>

        <div>
          <small>PROGRAM</small>
          <strong>{fallback(record.program)}</strong>
        </div>

        <div>
          <small>YEAR</small>
          <strong>{fallback(record.year)}</strong>
        </div>

        <div>
          <small>RESEARCH TYPE</small>
          <strong>{fallback(record.type)}</strong>
        </div>

      </section>

      {/* MAIN CONTENT */}
      <div className="detail-content-grid">

        <section className="detail-content-main">

          <article className="detail-section">
            <div className="detail-section-title">
              <Target size={16} />
              <span>RESEARCH OVERVIEW</span>
            </div>

            <h2>Investigation summary</h2>

            <p>{fallback(record.summary)}</p>
          </article>

          <article className="detail-section">
            <div className="detail-section-title">
              <FlaskConical size={16} />
              <span>SCIENTIFIC OBJECTIVE</span>
            </div>

            <h2>What the investigation examines</h2>

            <p>{fallback(record.objective)}</p>

            {!available(record.objective) && (
              <span className="detail-inline-note">
                <Info size={13} />
                OBJECTIVE NOT AVAILABLE IN CURRENT CATALOGUE
              </span>
            )}
          </article>

          <article className="detail-section">
            <div className="detail-section-title">
              <ChartNoAxesCombined size={16} />
              <span>RESEARCH APPROACH</span>
            </div>

            <h2>Experimental approach</h2>

            <p>
              {approachAvailable
                ? record.approach
                : "A detailed experimental procedure is not included in the current FLAME AI catalogue record. Open the original NASA PSI source for the investigation approach and experimental setup."
              }
            </p>

            {!approachAvailable && (
              <span className="detail-inline-note">
                <Info size={13} />
                SOURCE DETAILS NOT YET ADDED
              </span>
            )}
          </article>

          <article className="detail-section">
            <div className="detail-section-title">
              <BookOpen size={16} />
              <span>FINDINGS & SCIENTIFIC CONTEXT</span>
            </div>

            <h2>What the source reports</h2>

            <p>
              {findingsAvailable
                ? record.findings
                : "No verified findings have been added to this prototype record yet. FLAME AI will show findings here only when they can be linked to the original investigation or a cited publication."
              }
            </p>

            {!findingsAvailable && (
              <span className="detail-inline-note">
                <Info size={13} />
                NO VERIFIED FINDINGS ADDED
              </span>
            )}
          </article>

          <article className="detail-section">
            <div className="detail-section-title">
              <Tags size={16} />
              <span>RESEARCH KEYWORDS</span>
            </div>

            {tags.length > 0 ? (
              <div className="record-tags detail-tags">
                {tags.map(tag => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            ) : (
              <p>No research keywords are available in this record.</p>
            )}
          </article>

        </section>

        {/* SOURCE SIDEBAR */}
        <aside className="detail-aside">

          <section className="source-panel">

            <div className="detail-section-title">
              <Database size={16} />
              <span>DATA & SOURCE AVAILABILITY</span>
            </div>

            <Status value={record.status} />

            <h3>{statusTitle}</h3>

            <p>{statusDescription}</p>

            <div className="source-divider" />

            <div className="source-row">
              <FileText size={15} />

              <div>
                <b>NASA PSI investigation</b>
                <small>Original source search for {record.id}</small>
              </div>

              <a
                href={nasaUrl}
                target="_blank"
                rel="noreferrer"
                aria-label="Open NASA PSI investigation source"
              >
                <ArrowUpRight size={14} />
              </a>
            </div>

            <div className="source-row">
              <CalendarDays size={15} />

              <div>
                <b>Record year</b>
                <small>{fallback(record.year)}</small>
              </div>
            </div>

            <div className="source-row">
              <Database size={15} />

              <div>
                <b>Source collection</b>
                <small>{fallback(record.source)}</small>
              </div>
            </div>

            <div className="source-row">
              <BookOpen size={15} />

              <div>
                <b>DOI / publication</b>
                <small>
                  {available(record.doi)
                    ? record.doi
                    : "Not listed in current catalogue data"
                  }
                </small>
              </div>
            </div>

          </section>

          <section className="detail-section detail-availability">

            <div className="detail-section-title">
              <FileText size={15} />
              <span>FILES & PUBLICATIONS</span>
            </div>

            <h3>Source materials</h3>

            <p>
              Files, papers, videos and downloadable datasets
              will appear here when their links are confirmed
              from the NASA PSI record.
            </p>

            <div className="availability-empty">
              NO VERIFIED FILE LINKS IN THIS PROTOTYPE
            </div>

            <a
              className="source-open-link"
              href={nasaUrl}
              target="_blank"
              rel="noreferrer"
            >
              CHECK NASA SOURCE
              <ArrowUpRight size={13} />
            </a>

          </section>

          <div className="detail-disclaimer">
            <ShieldCheck size={15} />
            <div>
              <strong>SOURCE NOTE</strong>
              <p>
                This page separates catalogue metadata from
                verified experimental data. Missing procedures,
                findings, files and publications are not inferred
                or fabricated.
              </p>
            </div>
          </div>

        </aside>

      </div>

    </main>
  );
}
