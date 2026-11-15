
import React, { useState, useEffect } from "react";
import { Menu, ArrowUpRight, Flame } from "lucide-react";

import records from "./data/records";

import Home from "./pages/Home";
import Explorer from "./pages/Explorer";
import Compare from "./pages/Compare";
import Assistant from "./pages/Assistant";
import Insights from "./pages/Insights";
import Technology from "./pages/Technology";
import RecordDetail from "./pages/RecordDetail";

import { Footer } from "./components/Shared";

const nav = [
  ["ABOUT", "home"],
  ["RESEARCH", "explorer"],
  ["TECHNOLOGY", "technology"],
  ["AI ASSISTANT", "assistant"],
  ["EXPLORE", "insights"]
];

export default function App() {
  const [page, setPage] = useState(
    () => window.location.hash.replace("#", "") || "home"
  );

  const [query, setQuery] = useState("");
  const [program, setProgram] = useState("All");
  const [status, setStatus] = useState("All");
  const [type, setType] = useState("All");
  const [year, setYear] = useState("All");
  const [sort, setSort] = useState("Newest");

  const [selected, setSelected] = useState(null);
  const [compare, setCompare] = useState([]);

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Welcome to FLAME AI. Ask me about the investigations shown in this prototype. Answers are demo responses until the research assistant API is connected."
    }
  ]);

  const [question, setQuestion] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  // Synchronize the application with the URL hash
  useEffect(() => {
    const syncPage = () => {
      const next =
        window.location.hash.replace("#", "") || "home";

      setPage(next);

      if (next.startsWith("detail/")) {
        const id = next.split("/")[1];
        setSelected(records.find(r => r.id === id) || null);
      }
    };

    window.addEventListener("hashchange", syncPage);

    return () => {
      window.removeEventListener("hashchange", syncPage);
    };
  }, []);

  // Reveal elements when they enter the viewport
  useEffect(() => {
    const nodes = [
      ...document.querySelectorAll(".reveal-on-scroll")
    ];

    if (!("IntersectionObserver" in window)) {
      nodes.forEach(node =>
        node.classList.add("is-visible")
      );
      return;
    }

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.12,
        rootMargin: "0px 0px -40px 0px"
      }
    );

    nodes.forEach(node => observer.observe(node));

    return () => observer.disconnect();
  }, [page]);

  // Navigate between pages
  const navigate = p => {
    setMenuOpen(false);

    if (p !== page) {
      window.location.hash = p;
    }

    window.scrollTo({
      top: 0,
      behavior: "auto"
    });
  };

  // Add or remove investigations from comparison
  const toggleCompare = id => {
    setCompare(current =>
      current.includes(id)
        ? current.filter(x => x !== id)
        : current.length < 3
          ? [...current, id]
          : current
    );
  };

  // Open investigation details
  const openRecord = record => {
    setSelected(record);
    navigate(`detail/${record.id}`);
  };

  // Render the selected page
  const pageContent = () => {
    if (page === "home") {
      return (
        <Home
          records={records}
          onNavigate={navigate}
          onOpenRecord={openRecord}
        />
      );
    }

    if (page === "explorer") {
      return (
        <Explorer
          records={records}
          query={query}
          setQuery={setQuery}
          program={program}
          setProgram={setProgram}
          status={status}
          setStatus={setStatus}
          type={type}
          setType={setType}
          year={year}
          setYear={setYear}
          sort={sort}
          setSort={setSort}
          compare={compare}
          toggleCompare={toggleCompare}
          onOpenRecord={openRecord}
          onNavigate={navigate}
        />
      );
    }

    if (page === "compare") {
      return (
        <Compare
          records={records}
          compare={compare}
          toggleCompare={toggleCompare}
          onNavigate={navigate}
          onOpenRecord={openRecord}
        />
      );
    }

    if (page.startsWith("detail/")) {
      const record =
        selected ||
        records.find(r => r.id === page.split("/")[1]);

      return (
        <RecordDetail
          record={record}
          onBack={() => navigate("explorer")}
          onCompare={toggleCompare}
          selected={record ? compare.includes(record.id) : false}
        />
      );
    }

    if (page === "assistant") {
      return (
        <Assistant
          messages={messages}
          setMessages={setMessages}
          question={question}
          setQuestion={setQuestion}
        />
      );
    }

    if (page === "technology") {
      return (
        <Technology onNavigate={navigate} />
      );
    }

  if (page === "insights") {
  return (
    <Insights
      records={records}
      onNavigate={navigate}
      setQuery={setQuery}
      setProgram={setProgram}
    />
  );
}


return <Home records={records} onNavigate={navigate} />;
  };

  const activePage = page.startsWith("detail/")
    ? "explorer"
    : page;

  return (
    <div className="app-shell">

      <header className="site-header">

        <a
          className="brand"
          href="#"
          onClick={e => {
            e.preventDefault();
            navigate("home");
          }}
        >
          <span className="brand-mark">
            <Flame size={19} />
          </span>

          <span>
            <b>FLAME AI</b>
            <small>NASA SPACE APPS CHALLENGE 2026</small>
          </span>
        </a>

        <nav className="top-navigation">
          {nav.map(([label, target]) => (
            <button
              key={target}
              className={activePage === target ? "active" : ""}
              onClick={() => navigate(target)}
            >
              {label}
            </button>
          ))}
        </nav>

        <button
          className="launch-button"
          onClick={() => navigate("explorer")}
        >
          LAUNCH PLATFORM
          <ArrowUpRight size={13} />
        </button>

        <button
          className="mobile-menu"
          onClick={() => setMenuOpen(v => !v)}
          aria-label="Toggle navigation"
          aria-expanded={menuOpen}
        >
          <Menu />
        </button>

        {menuOpen && (
          <nav className="mobile-navigation">
            {nav.map(([label, target]) => (
              <button
                key={target}
                onClick={() => navigate(target)}
              >
                {label}
              </button>
            ))}
          </nav>
        )}

      </header>

      <div key={page} className="page-transition">
        {pageContent()}
      </div>

      <Footer />

    </div>
  );
}
