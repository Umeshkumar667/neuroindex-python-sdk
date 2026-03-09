"""
Nerqon — Official Python SDK
==================================

Hybrid Vector + Graph Database for AI applications.

Quick Start::

    from Nerqon import Nerqon

    client = Nerqon(api_key="nidx_your_key")

    # Add a document
    client.add("doc-1", vector=[0.1, 0.2, ...], text="Hello world")

    # Search
    results = client.search(vector=[0.1, 0.2, ...], top_k=5)
    for r in results.results:
        print(f"{r.id}: {r.score:.4f}")

Full docs: https://nidhitek.com/documentation.html
"""

__version__ = "1.1.0"

from .client import Nerqon
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    DimensionMismatchError,
    NerqonError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from .models import (
    Document,
    HealthStatus,
    Namespace,
    SearchResponse,
    SearchResult,
    Stats,
)

__all__ = [
    # Client
    "Nerqon",
    # Exceptions
    "NerqonError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
    "DimensionMismatchError",
    "ServerError",
    "ConnectionError",
    # Models
    "Document",
    "SearchResult",
    "SearchResponse",
    "Namespace",
    "Stats",
    "HealthStatus",
]
