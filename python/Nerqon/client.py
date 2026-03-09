"""
Nerqon SDK — Python Client
================================

Official Python client for the Nerqon Hybrid Vector + Graph Database API.

Usage:
    from Nerqon import Nerqon

    client = Nerqon(api_key="nidx_your_key")
    client.add("doc-1", text="Hello world", vector=[0.1, 0.2, ...])
    results = client.search(vector=[0.1, 0.2, ...], top_k=5)
"""

import time
from typing import Any, Dict, List, Optional, Union

import requests

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
    Stats,
)

__all__ = ["Nerqon"]

_DEFAULT_BASE_URL = "https://api.nidhitek.com"
_DEFAULT_TIMEOUT = 30
_MAX_RETRIES = 3


class Nerqon:
    """
    Official Python client for the Nerqon API.

    Args:
        api_key: Your Nerqon API key (starts with ``nidx_``).
        base_url: API base URL. Defaults to ``https://api.nidhitek.com``.
        timeout: Request timeout in seconds. Defaults to 30.
        max_retries: Max retries on transient failures. Defaults to 3.
        namespace: Default namespace for all operations.

    Example::

        from Nerqon import Nerqon

        client = Nerqon(api_key="nidx_your_key")

        # Add a document
        client.add("doc-1", text="AI is transforming search", vector=[0.1, 0.2, ...])

        # Search
        results = client.search(vector=[0.1, 0.2, ...], top_k=5)
        for r in results.results:
            print(f"{r.id}: {r.score:.4f} — {r.text[:80]}")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        namespace: str = "default",
    ):
        if not api_key:
            raise AuthenticationError("api_key is required. Get one at https://nidhitek.com/dashboard.html")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.namespace = namespace

        self._session = requests.Session()
        self._session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Nerqon-python/1.1.0",
        })

    # ──────────────────────────────────────────────
    # Internal HTTP helpers
    # ──────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an HTTP request with retries and error handling."""
        kwargs.setdefault("timeout", self.timeout)
        last_error = None

        for attempt in range(self.max_retries):
            try:
                resp = self._session.request(method, self._url(path), **kwargs)
                return self._handle_response(resp)
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = ConnectionError(
                    f"Cannot connect to Nerqon at {self.base_url}: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 8))
                continue
            except NerqonError:
                raise
            except Exception as e:
                raise NerqonError(f"Unexpected error: {e}")

        raise last_error

    def _handle_response(self, resp: requests.Response) -> dict:
        """Parse response and raise appropriate exceptions."""
        if resp.status_code == 204:
            return {}

        try:
            data = resp.json()
        except ValueError:
            data = {"detail": resp.text}

        if 200 <= resp.status_code < 300:
            return data

        detail = data.get("detail", data.get("message", str(data)))

        if resp.status_code in (401, 403):
            raise AuthenticationError(detail, status_code=resp.status_code, response=data)
        elif resp.status_code == 404:
            raise NotFoundError(detail, status_code=404, response=data)
        elif resp.status_code == 422:
            if "dimension" in str(detail).lower():
                raise DimensionMismatchError(detail, status_code=422, response=data)
            raise ValidationError(detail, status_code=422, response=data)
        elif resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            raise RateLimitError(
                detail, retry_after=retry_after, status_code=429, response=data
            )
        elif resp.status_code >= 500:
            raise ServerError(detail, status_code=resp.status_code, response=data)
        else:
            raise NerqonError(detail, status_code=resp.status_code, response=data)

    def _ns(self, namespace: Optional[str]) -> str:
        """Resolve namespace — use explicit value or fall back to default."""
        return namespace or self.namespace

    # ──────────────────────────────────────────────
    # Health & Stats
    # ──────────────────────────────────────────────

    def health(self) -> HealthStatus:
        """Check API health. Does not require authentication.

        Returns:
            HealthStatus with server status, version, and uptime.
        """
        data = self._request("GET", "/health")
        return HealthStatus.from_dict(data)

    def stats(self, namespace: str = None) -> Stats:
        """Get index statistics for a namespace.

        Args:
            namespace: Target namespace. Uses default if not specified.

        Returns:
            Stats object with document counts, dimension, cache hit rate, etc.
        """
        data = self._request("GET", "/v1/stats", params={"namespace": self._ns(namespace)})
        return Stats.from_dict(data)

    # ──────────────────────────────────────────────
    # Documents
    # ──────────────────────────────────────────────

    def add(
        self,
        id: str,
        vector: List[float],
        text: str = "",
        metadata: Dict[str, Any] = None,
        namespace: str = None,
    ) -> Document:
        """Add a single document.

        Args:
            id: Unique document identifier.
            vector: Embedding vector (list of floats).
            text: Document text content.
            metadata: Optional key-value metadata.
            namespace: Target namespace. Uses default if not specified.

        Returns:
            Document object with the stored document details.

        Raises:
            DimensionMismatchError: If vector dimension doesn't match namespace config.
            ValidationError: If parameters are invalid.
        """
        payload = {
            "vector": vector,
            "text": text,
            "metadata": metadata or {},
            "namespace": self._ns(namespace),
        }
        data = self._request("POST", "/v1/documents", json=payload)
        return Document.from_dict(data) if isinstance(data, dict) else Document(id=id)

    def add_batch(
        self,
        documents: List[Dict[str, Any]],
        namespace: str = None,
    ) -> dict:
        """Add multiple documents in a single request.

        Args:
            documents: List of document dicts, each with keys:
                ``id``, ``vector``, ``text`` (optional), ``metadata`` (optional).
            namespace: Target namespace for all documents.

        Returns:
            dict with batch operation results (e.g. ``{"added": 10}``).

        Example::

            docs = [
                {"id": "d1", "vector": [0.1, ...], "text": "First doc"},
                {"id": "d2", "vector": [0.2, ...], "text": "Second doc"},
            ]
            result = client.add_batch(docs)
        """
        payload = {
            "documents": documents,
            "namespace": self._ns(namespace),
        }
        return self._request("POST", "/v1/documents/batch", json=payload)

    def get(self, id: str, namespace: str = None) -> Document:
        """Retrieve a document by ID.

        Args:
            id: Document identifier.
            namespace: Target namespace.

        Returns:
            Document object.

        Raises:
            NotFoundError: If document doesn't exist.
        """
        data = self._request(
            "GET", f"/v1/documents/{id}",
            params={"namespace": self._ns(namespace)},
        )
        return Document.from_dict(data)

    def update(
        self,
        id: str,
        text: str = None,
        vector: List[float] = None,
        metadata: Dict[str, Any] = None,
        namespace: str = None,
    ) -> Document:
        """Update an existing document.

        Args:
            id: Document identifier.
            text: New text content (optional).
            vector: New embedding vector (optional).
            metadata: New metadata (optional).
            namespace: Target namespace.

        Returns:
            Updated Document object.
        """
        payload = {"namespace": self._ns(namespace)}
        if text is not None:
            payload["text"] = text
        if vector is not None:
            payload["vector"] = vector
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._request("PATCH", f"/v1/documents/{id}", json=payload)
        return Document.from_dict(data) if isinstance(data, dict) else Document(id=id)

    def delete(self, id: str, namespace: str = None) -> dict:
        """Delete a document by ID.

        Args:
            id: Document identifier.
            namespace: Target namespace.

        Returns:
            dict with deletion confirmation.

        Raises:
            NotFoundError: If document doesn't exist.
        """
        return self._request(
            "DELETE", f"/v1/documents/{id}",
            params={"namespace": self._ns(namespace)},
        )

    # ──────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────

    def search(
        self,
        vector: List[float] = None,
        text: str = None,
        top_k: int = 10,
        filters: Dict[str, Any] = None,
        namespace: str = None,
        mode: str = None,
        use_graph: bool = None,
        use_cache: bool = None,
    ) -> SearchResponse:
        """Search for similar documents.

        Supports vector search, text search, and hybrid search modes.

        Args:
            vector: Query embedding vector.
            text: Query text (if server-side embeddings are enabled).
            top_k: Number of results to return (default: 10).
            filters: Metadata filters using Query DSL.
            namespace: Target namespace.
            mode: Search mode — ``"vector"``, ``"hybrid"``, ``"graph"``.
            use_graph: Enable graph traversal for richer results.
            use_cache: Enable result caching.

        Returns:
            SearchResponse with results, scores, and query time.

        Example::

            # Vector search
            results = client.search(vector=[0.1, 0.2, ...], top_k=5)

            # With metadata filters
            results = client.search(
                vector=[0.1, ...],
                filters={"category": "science", "year": {"$gte": 2024}},
            )
        """
        payload = {
            "k": top_k,
            "namespace": self._ns(namespace),
        }
        if vector is not None:
            payload["query_vector"] = vector
        if text is not None:
            payload["query_text"] = text
        if filters:
            payload["metadata_filter"] = filters
        if use_graph is not None:
            payload["use_graph"] = use_graph
        if use_cache is not None:
            payload["use_cache"] = use_cache

        data = self._request("POST", "/v1/search", json=payload)
        return SearchResponse.from_dict(data)

    # ──────────────────────────────────────────────
    # Namespaces
    # ──────────────────────────────────────────────

    def list_namespaces(self) -> List[Namespace]:
        """List all namespaces.

        Returns:
            List of Namespace objects.
        """
        data = self._request("GET", "/v1/namespaces")
        namespaces = data if isinstance(data, list) else data.get("namespaces", [])
        return [Namespace.from_dict(ns) if isinstance(ns, dict) else Namespace(name=str(ns)) for ns in namespaces]

    def create_namespace(self, name: str, dimension: int = None) -> dict:
        """Create a new namespace.

        Args:
            name: Namespace name (alphanumeric + hyphens).
            dimension: Embedding dimension for this namespace (optional).

        Returns:
            dict with creation confirmation.
        """
        payload = {"name": name}
        if dimension:
            payload["dimension"] = dimension
        return self._request("POST", "/v1/namespaces", json=payload)

    def delete_namespace(self, name: str) -> dict:
        """Delete a namespace and all its data. This is irreversible.

        Args:
            name: Namespace to delete.

        Returns:
            dict with deletion confirmation.
        """
        return self._request("DELETE", f"/v1/namespaces/{name}")

    # ──────────────────────────────────────────────
    # User Info
    # ──────────────────────────────────────────────

    def me(self) -> dict:
        """Get current user information and usage stats.

        Returns:
            dict with user profile, plan, and usage data.
        """
        return self._request("GET", "/v1/me")

    # ──────────────────────────────────────────────
    # Context Manager
    # ──────────────────────────────────────────────

    def close(self):
        """Close the HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        return f"Nerqon(base_url={self.base_url!r}, namespace={self.namespace!r})"
