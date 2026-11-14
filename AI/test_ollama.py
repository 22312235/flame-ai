
import ollama

# 1. Test the embedding model
print("Testing embedding model...")

embedding_response = ollama.embed(
    model="nomic-embed-text:latest",
    input="Microgravity affects flame behavior and combustion."
)

embedding = embedding_response["embeddings"][0]

print("Embedding successful!")
print("Vector dimensions:", len(embedding))


# 2. Test the language model
print("\nTesting language model...")

response = ollama.chat(
    model="qwen3.5:4b",
    messages=[
        {
            "role": "user",
            "content": "In two sentences, explain how microgravity affects combustion."
        }
    ]
)

print("LLM response:")
print(response["message"]["content"])
