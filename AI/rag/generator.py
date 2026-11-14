
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
8. Give a concise answer (maximum 120 words).
9. Ensure the answer is complete.
10. Do not use citations such as [Source: ...].
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
                    "Answer the question using only the evidence. "
                    "Cite every factual claim with its evidence ID."
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

    answer = format_citations(
        answer=answer,
        retrieved_chunks=retrieved_chunks
    )

    return answer
