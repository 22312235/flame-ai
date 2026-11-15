
import React from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Flame,
  Sparkles,
  Orbit,
  Microscope,
  Database,
  ShieldCheck
} from "lucide-react";

const NASA_FLAME = "/images/flame_microgravity.png";

const NASA_SOFIE =
  "https://images-assets.nasa.gov/image/jsc2023e013681/jsc2023e013681~orig.jpg";

const NASA_STATION =
  "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=1200&q=90";

const stats = [
  {
    number: "01",
    icon: Microscope,
    title: "EXPERIMENTS",
    description: "NASA combustion investigations"
  },
  {
    number: "02",
    icon: Orbit,
    title: "RESEARCH PROGRAMS",
    description: "SAFFIRE · BASS · FLEX · ACME"
  },
  {
    number: "03",
    icon: Database,
    title: "SCIENTIFIC SOURCES",
    description: "Data, papers and mission records"
  }
];

export default function Home({
  records,
  onNavigate,
  onOpenRecord
}) {
  const spotlightRecords = records.slice(0, 3);

  return (
    <main className="home-page">

      {/* HERO */}
      <section className="hero">
        <div className="hero-bg" />

        <div className="hero-content">
          <div className="overline">
            NASA SPACE APPS CHALLENGE 2026
          </div>

          <div className="hero-coordinate">
            <span>SPACE RESEARCH / 001</span>
            <span>MICROGRAVITY COMBUSTION</span>
          </div>

          <h1>
            UNDERSTANDING
            <br />
            FIRE IN
            <br />
            <em>MICROGRAVITY</em>
          </h1>

          <p>
            Explore NASA's combustion research, connect
            experimental evidence, and uncover what fire
            teaches us about safer space exploration.
          </p>

          <div className="hero-actions">
            <button
              className="blue-button"
              onClick={() => onNavigate("explorer")}
            >
              EXPLORE RESEARCH
              <ArrowRight size={14} />
            </button>

            <button
              className="ghost-button"
              onClick={() => onNavigate("assistant")}
            >
              MEET THE AI
            </button>
          </div>

          <div className="hero-bottom-label">
            <span className="hero-scroll-line" />
            SCROLL TO EXPLORE
          </div>
        </div>

        <div className="hero-side-label">
          FLAME AI / RESEARCH PLATFORM
        </div>
      </section>

      {/* RESEARCH OVERVIEW */}
      <section className="three-stats">
        {stats.map(({ number, icon: Icon, title, description }) => (
          <article
            className="stat-card reveal-on-scroll"
            key={number}
          >
            <div className="stat-top">
              <small>{number}</small>
              <Icon size={19} />
            </div>

            <h3>{title}</h3>
            <p>{description}</p>
            <div className="stat-line" />
          </article>
        ))}
      </section>

      {/* MISSION */}
      <section className="editorial-section mission reveal-on-scroll">

        <div className="editorial-copy">
          <div className="overline">
            OUR MISSION / WHY IT MATTERS
          </div>

          <h2>
            FIRE BEHAVES
            <br />
            <em>DIFFERENT IN SPACE.</em>
          </h2>

          <p>
            Without buoyancy-driven flow, flames can take
            unfamiliar shapes and behave in ways that
            challenge assumptions. FLAME AI brings NASA
            combustion investigations into one place,
            making experiments easier to discover, compare
            and understand — with evidence and original
            sources kept in view.
          </p>

          <button
            className="text-link"
            onClick={() => onNavigate("explorer")}
          >
            DISCOVER THE COLLECTION
            <ArrowUpRight size={15} />
          </button>
        </div>

        <div
          className="editorial-image mission-background"
          role="img"
          aria-label="Earth and spacecraft viewed from orbit"
        >
          <div className="mission-image-overlay">
            <span>01 / THE ORBITAL ENVIRONMENT</span>
            <strong>UNDERSTANDING FIRE BEYOND EARTH</strong>
          </div>

          <span className="image-caption">
            ORBITAL RESEARCH ENVIRONMENT
          </span>
        </div>

      </section>

      {/* FLAME SCIENCE */}
      <section
        className="flame-feature reveal-on-scroll"
        style={{
          "--feature-image": `url("${NASA_FLAME}")`
        }}
      >
        <div className="flame-feature-content">
          <div className="overline">
            MICROGRAVITY COMBUSTION / NASA RESEARCH
          </div>

          <h2>
            THE SCIENCE BEHIND
            <br />
            <em>SAFER SPACEFLIGHT.</em>
          </h2>

          <p>
            Explore flame behavior observed aboard the
            International Space Station. NASA's SoFIE
            experiments investigate ignition, flame growth
            and extinction in microgravity.
          </p>

          <div className="feature-actions">
            <button
              className="blue-button"
              onClick={() => onNavigate("explorer")}
            >
              OPEN INVESTIGATION EXPLORER
              <ArrowRight size={14} />
            </button>

            <a
              className="text-link"
              href="https://www.nasa.gov/image-article/burning-microgravity/"
              target="_blank"
              rel="noreferrer"
            >
              NASA IMAGE SOURCE
              <ArrowUpRight size={13} />
            </a>
          </div>
        </div>

        <div className="feature-index">
          <Flame />
          <span>MICROGRAVITY FIRE STUDIES</span>
        </div>
      </section>

      {/* RESEARCH SPOTLIGHT */}
      <section className="program-section reveal-on-scroll">

        <div className="section-heading">
          <div>
            <div className="overline">
              NASA PSI COLLECTION
            </div>

            <h2>
              RESEARCH <em>SPOTLIGHT</em>
            </h2>

            <p>
              Start with selected investigations from the
              visible catalogue.
            </p>
          </div>

          <button
            className="text-link"
            onClick={() => onNavigate("explorer")}
          >
            VIEW ALL
            <ArrowUpRight size={14} />
          </button>
        </div>

        <div className="spotlight-grid">
          {spotlightRecords.map((record, index) => {
            const image = [
              NASA_FLAME,
              NASA_SOFIE,
              NASA_STATION
            ][index];

            return (
              <article
                className={`spot-card spot-card-${index} reveal-on-scroll`}
                key={record.id}
              >
                <div
                  className="spot-visual"
                  style={{
                    backgroundImage:
                      `linear-gradient(0deg,#06101df5,transparent 95%),url("${image}")`
                  }}
                >
                  <span>{record.program}</span>

                  <div className="spot-number">
                    0{index + 1}
                  </div>
                </div>

                <div className="spot-body">
                  <small>
                    {record.id} / {record.year}
                  </small>

                  <h3>{record.title}</h3>

                  <p>{record.summary}</p>

                  <button
                    className="text-link"
                    onClick={() => onOpenRecord(record)}
                  >
                    EXPLORE INVESTIGATION
                    <ArrowRight size={13} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>

      </section>

      {/* AI ASSISTANT */}
      <section className="assistant-banner assistant-banner-large reveal-on-scroll">

        <div
          className="assistant-banner-image"
          role="img"
          aria-label="Futuristic FLAME AI research workstation"
        />

        <div className="assistant-banner-copy">
          <div className="assistant-symbol">
            <Sparkles />
          </div>

          <div className="overline">
            FLAME AI / RESEARCH ASSISTANT
          </div>

          <h2>
            FROM COMPLEX EXPERIMENTS
            <br />
            <em>TO CLEARER INSIGHT.</em>
          </h2>

          <p>
            Explore NASA combustion investigations with
            a research interface designed to connect
            questions, experimental evidence and original
            sources.
          </p>

          <button
            className="blue-button"
            onClick={() => onNavigate("assistant")}
          >
            ENTER AI ASSISTANT
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="assistant-banner-index">
          <ShieldCheck size={15} />
          EVIDENCE-FOCUSED RESEARCH
        </div>

      </section>

      {/* CLOSING LABEL */}
      <div className="home-closing-label">
        <span>FLAME AI</span>
        <span>EXPLORING FIRE / ADVANCING UNDERSTANDING</span>
        <span>2026</span>
      </div>

    </main>
  );
}
