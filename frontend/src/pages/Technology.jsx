
import React from "react";
import {
  Database,
  FileText,
  Scissors,
  Layers3,
  Search,
  BrainCircuit,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Network
} from "lucide-react";
import { PageTitle } from "../components/Shared";

const stages = [
  {
    number: "01",
    icon: FileText,
    title: "NASA RESEARCH SOURCES",
    subtitle: "The knowledge foundation",
    description:
      "Collect available NASA investigation records, scientific publications, experiment documents and research datasets.",
    output: "Research documents and source metadata"
  },
  {
    number: "02",
    icon: Database,
    title: "DOCUMENT PROCESSING",
    subtitle: "Preparing scientific content",
    description:
      "Extract text, normalize document content and prepare research materials for structured processing.",
    output: "Clean and structured research text"
  },
  {
    number: "03",
    icon: Scissors,
    title: "TEXT CHUNKING",
    subtitle: "Organizing information",
    description:
      "Divide longer documents into smaller, meaningful sections while preserving their context and source references.",
    output: "Searchable research passages"
  },
  {
    number: "04",
    icon: Layers3,
    title: "KNOWLEDGE INDEXING",
    subtitle: "Building the research index",
    description:
      "Generate numerical embeddings from text passages and organize them for semantic retrieval.",
    output: "Indexed research representations"
  },
  {
    number: "05",
    icon: Search,
    title: "EVIDENCE RETRIEVAL",
    subtitle: "Finding relevant research",
    description:
      "Analyze a question and retrieve the most relevant indexed passages to support the response.",
    output: "Relevant evidence and source references"
  },
  {
    number: "06",
    icon: BrainCircuit,
    title: "AI RESPONSE GENERATION",
    subtitle: "Turning evidence into insight",
    description:
      "Use the retrieved context to formulate a clear response, while identifying information that the available sources do not support.",
    output: "A research-grounded answer"
  },
  {
    number: "07",
    icon: ShieldCheck,
    title: "SOURCE TRACEABILITY",
    subtitle: "Keeping evidence visible",
    description:
      "Present supporting source references and distinguish documented findings from missing information and AI interpretation.",
    output: "Traceable answers and citations"
  }
];

export default function Technology({ onNavigate }) {
  return (
    <main className="inner-page technology-page">

      <PageTitle
        eyebrow="03 / SYSTEM ARCHITECTURE"
        title={<>THE TECHNOLOGY <em>BEHIND FLAME AI</em></>}
        desc="Discover how scientific documents become searchable research knowledge and how an evidence-first AI assistant can help explore combustion experiments in microgravity."
      />

      <section className="technology-hero">
        <div className="technology-hero-copy">
          <span className="overline">FROM RESEARCH DATA TO SCIENTIFIC INSIGHT</span>
          <h2>
            A RESEARCH PIPELINE.
            <br />
            <em>BUILT AROUND EVIDENCE.</em>
          </h2>
          <p>
            FLAME AI is designed to connect scientific sources,
            intelligent retrieval and AI-assisted interpretation
            in one research environment.
          </p>
          <button
            className="blue-button"
            onClick={() => onNavigate("assistant")}
          >
            EXPLORE THE AI ASSISTANT <ArrowRight size={14} />
          </button>
        </div>
        <div className="technology-hero-visual">
          <Network size={72} strokeWidth={1} />
          <span>RESEARCH KNOWLEDGE SYSTEM</span>
          <div className="technology-orbit orbit-one" />
          <div className="technology-orbit orbit-two" />
        </div>
      </section>

      <section className="technology-section-heading">
        <span className="overline">THE PROCESS / 07 STAGES</span>
        <h2>HOW FLAME AI <em>WORKS</em></h2>
        <p>
          Follow the journey from original research material
          to a source-aware AI response.
        </p>
      </section>

      <section className="technology-pipeline">
        {stages.map((stage, index) => {
          const Icon = stage.icon;

          return (
            <article className="technology-stage" key={stage.number}>
              <div className="technology-stage-index">
                <span>{stage.number}</span>
                <div className="technology-stage-line" />
              </div>

              <div className="technology-stage-icon">
                <Icon size={23} />
              </div>

              <div className="technology-stage-content">
                <span className="overline">{stage.subtitle}</span>
                <h3>{stage.title}</h3>
                <p>{stage.description}</p>
                <div className="technology-output">
                  <span>OUTPUT</span>
                  <strong>{stage.output}</strong>
                </div>
              </div>

              <div className="technology-stage-arrow">
                {index !== stages.length - 1 && <ArrowRight size={17} />}
              </div>
            </article>
          );
        })}
      </section>

      <section className="technology-integrity">
        <div className="technology-integrity-icon">
          <ShieldCheck size={27} />
        </div>
        <div>
          <span className="overline">SCIENTIFIC INTEGRITY</span>
          <h2>NO EVIDENCE. NO CLAIM.</h2>
          <p>
            The system must not invent experimental results,
            measurements or scientific conclusions. Answers
            should be grounded in available research sources,
            with missing evidence clearly identified.
          </p>
        </div>
      </section>

      <section className="technology-cta">
        <Sparkles size={23} />
        <span className="overline">READY TO EXPLORE?</span>
        <h2>ASK QUESTIONS. <em>FOLLOW THE EVIDENCE.</em></h2>
        <button
          className="blue-button"
          onClick={() => onNavigate("assistant")}
        >
          OPEN RESEARCH ASSISTANT <ArrowRight size={14} />
        </button>
      </section>

      <p className="technology-disclaimer">
        ARCHITECTURE OVERVIEW — This page describes the intended
        FLAME AI research workflow. Individual processing and
        AI capabilities depend on backend integration and
        verified source availability.
      </p>

    </main>
  );
}
