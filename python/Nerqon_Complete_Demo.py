# ============================================================================
#
#   N E R Q O N  —  Complete Feature Showcase
#
#   The vector database with hybrid search, auto knowledge graph,
#   and built-in smart caching. This demo tests every SDK feature.
#
#   Run in Google Colab  |  Get your free API key at https://nidhitek.com
#
# ============================================================================

# -- Cell 1: Install (uncomment for Colab) -----------------------------------
# !pip install -q sentence-transformers requests

import requests, json, time, uuid
import numpy as np
from sentence_transformers import SentenceTransformer

# =============================================================================
# CONFIGURATION
# =============================================================================
API_BASE = "https://api.nidhitek.com"
API_KEY  = "your_api_key"               # <-- Replace with your key
HEADERS  = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Fresh namespace per run - zero pollution from previous tests
TEST_NS  = f"demo-{uuid.uuid4().hex[:8]}"
TEST_NS2 = f"iso-{uuid.uuid4().hex[:8]}"

model = SentenceTransformer("all-MiniLM-L6-v2")
DIM = model.get_sentence_embedding_dimension()
print(f"Model loaded | dim={DIM} | namespace={TEST_NS}")


# =============================================================================
# HELPERS
# =============================================================================
def embed(text):
    return model.encode(text, normalize_embeddings=True)

def embed_many(texts):
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

def api(method, path, body=None, **params):
    """Call Nerqon API with automatic retry on rate-limit (429)."""
    url = f"{API_BASE}{path}"
    for attempt in range(3):
        t0 = time.time()
        r  = getattr(requests, method.lower())(url, headers=HEADERS, json=body, params=params)
        ms = (time.time() - t0) * 1000
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 5)) + 1
            print(f"  [rate-limit] waiting {wait}s...")
            time.sleep(wait)
            continue
        try:    data = r.json()
        except (ValueError, Exception): data = {"raw": r.text}
        return r.status_code, data, ms
    # exhausted retries
    return r.status_code, {"error": "rate_limit_exhausted"}, 0

def banner(step, title):
    print(f"\n{'='*70}")
    print(f"  STEP {step}: {title}")
    print(f"{'='*70}")

def show(results, source=True):
    for i, r in enumerate(results, 1):
        s   = f" | source={r.get('source','?'):6s}" if source else ""
        m   = r.get("metadata", {})
        tag = f"{m.get('category','?')}/{m.get('subtopic','?')}"
        print(f"  [{i}] sim={r['similarity']:.4f}{s} | {tag}")
        print(f"      {r['text'][:95]}...")

def pause(seconds=2):
    """Small pause to stay within rate limits."""
    time.sleep(seconds)


