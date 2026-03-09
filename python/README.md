<p align="center">
  <img src="https://nidhitek.com/nidhitek_logo.png" alt="Nerqon" width="80" />
</p>

<h1 align="center">Nerqon Python SDK</h1>

<p align="center">
  <strong>The Hybrid Vector + Graph Database for AI Applications</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/Nerqon/"><img src="https://img.shields.io/pypi/v/Nerqon?color=6366f1&label=PyPI" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/Nerqon/"><img src="https://img.shields.io/pypi/pyversions/Nerqon?color=8b5cf6" alt="Python Versions"></a>
  <a href="https://github.com/nidhitek/Nerqon-python/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="https://nidhitek.com/documentation.html"><img src="https://img.shields.io/badge/Docs-nidhitek.com-blue" alt="Docs"></a>
</p>

<p align="center">
  <a href="https://nidhitek.com">Website</a> &bull;
  <a href="https://nidhitek.com/documentation.html">Documentation</a> &bull;
  <a href="https://nidhitek.com/dashboard.html">Get API Key</a> &bull;
  <a href="https://github.com/nidhitek/Nerqon-python/tree/main/examples">Examples</a>
</p>

---

## What is Nerqon?

Nerqon is a **hybrid vector + semantic graph database** that combines three search engines in one:

- **Vector Search** — Sub-millisecond similarity search with intelligent clustering
- **Graph Traversal** — Discover relationships between documents via semantic graphs
- **Hybrid Reranking** — Keyword-aware reranking that combines the best of both worlds

Unlike traditional vector databases, Nerqon **understands relationships** between your data.

## Installation

```bash
pip install Nerqon
```

## Quick Start

```python
from Nerqon import Nerqon

# Connect to Nerqon (get your free API key at nidhitek.com)
client = Nerqon(api_key="nidx_your_api_key")

# Add a document with its embedding vector
client.add(
    id="doc-1",
    text="AI is transforming healthcare with early diagnosis",
    vector=[0.12, -0.45, 0.78, ...],  # Your embedding vector
    metadata={"category": "ai", "year": 2025},
)

# Search for similar documents
results = client.search(vector=[0.12, -0.45, ...], top_k=5)
for r in results.results:
    print(f"[{r.score:.4f}] {r.id}: {r.text}")
```

## Features

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Vector + Graph + Keyword in a single query |
| **Namespaces** | Multi-tenant data isolation |
| **Metadata Filters** | Query DSL with `$gt`, `$lt`, `$in`, `$and`, `$or` |
| **Batch Operations** | Ingest thousands of documents in one call |
| **Document Versioning** | Track changes with automatic version history |
| **Knowledge Graph** | Define typed relationships between documents |
| **Smart Retrieval** | Confidence scoring with automatic thresholds |
| **Any Embedding** | Works with OpenAI, Cohere, HuggingFace, or any model |

## Usage Examples

### Add Documents

```python
# Single document
client.add(
    id="doc-1",
    text="Machine learning enables predictive analytics",
    vector=embedding,
    metadata={"source": "blog", "year": 2025},
)

# Batch add
docs = [
    {"id": "d1", "vector": emb1, "text": "First document", "metadata": {"type": "article"}},
    {"id": "d2", "vector": emb2, "text": "Second document", "metadata": {"type": "paper"}},
]
client.add_batch(docs)
```

### Search with Filters

```python
# Basic vector search
results = client.search(vector=query_embedding, top_k=10)

# With metadata filters
results = client.search(
    vector=query_embedding,
    top_k=5,
    filters={"category": "science", "year": {"$gte": 2024}},
)

# Hybrid search with graph traversal
results = client.search(
    vector=query_embedding,
    top_k=10,
    mode="hybrid",
    use_graph=True,
)
```

### Namespaces (Multi-tenancy)

```python
# Create a namespace
client.create_namespace("customer-a")

# Operations scoped to a namespace
client.add("doc-1", vector=emb, text="...", namespace="customer-a")
results = client.search(vector=query, namespace="customer-a")

# List all namespaces
namespaces = client.list_namespaces()
```

