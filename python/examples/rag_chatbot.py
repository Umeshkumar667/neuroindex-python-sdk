"""
Build a RAG Chatbot with Nerqon + OpenAI
=============================================

This example shows how to build a Retrieval-Augmented Generation (RAG)
chatbot using Nerqon for vector storage and OpenAI for embeddings + generation.

Requirements:
    pip install Nerqon openai
"""

from Nerqon import Nerqon

# Optional: uncomment if you have openai installed
# import openai
# openai.api_key = "sk-your-openai-key"


def get_embedding(text: str, dim=384):
    """
    Get embedding from OpenAI or any embedding provider.
    Replace this with your actual embedding model.
    """
    # ─── With OpenAI ──────────────────────────────
    # response = openai.embeddings.create(
    #     model="text-embedding-3-small",
    #     input=text,
    # )
    # return response.data[0].embedding

    # ─── Dummy embeddings for demo ────────────────
    import hashlib
    import random
    random.seed(hashlib.md5(text.encode()).hexdigest())
    return [random.uniform(-1, 1) for _ in range(dim)]


def main():
    # ─── Setup Nerqon ─────────────────────────
    client = Nerqon(
        api_key="nidx_your_api_key_here",
        namespace="rag-chatbot",
    )

    # ─── Index your knowledge base ────────────────
    knowledge_base = [
        {
            "id": "kb-1",
            "text": "Nerqon supports three search modes: vector similarity, "
                    "semantic graph traversal, and hybrid keyword reranking.",
        },
        {
            "id": "kb-2",
            "text": "To add documents, use the POST /v1/documents endpoint with "
                    "an id, text, vector, and optional metadata.",
        },
        {
            "id": "kb-3",
            "text": "Nerqon uses namespaces for multi-tenant isolation. "
                    "Each namespace has its own index and configuration.",
        },
        {
            "id": "kb-4",
            "text": "The free trial includes 10,000 documents and 1,000 API calls "
                    "per day for 15 days. No credit card required.",
        },
        {
            "id": "kb-5",
            "text": "Nerqon can be self-hosted using Docker. Run: "
                    "docker run -p 8000:8000 nidhitek/Nerqon",
        },
    ]

    print("Indexing knowledge base...")
    for doc in knowledge_base:
        embedding = get_embedding(doc["text"])
        client.add(
            id=doc["id"],
            text=doc["text"],
            vector=embedding,
            metadata={"type": "knowledge_base"},
        )
    print(f"Indexed {len(knowledge_base)} documents.\n")

    # ─── RAG Query Loop ──────────────────────────
    print("RAG Chatbot ready! Type 'quit' to exit.\n")

    while True:
        query = input("You: ").strip()
        if not query or query.lower() == "quit":
            break

        # Step 1: Embed the query
        query_vector = get_embedding(query)

        # Step 2: Retrieve relevant context from Nerqon
        results = client.search(vector=query_vector, top_k=3)

        context = "\n".join([
            f"- {r.text}" for r in results.results
        ])

        # Step 3: Generate response with context (using OpenAI or any LLM)
        prompt = f"""Answer the user's question using ONLY the context below.
If the context doesn't contain the answer, say "I don't have that information."

Context:
{context}

Question: {query}

Answer:"""

        # ─── With OpenAI ──────────────────────────
        # response = openai.chat.completions.create(
        #     model="gpt-4o-mini",
        #     messages=[{"role": "user", "content": prompt}],
        # )
        # answer = response.choices[0].message.content

        # ─── Without OpenAI (show retrieved context) ──
        print(f"\nBot: Based on {len(results.results)} relevant documents:")
        for r in results.results:
            print(f"  [{r.score:.3f}] {r.text[:100]}")
        print()

    client.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()