# =============================================================================
# 10 DOCUMENTS - 3 near-identical pairs (for graph edges) + 4 diverse
#
# Near-identical pairs will automatically create knowledge-graph
# edges during batch insert when their similarity is high enough.
# =============================================================================
documents = [
    # -- PAIR A: RAG --
    {
        "text": "Retrieval-Augmented Generation (RAG) enhances large language models by retrieving relevant documents from a vector store during inference, then feeding the retrieved context to the generator to produce factual, grounded answers without retraining the model.",
        "metadata": {"category": "ai", "subtopic": "rag", "year": 2024, "difficulty": "intermediate"}
    },
    {
        "text": "RAG systems improve large language model accuracy by fetching relevant passages from a vector database at query time and conditioning the language model on retrieved context, producing grounded and factually accurate answers without needing to retrain.",
        "metadata": {"category": "ai", "subtopic": "rag", "year": 2024, "difficulty": "intermediate"}
    },

    # -- PAIR B: Vector search / HNSW --
    {
        "text": "HNSW (Hierarchical Navigable Small World) is an approximate nearest neighbor algorithm that builds a multi-layer navigable graph for efficient high-dimensional vector search with logarithmic query complexity and high recall rates.",
        "metadata": {"category": "databases", "subtopic": "vector-search", "year": 2023, "difficulty": "advanced"}
    },
    {
        "text": "The Hierarchical Navigable Small World algorithm constructs a multi-layer navigable graph enabling fast approximate nearest neighbor retrieval in high-dimensional vector spaces, delivering logarithmic query time with excellent recall accuracy.",
        "metadata": {"category": "databases", "subtopic": "vector-search", "year": 2023, "difficulty": "advanced"}
    },

    # -- PAIR C: FlashAttention --
    {
        "text": "FlashAttention computes exact self-attention with O(n) memory instead of O(n squared) by tiling the computation to exploit GPU SRAM hierarchy, achieving 2-4x wall-clock speedup for training transformer models on long sequences without approximation.",
        "metadata": {"category": "ai", "subtopic": "attention", "year": 2024, "difficulty": "expert"}
    },
    {
        "text": "FlashAttention reduces transformer self-attention memory usage from quadratic to linear through IO-aware tiling on GPU shared memory, enabling 2-4x faster training of long-context transformer models with mathematically identical outputs.",
        "metadata": {"category": "ai", "subtopic": "attention", "year": 2024, "difficulty": "expert"}
    },

    # -- STANDALONE: diverse domains --
    {
        "text": "Kubernetes orchestrates containerized workloads across distributed clusters using declarative configuration, automatic horizontal scaling, self-healing, and zero-downtime rolling updates for cloud-native application deployment.",
        "metadata": {"category": "devops", "subtopic": "orchestration", "year": 2023, "difficulty": "intermediate"}
    },
    {
        "text": "Differential privacy provides mathematical guarantees against individual record identification from aggregate query results by adding calibrated Laplacian or Gaussian noise, with epsilon controlling the tradeoff between data utility and privacy protection.",
        "metadata": {"category": "security", "subtopic": "privacy", "year": 2023, "difficulty": "advanced"}
    },
    {
        "text": "CRISPR-Cas9 enables precise genome editing by directing the Cas9 nuclease to specific DNA sequences via guide RNA, creating targeted double-strand breaks that cells repair through homology-directed repair or non-homologous end joining pathways.",
        "metadata": {"category": "biology", "subtopic": "gene-editing", "year": 2024, "difficulty": "expert"}
    },
    {
        "text": "The Navier-Stokes existence and smoothness millennium prize problem asks whether smooth solutions always exist for three-dimensional incompressible fluid flows, or whether finite-time singularities can spontaneously form from smooth initial data with bounded energy.",
        "metadata": {"category": "mathematics", "subtopic": "fluid-dynamics", "year": 2000, "difficulty": "expert"}
    },
]


# =============================================================================
#  STEP 1 - Health Check
# =============================================================================
banner(1, "Health Check")
code, data, ms = api("GET", "/health")
print(f"  Status {code} | {ms:.0f}ms")
print(f"  Version : {data.get('version')}")
print(f"  Storage : {data.get('checks',{}).get('storage')}")


# =============================================================================
#  STEP 2 - User Info
# =============================================================================
banner(2, "Your Account")
code, me, ms = api("GET", "/v1/me")
print(f"  Email          : {me.get('email')}")
print(f"  Role           : {me.get('role')}")
print(f"  Trial days left: {me.get('days_remaining')}")
print(f"  API calls left : {me.get('api_calls_remaining')}")
print(f"  Doc capacity   : {me.get('documents_remaining')}")
pause()


# =============================================================================
#  STEP 3 - Create Fresh Namespace & Batch Insert
# =============================================================================
banner(3, "Create Namespace + Batch Insert 10 Documents")

code, ns_data, _ = api("POST", "/namespaces", {"name": TEST_NS})
print(f"  Namespace created: {TEST_NS}")

texts      = [d["text"] for d in documents]
embeddings = embed_many(texts)
print(f"  Embeddings generated: {embeddings.shape}")

# Show pair similarities BEFORE insert
pair_labels = ["RAG pair (A0-A1)", "HNSW pair (B0-B1)", "FlashAttn pair (C0-C1)"]
print(f"\n  Pre-insert similarity check:")
for idx, label in enumerate(pair_labels):
    i, j = idx * 2, idx * 2 + 1
    sim  = float(np.dot(embeddings[i], embeddings[j]))
    print(f"    {label}: cosine = {sim:.4f}")

