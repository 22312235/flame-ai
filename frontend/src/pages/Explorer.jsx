
import React, { useMemo } from "react";
import {
  Search,
  X,
  Flame,
  Plus,
  Check,
  ChevronRight,
  ArrowRight,
  SlidersHorizontal,
  Database,
  Layers3,
  CalendarDays,
  FileSearch,
  Filter,
  GitCompareArrows
} from "lucide-react";
import { PageTitle, Status } from "../components/Shared";
export default function Explorer({
  records,
  query,
  setQuery,
  program,
  setProgram,
  status,
  setStatus,
  type,
  setType,
  year,
  setYear,
  sort,
  setSort,
  compare,
  toggleCompare,
  onOpenRecord,
  onNavigate
}) {
  const programs = useMemo(
    () => [...new Set(records.map(r => r.program))].sort(),
    [records]
  );

  const types = useMemo(
    () => [...new Set(records.map(r => r.type))].sort(),
    [records]
  );

  const years = useMemo(
    () => [...new Set(records.map(r => String(r.year)))].sort(
      (a, b) => Number(b) - Number(a)
    ),
    [records]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();

    return records
      .filter(r =>
        (!q ||
          `${r.id} ${r.title} ${r.program} ${r.type} ${r.summary} ${r.tags.join(" ")}`
            .toLowerCase()
            .includes(q)
        ) &&
        (program === "All" || r.program === program) &&
        (status === "All" || r.status === status) &&
        (type === "All" || r.type === type) &&
        (year === "All" || String(r.year) === year)
      )
      .sort((a, b) =>
        sort === "Oldest"
          ? a.year - b.year
          : sort === "Title A–Z"
            ? a.title.localeCompare(b.title)
            : sort === "Title Z–A"
              ? b.title.localeCompare(a.title)
              : b.year - a.year
      );
  }, [records, query, program, status, type, year, sort]);

  const indexed = records.filter(r => r.status === "Indexed").length;
  const metadata = records.filter(r => r.status === "Metadata only").length;
  const processing = records.filter(r => r.status === "Processing").length;
  const researchPrograms = programs.length;

  const activeFilters = [
    query.trim() && {
      label: `Search: ${query}`,
      clear: () => setQuery("")
    },
    program !== "All" && {
      label: program,
      clear: () => setProgram("All")
    },
    type !== "All" && {
      label: type,
      clear: () => setType("All")
    },
    status !== "All" && {
      label: status,
      clear: () => setStatus("All")
    },
    year !== "All" && {
      label: year,
      clear: () => setYear("All")
    }
  ].filter(Boolean);

  const clearFilters = () => {
    setQuery("");
    setProgram("All");
    setStatus("All");
    setType("All");
    setYear("All");
    setSort("Newest");
  };

  return (
    <main className="inner-page explorer-page">

      <PageTitle
        eyebrow="01 / NASA PHYSICAL SCIENCES INFORMATICS"
        title={<>INVESTIGATION <em>EXPLORER</em></>}
        desc="Search, filter and inspect NASA investigation records. Open a record to explore its research summary, objectives and original source."
      />

      {/* CATALOGUE METRICS */}
      <section className="explorer-metrics" aria-label="Catalogue summary">

        <div className="explorer-metric">
          <span><Database size={15} /></span>
          <div>
            <strong>{records.length}</strong>
            <small>CATALOGUE RECORDS</small>
          </div>
        </div>

        <div className="explorer-metric">
          <span><Layers3 size={15} /></span>
          <div>
            <strong>{researchPrograms}</strong>
            <small>RESEARCH PROGRAMS</small>
          </div>
        </div>

        <div className="explorer-metric">
          <span><Check size={15} /></span>
          <div>
            <strong>{indexed}</strong>
            <small>INDEXED RECORDS</small>
          </div>
        </div>

        <div className="explorer-metric">
          <span><FileSearch size={15} /></span>
          <div>
            <strong>{metadata}</strong>
            <small>METADATA ONLY</small>
          </div>
        </div>

        <div className="explorer-metric">
          <span><CalendarDays size={15} /></span>
          <div>
            <strong>{processing}</strong>
            <small>PROCESSING</small>
          </div>
        </div>

      </section>


      {/* FILTERS */}
      <div className="explorer-toolbar-label">
        <span>
          <SlidersHorizontal size={13} />
          CATALOGUE SEARCH & FILTERS
        </span>

        <button onClick={clearFilters}>
          RESET FILTERS <X size={12} />
        </button>
      </div>

      <section className="filter-panel explorer-filters">

        <div className="searchbox">
          <Search size={16} />

          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search PSI ID, title, program, keywords or research type..."
            aria-label="Search investigations"
          />

          {query && (
            <button
              onClick={() => setQuery("")}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <select
          aria-label="Research program"
          value={program}
          onChange={e => setProgram(e.target.value)}
        >
          <option value="All">All programs</option>
          {programs.map(p => <option key={p}>{p}</option>)}
        </select>

        <select
          aria-label="Research category"
          value={type}
          onChange={e => setType(e.target.value)}
        >
          <option value="All">All categories</option>
          {types.map(t => <option key={t}>{t}</option>)}
        </select>

        <select
          aria-label="Indexing status"
          value={status}
          onChange={e => setStatus(e.target.value)}
        >
          <option value="All">All statuses</option>
          <option>Indexed</option>
          <option>Metadata only</option>
          <option>Processing</option>
        </select>

        <select
          aria-label="Year"
          value={year}
          onChange={e => setYear(e.target.value)}
        >
          <option value="All">All years</option>
          {years.map(y => <option key={y}>{y}</option>)}
        </select>

        <select
          aria-label="Sort records"
          value={sort}
          onChange={e => setSort(e.target.value)}
        >
          <option>Newest</option>
          <option>Oldest</option>
          <option>Title A–Z</option>
          <option>Title Z–A</option>
        </select>

      </section>

      {/* ACTIVE FILTERS */}
      {activeFilters.length > 0 && (
        <div className="active-filter-row">
          <span><Filter size={12} /> ACTIVE FILTERS</span>

          <div className="active-filter-chips">
            {activeFilters.map((filter, index) => (
              <button
                key={index}
                onClick={filter.clear}
                title={`Remove ${filter.label}`}
              >
                {filter.label}
                <X size={12} />
              </button>
            ))}
          </div>

          <button
            className="clear-active-filters"
            onClick={clearFilters}
          >
            CLEAR ALL
          </button>
        </div>
      )}

      {/* RESULTS HEADER */}
      <div className="records-heading">
        <div>
          <span className="overline">NASA PSI COLLECTION</span>
          <h2>AVAILABLE INVESTIGATIONS</h2>
        </div>

        <span className="result-count">
          SHOWING {filtered.length} OF {records.length} RECORDS
        </span>
      </div>

      {/* RECORD LIST */}
      <div className="record-list">

        {filtered.map((r, index) => (
          <article className="record-row" key={r.id}>

            <div className="record-glyph">
              <Flame />
              <small>{String(index + 1).padStart(2, "0")}</small>
            </div>

            <div className="record-main">

              <div className="record-top">
                <span>{r.id} / {r.program}</span>
                <Status value={r.status} />
              </div>

              <h3>{r.title}</h3>

              <p>{r.summary}</p>

              <div className="record-tags">
                {r.tags.map(t => (
                  <span key={t}>{t}</span>
                ))}
              </div>

            </div>

            <div className="record-actions">

              <span className="record-year">{r.year}</span>

              <button
                className="outline-button"
                onClick={() => onOpenRecord(r)}
              >
                DETAILS <ChevronRight size={13} />
              </button>

              <button
                aria-label={
                  compare.includes(r.id)
                    ? `Remove ${r.id} from comparison`
                    : `Add ${r.id} to comparison`
                }
                title={
                  compare.includes(r.id)
                    ? "Remove from comparison"
                    : compare.length >= 3
                      ? "Comparison limit reached"
                      : "Add to comparison"
                }
                disabled={!compare.includes(r.id) && compare.length >= 3}
                className={
                  "compare-toggle " +
                  (compare.includes(r.id) ? "chosen" : "")
                }
                onClick={() => toggleCompare(r.id)}
              >
                {compare.includes(r.id)
                  ? <Check size={15} />
                  : <Plus size={15} />
                }
              </button>

            </div>

          </article>
        ))}

        {!filtered.length && (
          <div className="empty explorer-empty">
            <div className="empty-icon">
              <Search size={25} />
            </div>

            <span className="overline">NO RESULTS FOUND</span>

            <h3>No matching investigations</h3>

            <p>
              We couldn't find records matching your current
              search and filters. Try another keyword or reset
              the catalogue filters.
            </p>

            <button
              className="blue-button"
              onClick={clearFilters}
            >
              RESET SEARCH <X size={13} />
            </button>
          </div>
        )}

      </div>

      {/* COMPARISON BAR */}
      <section className="compare-inline">

        <div className="compare-inline-icon">
          <GitCompareArrows size={21} />
        </div>

        <div className="compare-inline-copy">
          <strong>{compare.length} / 3 INVESTIGATIONS SELECTED</strong>

          <small>
            {compare.length < 2
              ? "Select at least two investigations to compare their catalogue details."
              : compare.length === 3
                ? "Your three investigations are ready to compare."
                : "Your selections are ready for comparison."
            }
          </small>
        </div>

        <button
          className="blue-button"
          disabled={compare.length < 2}
          onClick={() => onNavigate("compare")}
        >
          OPEN COMPARISON LAB
          <ArrowRight size={14} />
        </button>

      </section>

      <p className="catalogue-note">
        <CalendarDays size={13} />
        Catalogue counts are calculated from the records currently
        loaded in this prototype. Indexing status describes FLAME AI
        availability, not NASA's original record status.
      </p>

    </main>
  );
}