### Error Handling

```python
from Nerqon import (
    Nerqon,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    DimensionMismatchError,
)

try:
    results = client.search(vector=query, top_k=5)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except DimensionMismatchError:
    print("Vector dimension doesn't match namespace config")
except NotFoundError:
    print("Resource not found")
```

### Context Manager

```python
with Nerqon(api_key="nidx_...") as client:
    client.add("doc-1", vector=emb, text="Hello")
    results = client.search(vector=query)
# Session automatically closed
```

## Build a RAG Chatbot

```python
from Nerqon import Nerqon
import openai

client = Nerqon(api_key="nidx_your_key", namespace="knowledge-base")

# Index your knowledge base
for doc in documents:
    embedding = openai.embeddings.create(model="text-embedding-3-small", input=doc["text"])
    client.add(id=doc["id"], vector=embedding.data[0].embedding, text=doc["text"])

# RAG query
query = "How does authentication work?"
query_emb = openai.embeddings.create(model="text-embedding-3-small", input=query)

# Retrieve relevant context
results = client.search(vector=query_emb.data[0].embedding, top_k=3)
context = "\n".join([r.text for r in results.results])

# Generate answer
answer = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": f"Answer using this context:\n{context}"},
        {"role": "user", "content": query},
    ],
)
print(answer.choices[0].message.content)
```

## API Reference

### Client

```python
Nerqon(
    api_key: str,               # Required — your API key
    base_url: str = "https://api.nidhitek.com",
    timeout: int = 30,          # Request timeout in seconds
    max_retries: int = 3,       # Retries on transient failures
    namespace: str = "default", # Default namespace
)
```

### Methods

| Method | Description |
|--------|-------------|
| `client.health()` | Check API health status |
| `client.stats(namespace)` | Get index statistics |
| `client.add(id, vector, text, metadata, namespace)` | Add a document |
| `client.add_batch(documents, namespace)` | Batch add documents |
| `client.get(id, namespace)` | Get a document by ID |
| `client.update(id, text, vector, metadata, namespace)` | Update a document |
| `client.delete(id, namespace)` | Delete a document |
| `client.search(vector, text, top_k, filters, namespace, mode)` | Search documents |
| `client.list_namespaces()` | List all namespaces |
| `client.create_namespace(name, dimension)` | Create a namespace |
| `client.delete_namespace(name)` | Delete a namespace |
| `client.me()` | Get current user info |

## Self-Hosting

Nerqon can be self-hosted with Docker:

```bash
# Create a .env file with your configuration first
docker run -d \
  -p 8000:8000 \
  -v nerqon_data:/data \
  --env-file .env \
  nidhitek/Nerqon:latest
```

See the [self-hosting guide](https://nidhitek.com/documentation.html#self-hosting) for configuration details.

Then point the SDK to your server:

```python
client = Nerqon(api_key="your-key", base_url="http://localhost:8000")
```

## Free Trial

Get started with a **15-day free trial** — no credit card required:

- 10,000 documents
- 1,000 API calls/day
- All features included
- Any embedding dimension

**[Get Your Free API Key →](https://nidhitek.com/dashboard.html)**

## Benchmarks

Nerqon has been benchmarked across latency, throughput, retrieval quality, and disambiguation at 500 / 1K / 5K document scales.

| Metric | Result |
|--------|--------|
| **Search P50 Latency** | 2.5 - 5.1 ms |
| **Batch Insert** | 4,500+ docs/sec |
| **Search Throughput** | 57 - 124 QPS |
| **Hit@1 / MRR** | 0.70 - 0.90 / 0.79 - 0.93 |
| **Graph Boost** | +10% Hit@1 at 5K docs |

Full results: **[BENCHMARKS.md](BENCHMARKS.md)**

## License

This SDK is released under the [MIT License](LICENSE).

The Nerqon server engine is proprietary software by [NidhiTek](https://nidhitek.com).

---

<p align="center">
  Built with care by <a href="https://nidhitek.com"><strong>NidhiTek</strong></a>
</p>