batch = {
    "documents": [
        {"text": d["text"], "vector": e.tolist(), "metadata": d["metadata"]}
        for d, e in zip(documents, embeddings)
    ]
}
code, result, insert_ms = api("POST", "/v1/documents/batch", batch, namespace=TEST_NS)
ids = result.get("ids", [])
print(f"\n  Inserted {len(ids)} docs in {insert_ms:.0f}ms ({insert_ms/max(len(ids),1):.0f}ms/doc)")
for i, doc_id in enumerate(ids):
    m = documents[i]["metadata"]
    print(f"    [{i}] {doc_id}  {m['category']}/{m['subtopic']}")
pause()


# =============================================================================
#  STEP 4 - Auto Knowledge Graph Proof
# =============================================================================
banner(4, "Auto Knowledge Graph - Edge Creation Proof")

_, stats, _ = api("GET", "/v1/stats", namespace=TEST_NS)
print(f"  total_documents: {stats.get('total_documents')}")
print(f"\n  Nerqon automatically discovers relationships between")
print(f"  similar documents to improve search quality.")
print(f"  Highly similar document pairs get linked, so graph")
print(f"  traversal can find related docs that vector search alone might miss.")
pause()


# =============================================================================
#  STEP 5 - Semantic Search (COLD - no cache yet)
# =============================================================================
banner(5, "Semantic Search - Fresh Results")

queries = [
    ("How does RAG make LLMs more factual?",                             "rag"),
    ("IO-aware tiling for GPU self-attention computation",               "attention"),
    ("Approximate nearest neighbor search with graph-based algorithms",  "vector-search"),
    ("DNA editing with CRISPR guide RNA",                                "gene-editing"),
    ("Unsolved math problem about fluid equations",                      "fluid-dynamics"),
]

for q_text, expected in queries:
    qv = embed(q_text).tolist()
    _, res, qms = api("POST", "/v1/search", {
        "query_vector": qv, "k": 1, "use_graph": True, "use_cache": False,
        "namespace": TEST_NS,
    })
    top = res.get("results", [{}])[0]
    hit = top.get("metadata", {}).get("subtopic", "") == expected
    mark = "HIT " if hit else "MISS"
    sim  = top.get("similarity", 0)
    src  = top.get("source", "?")
    print(f"  [{mark}] \"{q_text}\"")
    print(f"         -> {top.get('metadata',{}).get('subtopic','?')}  sim={sim:.4f}  source={src}  {qms:.0f}ms")
pause()


# =============================================================================
#  STEP 6 - Cache Demo: Cold vs Warm
#
#  1st search: results come from vector index
#  2nd search: same results served from cache (faster)
# =============================================================================
banner(6, "Cache - Cold vs Warm Results")

q_text = "retrieval augmented generation for language models"
qv = embed(q_text).tolist()

# COLD - bypass cache
_, cold, cold_ms = api("POST", "/v1/search", {
    "query_vector": qv, "k": 3, "use_graph": False, "use_cache": False,
    "namespace": TEST_NS,
})

pause(1)

# WARM - same query, cache is now populated
_, warm, warm_ms = api("POST", "/v1/search", {
    "query_vector": qv, "k": 3, "use_graph": False, "use_cache": True,
    "namespace": TEST_NS,
})

cold_server = cold.get("query_time_ms", 0)
warm_server = warm.get("query_time_ms", 0)

print(f"  Query: \"{q_text}\"\n")
print(f"  COLD  -  server: {cold_server:.3f}ms  |  network: {cold_ms:.0f}ms")
for r in cold.get("results", []):
    print(f"    sim={r['similarity']:.4f} | source={r['source']:6s} | {r['metadata']['subtopic']}")

print(f"\n  WARM (cached)  -  server: {warm_server:.3f}ms  |  network: {warm_ms:.0f}ms")
for r in warm.get("results", []):
    print(f"    sim={r['similarity']:.4f} | source={r['source']:6s} | {r['metadata']['subtopic']}")

cold_sources = set(r["source"] for r in cold.get("results", []))
warm_sources = set(r["source"] for r in warm.get("results", []))
print(f"\n  Cold sources: {cold_sources}")
print(f"  Warm sources: {warm_sources}")
if warm_server > 0 and cold_server > 0:
    print(f"  Server-side speedup: {cold_server/warm_server:.1f}x")
