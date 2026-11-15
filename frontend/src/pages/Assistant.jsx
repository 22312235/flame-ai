
import React, { useState } from "react";
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

const API_URL = "http://127.0.0.1:8000";

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
  const [isLoading, setIsLoading] = useState(false);

  async function ask(e) {
    e.preventDefault();

    const q = question.trim();

    if (!q || isLoading) return;

    setQuestion("");
    setIsLoading(true);

    setMessages(current => [
      ...current,
      { role: "user", text: q },
      {
        role: "assistant",
        text: "Searching NASA research documents and analyzing evidence...",
        loading: true
      }
    ]);

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question: q
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "The AI service could not process your question."
        );
      }

      setMessages(current => [
        ...current.slice(0, -1),
        {
          role: "assistant",
          text: data.answer,
          sources: data.sources || []
        }
      ]);

    } catch (error) {
      setMessages(current => [
        ...current.slice(0, -1),
        {
          role: "assistant",
          text: `Unable to contact FLAME AI: ${error.message}`,
          error: true
        }
      ]);

    } finally {
      setIsLoading(false);
    }
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
        desc="Explore combustion research through AI-powered document retrieval and evidence-based answers."
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
              <span>Indexed research documents</span>
            </div>
            <span className="sidebar-status">ACTIVE</span>
          </div>

          <div className="assistant-sidebar-card">
            <Search size={21} />
            <div>
              <strong>SEMANTIC SEARCH</strong>
              <span>AI-powered retrieval</span>
            </div>
          </div>

          <div className="assistant-sidebar-card">
            <ShieldCheck size={21} />
            <div>
              <strong>SOURCE TRACEABILITY</strong>
              <span>Document and page citations</span>
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
                AI RESEARCH SERVICE
              </p>
            </div>

            <span className="demo">
              {isLoading ? "PROCESSING" : "AI POWERED"}
            </span>
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

                  {message.loading && (
                    <div className="citation-note">
                      <Search size={12} />
                      Retrieving relevant research evidence...
                    </div>
                  )}

                  {message.error && (
                    <div className="citation-note">
                      <ShieldCheck size={12} />
                      Check that the AI server is running.
                    </div>
                  )}

                  {message.sources?.length > 0 && (
                    <div className="citation-note">
                      <FileText size={12} />

                      <span>
                        **RESEARCH SOURCES**

                        {message.sources.map((source, i) => (
                          <span key={i}>
                            {source.source}, Page {source.page}
                            {source.similarity !== undefined
                              ? ` (Relevance: ${(source.similarity * 100).toFixed(1)}%)`
                              : ""}
                            {i < message.sources.length - 1
                              ? " · "
                              : ""}
                          </span>
                        ))}
                      </span>
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
                  disabled={isLoading}
                  onClick={() => {
                    setQuestion(prompt);
                   ask({
                     preventDefault: () => {}
                     });
}}
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
              disabled={isLoading}
            />

            <button
              className="send-button"
              type="submit"
              disabled={!question.trim() || isLoading}
              aria-label="Send question"
            >
              <Send size={16} />
            </button>

          </form>

          <div className="chat-disclaimer">
            <ShieldCheck size={12} />
            AI-GENERATED RESPONSES WITH RETRIEVED RESEARCH SOURCES
          </div>

        </section>
      </section>

    </main>
  );
}
