"""
Nerqon Quick Start
=======================

Get started with Nerqon in under 30 seconds.

1. Sign up at https://nidhitek.com/dashboard.html
2. Copy your API key
3. Run this script!
"""

from Nerqon import Nerqon

# ─── Connect ──────────────────────────────────────
client = Nerqon(api_key="nidx_your_api_key_here")

# ─── Check health ─────────────────────────────────
health = client.health()
print(f"API Status: {health.status}")

# ─── Add documents ────────────────────────────────
# In production, use embeddings from OpenAI, Cohere, HuggingFace, etc.
# Here we use dummy 384-dim vectors for demonstration.
import random
def random_vector(dim=384):
    return [random.uniform(-1, 1) for _ in range(dim)]

client.add(
    id="doc-1",
    text="Artificial intelligence is revolutionizing healthcare with early diagnosis.",
    vector=random_vector(),
    metadata={"category": "ai", "source": "research", "year": 2024},
)

client.add(
    id="doc-2",
    text="Machine learning models can predict protein structures with high accuracy.",
    vector=random_vector(),
    metadata={"category": "biotech", "source": "journal", "year": 2025},
)

client.add(
    id="doc-3",
    text="Neural networks are being used for real-time language translation.",
    vector=random_vector(),
    metadata={"category": "ai", "source": "blog", "year": 2024},
)

print("Added 3 documents.")

# ─── Search ───────────────────────────────────────
results = client.search(vector=random_vector(), top_k=3)

print(f"\nSearch returned {len(results.results)} results in {results.query_time_ms:.1f}ms:\n")
for r in results.results:
    print(f"  [{r.score:.4f}] {r.id}: {r.text[:60]}...")

# ─── Search with filters ─────────────────────────
results = client.search(
    vector=random_vector(),
    top_k=5,
    filters={"category": "ai"},
)
print(f"\nFiltered search (category=ai): {len(results.results)} results")

# ─── Get document ─────────────────────────────────
doc = client.get("doc-1")
print(f"\nDocument: {doc.id} — {doc.text[:60]}...")

# ─── Stats ────────────────────────────────────────
stats = client.stats()
print(f"\nIndex stats: {stats.total_documents} documents, dim={stats.dimension}")

# ─── Cleanup ──────────────────────────────────────
client.close()
print("\nDone! Visit https://nidhitek.com/documentation.html for full API reference.")