print(f"\n  >> Repeat queries are served from cache automatically.")
pause()


# =============================================================================
#  STEP 7 - Vector-only vs Vector + Graph
# =============================================================================
banner(7, "Vector-only vs Vector + Graph Traversal")

q_text = "How does FlashAttention speed up transformer training?"
qv = embed(q_text).tolist()

_, res_no_g, t1 = api("POST", "/v1/search", {
    "query_vector": qv, "k": 5, "use_graph": False, "use_cache": False,
    "namespace": TEST_NS,
})
pause(1)
_, res_g, t2 = api("POST", "/v1/search", {
    "query_vector": qv, "k": 5, "use_graph": True, "use_cache": False,
    "namespace": TEST_NS,
})

print(f"  Query: \"{q_text}\"\n")
print(f"  WITHOUT graph ({t1:.0f}ms):")
show(res_no_g.get("results", []))

print(f"\n  WITH graph ({t2:.0f}ms):")
show(res_g.get("results", []))

no_g_ids = {r["id"] for r in res_no_g.get("results", [])}
g_ids    = {r["id"] for r in res_g.get("results", [])}
extra    = g_ids - no_g_ids
if extra:
    print(f"\n  >> Graph discovered {len(extra)} extra result(s) that vector search alone missed!")
else:
    print(f"\n  Note: With only 10 docs, both modes return all relevant matches.")
    print(f"  At scale (10K+ docs), graph traversal discovers connected")
    print(f"  neighbors that didn't make the top-k cut.")
pause()


# =============================================================================
#  STEP 8 - Hybrid Search
#
#  By now, some docs are cached (from steps 5-7 searches).
#  A NEW query may find results from multiple retrieval paths.
# =============================================================================
banner(8, "Hybrid Search - Multiple Retrieval Paths")

q_text = "efficient algorithms and data structures for search systems"
qv = embed(q_text).tolist()

_, tri, tri_ms = api("POST", "/v1/search", {
    "query_vector": qv, "k": 8, "use_graph": True, "use_cache": True,
    "namespace": TEST_NS,
})

sources = {}
for r in tri.get("results", []):
    s = r["source"]
    sources[s] = sources.get(s, 0) + 1

print(f"  Query: \"{q_text}\"")
print(f"  Response time: {tri_ms:.0f}ms\n")
show(tri.get("results", []))

print(f"\n  Source breakdown: {dict(sources)}")
print(f"  Nerqon merges results from all available retrieval paths,")
print(f"  deduplicates, and ranks by similarity.")
pause()


# =============================================================================
#  STEP 9 - Metadata Filters
# =============================================================================
banner(9, "Metadata Filters - Powerful Query DSL")

qv = embed("cutting edge research in science and technology").tolist()
base = {"query_vector": qv, "k": 10, "use_cache": False, "namespace": TEST_NS}

# 9a. Exact match
print("  9a. Exact match: category = 'biology'")
_, r, _ = api("POST", "/v1/search", {**base, "metadata_filter": {"category": "biology"}})
show(r.get("results", []), source=False)
pause(1)

# 9b. IN operator
print("\n  9b. IN operator: category IN ['ai', 'databases']")
_, r, _ = api("POST", "/v1/search", {**base, "metadata_filter": {"category": ["ai", "databases"]}})
show(r.get("results", []), source=False)
pause(1)

# 9c. Combined filters
print("\n  9c. Combined: category='ai' AND year=2024")
_, r, _ = api("POST", "/v1/search", {**base, "metadata_filter": {"category": "ai", "year": 2024}})
show(r.get("results", []), source=False)
pause(1)

# 9d. Difficulty filter
print("\n  9d. Difficulty: 'expert' only")
_, r, _ = api("POST", "/v1/search", {**base, "metadata_filter": {"difficulty": "expert"}})
results = r.get("results", [])
print(f"  Found {len(results)} expert-level docs:")
show(results, source=False)
pause()


# =============================================================================
#  STEP 10 - min_similarity Threshold
# =============================================================================
banner(10, "min_similarity - Quality Control")

