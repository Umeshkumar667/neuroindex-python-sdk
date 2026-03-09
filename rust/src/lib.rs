//! # Nerqon Rust SDK
//!
//! Official Rust client for the Nerqon vector database API.
//!
//! ```rust,no_run
//! use nerqon::NerqonClient;
//!
//! #[tokio::main]
//! async fn main() -> Result<(), nerqon::NerqonError> {
//!     let client = NerqonClient::new("nidx_your_key");
//!     let resp = client.add("Machine learning transforms data", None, None).await?;
//!     let results = client.search_text("AI and data science", 5, None).await?;
//!     Ok(())
//! }
//! ```

use reqwest::header::{HeaderMap, HeaderValue};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

const DEFAULT_BASE_URL: &str = "https://api.nidhitek.com";
const DEFAULT_TIMEOUT_SECS: u64 = 30;
const DEFAULT_RETRIES: u32 = 3;
const USER_AGENT: &str = "nerqon-rust/1.0.0";

// ── Error ──

#[derive(thiserror::Error, Debug)]
pub enum NerqonError {
    #[error("Authentication failed: {0}")]
    Auth(String),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Rate limited: {0}")]
    RateLimit(String),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Server error (HTTP {status}): {message}")]
    Server { status: u16, message: String },
    #[error("Request error: {0}")]
    Request(#[from] reqwest::Error),
    #[error("Serialization error: {0}")]
    Serde(#[from] serde_json::Error),
}

// ── Types ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub node_id: String,
    pub text: String,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub namespace: String,
    #[serde(default)]
    pub version: i32,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AddResponse {
    pub node_id: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BatchAddResponse {
    pub node_ids: Vec<String>,
    pub count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub node_id: String,
    pub text: String,
    pub similarity: f64,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResponse {
    pub results: Vec<SearchResult>,
    #[serde(default)]
    pub total_results: usize,
    #[serde(default)]
    pub query_time_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NamespaceInfo {
    pub name: String,
    #[serde(default)]
    pub document_count: usize,
    #[serde(default)]
    pub dimension: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub uptime_seconds: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stats {
    #[serde(default)]
    pub total_documents: usize,
    #[serde(default)]
    pub total_namespaces: usize,
    #[serde(default)]
    pub dimension: usize,
    #[serde(default)]
    pub index_size_bytes: u64,
    #[serde(default)]
    pub cache_hit_rate: f64,
}

#[derive(Debug, Clone, Serialize)]
struct AddDocRequest {
    text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    vector: Option<Vec<f64>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    metadata: Option<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Clone, Serialize)]
struct BatchRequest {
    documents: Vec<AddDocRequest>,
}

#[derive(Debug, Clone, Serialize)]
struct SearchBody {
    #[serde(skip_serializing_if = "Option::is_none")]
    query_text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    query_vector: Option<Vec<f64>>,
    k: usize,
    namespace: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    metadata_filter: Option<HashMap<String, serde_json::Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    use_graph: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    use_cache: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    min_similarity: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct NamespaceListResponse {
    namespaces: Vec<NamespaceInfo>,
}

// ── Client ──

pub struct NerqonClient {
    client: reqwest::Client,
    base_url: String,
    default_namespace: String,
    max_retries: u32,
}

impl NerqonClient {
    pub fn new(api_key: &str) -> Self {
        Self::with_config(api_key, DEFAULT_BASE_URL, "default", DEFAULT_RETRIES)
    }

    pub fn with_base_url(api_key: &str, base_url: &str) -> Self {
        Self::with_config(api_key, base_url, "default", DEFAULT_RETRIES)
    }

    pub fn with_config(api_key: &str, base_url: &str, namespace: &str, max_retries: u32) -> Self {
        let mut headers = HeaderMap::new();
        headers.insert("X-API-Key", HeaderValue::from_str(api_key).expect("Invalid API key"));
        headers.insert("User-Agent", HeaderValue::from_static(USER_AGENT));

        let client = reqwest::Client::builder()
            .default_headers(headers)
            .timeout(Duration::from_secs(DEFAULT_TIMEOUT_SECS))
            .build()
            .expect("Failed to build HTTP client");

        NerqonClient {
            client,
            base_url: base_url.trim_end_matches('/').to_string(),
            default_namespace: namespace.to_string(),
            max_retries,
        }
    }

    fn ns(&self, namespace: Option<&str>) -> String {
        namespace.unwrap_or(&self.default_namespace).to_string()
    }

    // ── Documents ──

    pub async fn add(
        &self,
        text: &str,
        metadata: Option<HashMap<String, serde_json::Value>>,
        namespace: Option<&str>,
    ) -> Result<AddResponse, NerqonError> {
        let ns = self.ns(namespace);
        let body = AddDocRequest { text: text.to_string(), vector: None, metadata };
        self.post(&format!("/v1/documents?namespace={}", urlencoding(&ns)), &body).await
    }

    pub async fn add_with_vector(
        &self,
        text: &str,
        vector: Vec<f64>,
        metadata: Option<HashMap<String, serde_json::Value>>,
        namespace: Option<&str>,
    ) -> Result<AddResponse, NerqonError> {
        let ns = self.ns(namespace);
        let body = AddDocRequest { text: text.to_string(), vector: Some(vector), metadata };
        self.post(&format!("/v1/documents?namespace={}", urlencoding(&ns)), &body).await
    }

    pub async fn add_batch(
        &self,
        documents: Vec<(&str, Option<HashMap<String, serde_json::Value>>)>,
        namespace: Option<&str>,
    ) -> Result<BatchAddResponse, NerqonError> {
        let ns = self.ns(namespace);
        let docs: Vec<AddDocRequest> = documents
            .into_iter()
            .map(|(text, meta)| AddDocRequest { text: text.to_string(), vector: None, metadata: meta })
            .collect();
        self.post(&format!("/v1/documents/batch?namespace={}", urlencoding(&ns)), &BatchRequest { documents: docs }).await
    }

    pub async fn get(&self, id: &str, namespace: Option<&str>) -> Result<Document, NerqonError> {
        let ns = self.ns(namespace);
        self.get_request(&format!("/documents/{}?namespace={}", urlencoding(id), urlencoding(&ns))).await
    }

    pub async fn delete(&self, id: &str, namespace: Option<&str>) -> Result<AddResponse, NerqonError> {
        let ns = self.ns(namespace);
        self.delete_request(&format!("/documents/{}?namespace={}", urlencoding(id), urlencoding(&ns))).await
    }

    // ── Search ──

    pub async fn search_text(
        &self,
        text: &str,
        top_k: usize,
        namespace: Option<&str>,
    ) -> Result<SearchResponse, NerqonError> {
        let ns = self.ns(namespace);
        let body = SearchBody {
            query_text: Some(text.to_string()),
            query_vector: None,
            k: top_k,
            namespace: ns,
            metadata_filter: None,
            use_graph: None,
            use_cache: None,
            min_similarity: None,
        };
        self.post("/v1/search", &body).await
    }

    pub async fn search_vector(
        &self,
        vector: Vec<f64>,
        top_k: usize,
        namespace: Option<&str>,
    ) -> Result<SearchResponse, NerqonError> {
        let ns = self.ns(namespace);
        let body = SearchBody {
            query_text: None,
            query_vector: Some(vector),
            k: top_k,
            namespace: ns,
            metadata_filter: None,
            use_graph: None,
            use_cache: None,
            min_similarity: None,
        };
        self.post("/v1/search", &body).await
    }

    // ── Namespaces ──

    pub async fn list_namespaces(&self) -> Result<Vec<NamespaceInfo>, NerqonError> {
        let resp: NamespaceListResponse = self.get_request("/namespaces").await?;
        Ok(resp.namespaces)
    }

    pub async fn create_namespace(&self, name: &str) -> Result<serde_json::Value, NerqonError> {
        self.post("/namespaces", &serde_json::json!({"name": name})).await
    }

    pub async fn delete_namespace(&self, name: &str) -> Result<serde_json::Value, NerqonError> {
        self.delete_request(&format!("/namespaces/{}", urlencoding(name))).await
    }

    // ── Health ──

    pub async fn health(&self) -> Result<HealthStatus, NerqonError> {
        self.get_request("/health").await
    }

    pub async fn stats(&self, namespace: Option<&str>) -> Result<Stats, NerqonError> {
        let ns = self.ns(namespace);
        self.get_request(&format!("/v1/stats?namespace={}", urlencoding(&ns))).await
    }

    // ── Internal HTTP ──

    async fn post<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R, NerqonError> {
        self.request_with_retry(reqwest::Method::POST, path, Some(body)).await
    }

    async fn get_request<R: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<R, NerqonError> {
        self.request_with_retry::<(), R>(reqwest::Method::GET, path, None).await
    }

    async fn delete_request<R: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<R, NerqonError> {
        self.request_with_retry::<(), R>(reqwest::Method::DELETE, path, None).await
    }

    async fn request_with_retry<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        method: reqwest::Method,
        path: &str,
        body: Option<&T>,
    ) -> Result<R, NerqonError> {
        let url = format!("{}{}", self.base_url, path);
        let mut last_err: Option<NerqonError> = None;

        for attempt in 0..=self.max_retries {
            if attempt > 0 {
                let backoff = std::cmp::min(1000 * 2u64.pow(attempt - 1), 8000);
                tokio::time::sleep(Duration::from_millis(backoff)).await;
            }

            let mut req = self.client.request(method.clone(), &url);
            if let Some(b) = body {
                req = req.json(b);
            }

            let resp = match req.send().await {
                Ok(r) => r,
                Err(e) => {
                    last_err = Some(NerqonError::Request(e));
                    continue;
                }
            };

            let status = resp.status().as_u16();
            if (200..300).contains(&status) {
                return Ok(resp.json().await?);
            }

            let detail = resp.text().await.unwrap_or_default();
            let message = serde_json::from_str::<serde_json::Value>(&detail)
                .ok()
                .and_then(|v| v.get("detail").and_then(|d| d.as_str()).map(String::from))
                .unwrap_or(detail);

            match status {
                401 | 403 => return Err(NerqonError::Auth(message)),
                404 => return Err(NerqonError::NotFound(message)),
                422 => return Err(NerqonError::Validation(message)),
                429 => return Err(NerqonError::RateLimit(message)),
                _ if status >= 500 => {
                    last_err = Some(NerqonError::Server { status, message });
                    continue;
                }
                _ => return Err(NerqonError::Server { status, message }),
            }
        }

        Err(last_err.unwrap_or(NerqonError::Server {
            status: 0,
            message: "Request failed after retries".to_string(),
        }))
    }
}

fn urlencoding(s: &str) -> String {
    // Percent-encode for URL path/query safety
    s.chars()
        .map(|c| match c {
            'A'..='Z' | 'a'..='z' | '0'..='9' | '-' | '_' | '.' | '~' => c.to_string(),
            _ => format!("%{:02X}", c as u32),
        })
        .collect()
}
