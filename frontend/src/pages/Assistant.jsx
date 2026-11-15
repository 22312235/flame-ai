
import React from "react";
import {
  Sparkles,
  FileText,
  Send,
  Database,
  Search,
  ShieldCheck,
  Atom,
  MessageSquare,
  ArrowUpRight
} from "lucide-react";
import { PageTitle } from "../components/Shared";

const prompts = [
  {
    icon: Database,
    category: "INVESTIGATION",
    question: "What is the SAFFIRE experiment?"
  },
  {
    icon: Atom,
    category: "FLAME BEHAVIOR",
    question: "Explain flame extinction in microgravity."
  },
  {
    icon: Search,
    category: "RESEARCH DISCOVERY",
    question: "Which investigations mention smoke?"
  }
];

export default function Assistant({
  messages,
  setMessages,
  question,
  setQuestion
}) {
  function ask(e) {
    e.preventDefault();

    if (!question.trim()) return;

    const q = question.trim();

    setMessages(current => [
      ...current,
      { role: "user", text: q },
      {
        role: "assistant",
        text: `This prototype is not connected to the NASA research index or a verified AI model yet. To investigate "${q}", start with the Investigation Explorer and review the relevant PSI records. Once the backend and retrieval system are connected, this assistant can provide evidence-based answers with source citations.`
      }
    ]);

    setQuestion("");
  }

  return (
    <main className="inner-page assistant-page">

      <section className="assistant-page-visual">
        <img
          src="/images/ai_space_assistant.png"
          alt="Futuristic research workstation aboard a space station"
        />

        <div className="assistant-page-visual-copy">
          <div className="overline">
            FLAME AI / ORBITAL RESEARCH INTELLIGENCE
          </div>

          <h2>
            ASK. EXPLORE.
            <em> UNDERSTAND.</em>
          </h2>

          <p>
            Explore the science of combustion in microgravity
            through an intelligent research interface.
          </p>

          <div className="assistant-hero-tags">
            <span>MICROGRAVITY</span>
            <span>COMBUSTION SCIENCE</span>
            <span>RESEARCH AI</span>
          </div>
        </div>
      </section>

      <PageTitle
        eyebrow="04 / KNOWLEDGE DISCOVERY"
        title={<>AI RESEARCH <em>ASSISTANT</em></>}
        desc="A conversational research interface concept designed to make complex combustion investigations easier to explore and understand."
      />

      <section className="assistant-workspace">

        <aside className="assistant-sidebar">

          <div className="assistant-sidebar-heading">
            <span className="overline">RESEARCH ENVIRONMENT</span>
            <Atom size={20} />
          </div>

          <div className="assistant-sidebar-card">
            <Database size={21} />
            <div>
              <strong>NASA RESEARCH DATA</strong>
              <span>Investigation records</span>
            </div>
            <span className="sidebar-status">DEMO</span>
          </div>

          <div className="assistant-sidebar-card">
            <Search size={21} />
            <div>
              <strong>SEMANTIC SEARCH</strong>
              <span>Planned retrieval feature</span>
            </div>
          </div>

          <div className="assistant-sidebar-card">
            <ShieldCheck size={21} />
            <div>
              <strong>SOURCE TRACEABILITY</strong>
              <span>Citations planned</span>
            </div>
          </div>

          <div className="assistant-sidebar-note">
            <span className="overline">SCIENTIFIC PRINCIPLE</span>
            <p>
              Every research claim should be supported by
              an identifiable source. Missing evidence
              must remain clearly identified.
            </p>
          </div>

        </aside>

        <section className="chat-shell">

          <div className="chat-head">
            <div className="assistant-symbol">
              <Sparkles size={21} />
            </div>

            <div className="chat-head-copy">
              <h3>FLAME AI / RESEARCH COPILOT</h3>
              <p>
                <i className="live-dot" />
                DEMO MODE · BACKEND NOT CONNECTED
              </p>
            </div>

            <span className="demo">PROTOTYPE</span>
          </div>

          <div className="chat-context-bar">
            <span>
              <MessageSquare size={13} />
              RESEARCH CONVERSATION
            </span>
            <span>MICROGRAVITY COMBUSTION</span>
          </div>

          <div className="chat-messages">
            {messages.map((message, index) => (
              <div
                key={index}
                className={"message " + message.role}
              >
                <div className="message-avatar">
                  {message.role === "assistant"
                    ? <Sparkles size={15} />
                    : "YOU"}
                </div>

                <div className="message-bubble">
                  <span className="message-label">
                    {message.role === "assistant"
                      ? "FLAME AI"
                      : "YOUR QUESTION"}
                  </span>

                  <p>{message.text}</p>

                  {message.role === "assistant" && index > 0 && (
                    <div className="citation-note">
                      <FileText size={12} />
                      Source citations unavailable in demo mode
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="assistant-prompt-area">
            <div className="suggestions-heading">
              <span className="overline">START YOUR RESEARCH</span>
              <span>SELECT A QUESTION</span>
            </div>

            <div className="suggestions">
              {prompts.map(({ icon: Icon, category, question: prompt }) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setQuestion(prompt)}
                >
                  <Icon size={17} />
                  <span>
                    <small>{category}</small>
                    <strong>{prompt}</strong>
                  </span>
                  <ArrowUpRight size={14} />
                </button>
              ))}
            </div>
          </div>

          <form className="chat-input" onSubmit={ask}>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="Ask about microgravity combustion research..."
              aria-label="Ask a research question"
            />

            <button
              className="send-button"
              type="submit"
              disabled={!question.trim()}
              aria-label="Send question"
            >
              <Send size={16} />
            </button>
          </form>

          <div className="chat-disclaimer">
            <ShieldCheck size={12} />
            AI-GENERATED RESEARCH RESPONSES WILL REQUIRE VERIFIED SOURCES
          </div>

        </section>
      </section>

    </main>
  );
}