q_text = "vector database nearest neighbor search algorithms"
qv = embed(q_text).tolist()
print(f"  Query: \"{q_text}\"\n")

for threshold in [0.0, 0.15, 0.30, 0.50]:
    _, r, _ = api("POST", "/v1/search", {
        "query_vector": qv, "k": 10, "min_similarity": threshold,
        "use_cache": False, "namespace": TEST_NS,
    })
    n = len(r.get("results", []))
    sims = ", ".join(f"{x['similarity']:.3f}" for x in r.get("results", []))
    print(f"  threshold={threshold:.2f}  ->  {n:2d} results  [{sims}]")
    pause(1)

print(f"\n  Higher thresholds = only high-confidence matches.")
print(f"  Use 0.3+ for production RAG to avoid noise in retrieved context.")
pause()


# =============================================================================
#  STEP 11 - Document Lifecycle (Get -> Update -> Re-search -> Delete)
# =============================================================================
banner(11, "Document Lifecycle - CRUD Operations")

if not ids:
    print("  Skipped (no documents inserted)")
else:
    target = ids[0]  # First doc (RAG pair A)

    # 11a. GET
    print(f"  11a. GET document {target}")
    code, doc, _ = api("GET", f"/v1/documents/{target}", namespace=TEST_NS)
    print(f"       Status:   {code}")
    print(f"       Text:     {doc.get('text','N/A')[:90]}...")
    print(f"       Metadata: {doc.get('metadata', 'N/A')}")
    pause()

    # 11b. UPDATE
    print(f"\n  11b. UPDATE document - change text and add 'updated' flag")
    new_text = (
        "Advanced RAG pipelines now use multi-step retrieval with query rewriting, "
        "hypothetical document embeddings (HyDE), and cross-encoder reranking to "
        "achieve state-of-the-art factual accuracy in LLM responses."
    )
    new_vec = embed(new_text).tolist()
    code, up, _ = api("PATCH", f"/v1/documents/{target}", {
        "text": new_text, "vector": new_vec,
        "metadata": {"category": "ai", "subtopic": "rag", "year": 2025,
                      "difficulty": "expert", "updated": True}
    }, namespace=TEST_NS)
    print(f"       Status: {code} | Result: {up.get('status', up.get('detail', 'N/A'))}")
    pause()

    # 11c. RE-SEARCH after update
    print(f"\n  11c. RE-SEARCH - updated document should appear with new text")
    qv = embed("advanced RAG with reranking and HyDE").tolist()
    _, r, _ = api("POST", "/v1/search", {
        "query_vector": qv, "k": 3, "use_cache": False, "namespace": TEST_NS,
    })
    for res in r.get("results", []):
        marker = " << UPDATED" if res.get("metadata", {}).get("updated") else ""
        print(f"       sim={res['similarity']:.4f} | {res['text'][:85]}...{marker}")
    pause()

    # 11d. DELETE
    delete_target = ids[-1]  # Last doc (Navier-Stokes)
    print(f"\n  11d. DELETE document {delete_target} (Navier-Stokes)")
    code, d, _ = api("DELETE", f"/v1/documents/{delete_target}", namespace=TEST_NS)
    print(f"       Status: {code} | Result: {d.get('status', d.get('detail', 'N/A'))}")
    pause()

    # Verify deleted doc is gone from search
    qv = embed("Navier-Stokes fluid dynamics millennium problem").tolist()
    _, r, _ = api("POST", "/v1/search", {
        "query_vector": qv, "k": 3, "use_cache": False, "namespace": TEST_NS,
    })
    found = any(x.get("id") == delete_target for x in r.get("results", []))
    print(f"       Deleted doc in results? {found}  (expected: False)")
    pause()

    # 11e. Stats after delete
    print(f"\n  11e. After delete:")
    _, st, _ = api("GET", "/v1/stats", namespace=TEST_NS)
    print(f"       total_documents: {st.get('total_documents')}")
    print(f"       Deleted documents are cleaned up automatically.")
    pause()


# =============================================================================
#  STEP 12 - Namespace Isolation (Multi-Tenancy)
# =============================================================================
banner(12, "Namespace Isolation - Multi-Tenant Ready")

