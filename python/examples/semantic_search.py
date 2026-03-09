"""
Semantic Search with Metadata Filtering
=========================================

This example demonstrates:
- Adding documents with rich metadata
- Searching with metadata filters (Query DSL)
- Using namespaces for data isolation
- Batch document ingestion
"""

from Nerqon import Nerqon

# Dummy embedding function — replace with your actual embedding model
import random
def embed(text, dim=384):
    import hashlib
    random.seed(hashlib.md5(text.encode()).hexdigest())
    return [random.uniform(-1, 1) for _ in range(dim)]


def main():
    client = Nerqon(
        api_key="nidx_your_api_key_here",
        namespace="research-papers",
    )

    # ─── Batch ingest research papers ─────────────
    papers = [
        {
            "id": "paper-001",
            "text": "Attention Is All You Need — Transformer architecture for sequence modeling",
            "vector": embed("Attention Is All You Need"),
            "metadata": {"year": 2017, "category": "nlp", "citations": 90000, "venue": "NeurIPS"},
        },
        {
            "id": "paper-002",
            "text": "BERT: Pre-training of Deep Bidirectional Transformers",
            "vector": embed("BERT pre-training bidirectional transformers"),
            "metadata": {"year": 2018, "category": "nlp", "citations": 75000, "venue": "NAACL"},
        },
        {
            "id": "paper-003",
            "text": "GPT-4 Technical Report — Large multimodal model capabilities",
            "vector": embed("GPT-4 large multimodal model"),
            "metadata": {"year": 2023, "category": "llm", "citations": 5000, "venue": "arXiv"},
        },
        {
            "id": "paper-004",
            "text": "AlphaFold: Protein structure prediction using deep learning",
            "vector": embed("AlphaFold protein structure prediction"),
            "metadata": {"year": 2021, "category": "biotech", "citations": 20000, "venue": "Nature"},
        },
        {
            "id": "paper-005",
            "text": "Stable Diffusion: High-resolution image synthesis with latent diffusion",
            "vector": embed("Stable Diffusion image synthesis latent diffusion"),
            "metadata": {"year": 2022, "category": "cv", "citations": 12000, "venue": "CVPR"},
        },
    ]

    result = client.add_batch(papers)
    print(f"Batch ingested: {result}")

    # ─── Search: All papers ───────────────────────
    query = "transformer language model"
    results = client.search(vector=embed(query), top_k=5)
    print(f"\nSearch: '{query}'")
    for r in results.results:
        print(f"  [{r.score:.4f}] {r.id}: {r.text[:60]}...")

    # ─── Search with filter: NLP only ─────────────
    results = client.search(
        vector=embed(query),
        top_k=5,
        filters={"category": "nlp"},
    )
    print(f"\nFiltered (category=nlp):")
    for r in results.results:
        print(f"  [{r.score:.4f}] {r.id}: {r.text[:60]}...")

    # ─── Search with complex filter ───────────────
    results = client.search(
        vector=embed("deep learning breakthroughs"),
        top_k=5,
        filters={
            "year": {"$gte": 2021},
            "citations": {"$gte": 10000},
        },
    )
    print(f"\nFiltered (year>=2021, citations>=10000):")
    for r in results.results:
        print(f"  [{r.score:.4f}] {r.id} — {r.metadata}")

    # ─── Namespace isolation ──────────────────────
    namespaces = client.list_namespaces()
    print(f"\nNamespaces: {[ns.name for ns in namespaces]}")

    stats = client.stats()
    print(f"Stats: {stats.total_documents} docs, dim={stats.dimension}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
