
import re
import ollama


def format_citations(
    answer: str,
    retrieved_chunks: list[dict]
) -> str:

    def replace_reference(match):
        evidence_id = int(match.group(1))

        if evidence_id < 1 or evidence_id > len(retrieved_chunks):
            return f"[Invalid evidence reference: E{evidence_id}]"

        chunk = retrieved_chunks[evidence_id - 1]

        return (
            f"[Source: {chunk['source']}, "
            f"Page: {chunk['page_number']}]"
        )

    return re.sub(
        r"\[E(\d+)\]",
        replace_reference,
        answer
    )


def generate_answer(
    query: str,
    retrieved_chunks: list[dict],
    model: str = "qwen3.5:4b"
) -> str:

    if not query.strip():
        raise ValueError("Query cannot be empty.")

    if not retrieved_chunks:
        return "Insufficient evidence in the provided documents."

    evidence = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        evidence.append(
            f"""
[E{index}]
Source: {chunk['source']}
Page: {chunk['page_number']}
Text:
{chunk['text']}
"""
        )

    context = "\n".join(evidence)

    system_prompt = """
You are FLAME AI, a scientific research assistant
specialized in combustion research.

Use ONLY the provided evidence.

STRICT RULES:

1. Never invent facts or use outside knowledge.
2. Cite every scientific claim using evidence IDs:
   [E1], [E2], [E3], etc.
3. Use ONLY evidence IDs that exist in the provided context.
4. Never create source names or page numbers.
5. Distinguish experimental observations from simulations,
   predictions, hypotheses, and research objectives.
6. Do not claim that a condition caused an outcome unless
   the evidence explicitly establishes that relationship.
7. If evidence is insufficient, clearly state what is unknown.
8. Keep answers concise and focused on the question.
9. Ensure the answer is complete.
10. Use evidence IDs only. The application formats citations.
11. Never interpret research objectives, hypotheses, or planned
    test conditions as confirmed experimental results.
12. When asked what was actually observed, prioritize explicit
    experimental results over research objectives and hypotheses.
13. If evidence does not confirm a successful experimental
    outcome, do not claim that it was successful.
14. When evidence directly answers the question,
    state confirmed facts clearly and directly.
15. If only some requested details are missing,
    answer supported parts and identify missing details.
16. Answer only what the user asks.
17. Do not describe confirmed information as unconfirmed.
18. Do not mention missing information the user did not ask about.
19. Do not repeat facts or citations unnecessarily.
20. Prefer a direct answer in one short paragraph.
"""

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"Evidence:\n{context}\n\n"
                    "Answer using only the evidence. "
                    "Cite every factual claim with its evidence ID. "
                    "Do not include unrelated information."
                )
            }
        ],
        think=False,
        options={
            "num_predict": 300,
            "temperature": 0.1
        }
    )

    answer = response["message"]["content"]

    return format_citations(
        answer=answer,
        retrieved_chunks=retrieved_chunks
    )
