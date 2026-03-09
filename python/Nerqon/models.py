"""
Nerqon SDK — Response models
=================================

Lightweight dataclasses for structured API responses.
No external dependencies (uses stdlib dataclasses).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """A document stored in Nerqon."""
    id: str
    text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"
    version: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            metadata=data.get("metadata", {}),
            namespace=data.get("namespace", "default"),
            version=data.get("version"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class SearchResult:
    """A single search result with similarity score."""
    id: str
    text: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResult":
        return cls(
            id=data.get("id", ""),
            text=data.get("text", ""),
            score=data.get("score", data.get("similarity", 0.0)),
            metadata=data.get("metadata", {}),
            namespace=data.get("namespace", "default"),
        )


@dataclass
class SearchResponse:
    """Collection of search results."""
    results: List[SearchResult] = field(default_factory=list)
    total: int = 0
    query_time_ms: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "SearchResponse":
        results_data = data.get("results", [])
        return cls(
            results=[SearchResult.from_dict(r) for r in results_data],
            total=data.get("total", len(results_data)),
            query_time_ms=data.get("query_time_ms", 0.0),
        )


@dataclass
class Namespace:
    """A namespace (multi-tenant isolation unit)."""
    name: str
    document_count: int = 0
    dimension: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Namespace":
        return cls(
            name=data.get("name", ""),
            document_count=data.get("document_count", 0),
            dimension=data.get("dimension", 0),
        )


@dataclass
class Stats:
    """Index statistics for a namespace."""
    total_documents: int = 0
    total_namespaces: int = 0
    dimension: int = 0
    index_size_bytes: int = 0
    cache_hit_rate: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Stats":
        return cls(
            total_documents=data.get("total_documents", 0),
            total_namespaces=data.get("total_namespaces", 0),
            dimension=data.get("dimension", 0),
            index_size_bytes=data.get("index_size_bytes", 0),
            cache_hit_rate=data.get("cache_hit_rate", 0.0),
            raw=data,
        )


@dataclass
class HealthStatus:
    """API health check response."""
    status: str = "unknown"
    version: str = ""
    uptime: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "HealthStatus":
        return cls(
            status=data.get("status", "unknown"),
            version=data.get("version", ""),
            uptime=data.get("uptime", 0.0),
        )