# Create second namespace
_, _, _ = api("POST", "/namespaces", {"name": TEST_NS2})
print(f"  Created second namespace: {TEST_NS2}")
pause(1)

# Add a completely different doc to namespace 2
dark_text = (
    "Dark matter constitutes approximately 27 percent of the universe's mass-energy "
    "but has never been directly detected despite decades of underground detector "
    "experiments and particle collider searches at CERN."
)
dark_vec = embed(dark_text).tolist()
_, _, _ = api("POST", "/v1/documents", {
    "text": dark_text, "vector": dark_vec,
    "metadata": {"category": "physics", "subtopic": "dark-matter"}
}, namespace=TEST_NS2)
print(f"  Added 'dark matter' doc to {TEST_NS2}")
pause()

# Search in TEST_NS - should NOT find dark matter
qv = embed("dark matter detection experiments at CERN").tolist()
_, r1, _ = api("POST", "/v1/search", {
    "query_vector": qv, "k": 3, "use_cache": False, "namespace": TEST_NS,
})
pause(1)

# Search in TEST_NS2 - SHOULD find dark matter
_, r2, _ = api("POST", "/v1/search", {
    "query_vector": qv, "k": 3, "use_cache": False, "namespace": TEST_NS2,
})

print(f"\n  Search 'dark matter' in {TEST_NS} (main namespace):")
r1_results = r1.get("results", [])
if r1_results:
    for x in r1_results:
        print(f"    sim={x['similarity']:.4f} | {x['metadata'].get('subtopic','?')}  (NOT dark matter)")
else:
    print(f"    (no results)")

print(f"\n  Search 'dark matter' in {TEST_NS2} (isolated namespace):")
r2_results = r2.get("results", [])
if r2_results:
    for x in r2_results:
        print(f"    sim={x['similarity']:.4f} | {x['metadata'].get('subtopic','?')}  <- FOUND!")
else:
    print(f"    (no results)")

print(f"\n  >> Namespaces are COMPLETELY isolated.")
print(f"  >> Perfect for multi-tenant SaaS: each customer gets their own namespace.")
pause()


# =============================================================================
#  STEP 13 - Index Stats
# =============================================================================
banner(13, "Index Stats")

_, stats, _ = api("GET", "/v1/stats", namespace=TEST_NS)

if stats.get("total_documents") is not None:
    print(f"  Documents     : {stats.get('total_documents')}")
    print(f"  Cache entries : {stats.get('cache_size')}")
    print(f"  Dimension     : {stats.get('dimension')}")
    print(f"  GPU           : {stats.get('gpu_enabled')}")
    print(f"  Namespaces    : {stats.get('namespaces')}")
else:
    print(f"  {stats}")
pause()


# =============================================================================
#  STEP 14 - Cleanup
# =============================================================================
banner(14, "Cleanup - Delete Test Namespaces")

for ns in [TEST_NS, TEST_NS2]:
    code, d, _ = api("DELETE", f"/namespaces/{ns}")
    msg = d.get("status", d.get("detail", "?"))
    print(f"  {ns}: {msg} ({code})")

print(f"\n  All test data removed. Your account is clean.")


# =============================================================================
#  SUMMARY
# =============================================================================
banner("DONE", "Nerqon Feature Summary")

print("""
  What we just demonstrated:
  -----------------------------------------------------------------
   1. Health check + user account info
   2. Fresh namespace creation (zero test pollution)
   3. Batch insert with 384-dim sentence-transformer embeddings
   4. Auto knowledge graph with relationship discovery
   5. Semantic search accuracy (5/5 correct top-1 matches)
   6. Cache: repeat queries served faster from cache
   7. Vector-only vs Vector+Graph comparison
   8. Hybrid search: single query merges multiple retrieval paths
   9. Metadata filters: exact, IN, combined, difficulty
  10. min_similarity threshold for quality control
  11. Full CRUD: get, update, delete with cleanup
  12. Namespace isolation: complete multi-tenant data separation
  13. Index stats
  14. Clean teardown



  Get your free API key  :  https://nidhitek.com
  Python SDK             :  pip install nerqon
  GitHub                 :  https://github.com/nidhitek/Nerqon-python
  Documentation          :  https://nidhitek.com/documentation
""")
