// Package nerqon provides the official Go client for the Nerqon vector database API.
//
// Usage:
//
//	client := nerqon.New("nidx_your_key")
//	resp, err := client.Add(ctx, nerqon.AddRequest{Text: "Hello world"})
//	results, err := client.Search(ctx, nerqon.SearchRequest{Text: "Hello"})
package nerqon

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"time"
)

const (
	DefaultBaseURL   = "https://api.nidhitek.com"
	DefaultTimeout   = 30 * time.Second
	DefaultRetries   = 3
	DefaultNamespace = "default"
	userAgent        = "nerqon-go/1.0.0"
)

// ── Configuration ──

type Config struct {
	APIKey    string
	BaseURL   string
	Timeout   time.Duration
	Retries   int
	Namespace string
	Client    *http.Client
}

type Option func(*Config)

func WithBaseURL(u string) Option    { return func(c *Config) { c.BaseURL = u } }
func WithTimeout(d time.Duration) Option { return func(c *Config) { c.Timeout = d } }
func WithRetries(n int) Option       { return func(c *Config) { c.Retries = n } }
func WithNamespace(ns string) Option { return func(c *Config) { c.Namespace = ns } }
func WithHTTPClient(h *http.Client) Option { return func(c *Config) { c.Client = h } }

// ── Types ──

type Document struct {
	ID        string                 `json:"node_id"`
	Text      string                 `json:"text"`
	Vector    []float64              `json:"vector,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
	Namespace string                 `json:"namespace,omitempty"`
	Version   int                    `json:"version,omitempty"`
	CreatedAt string                 `json:"created_at,omitempty"`
	UpdatedAt string                 `json:"updated_at,omitempty"`
}

type SearchResult struct {
	ID       string                 `json:"node_id"`
	Text     string                 `json:"text"`
	Score    float64                `json:"similarity"`
	Metadata map[string]interface{} `json:"metadata"`
	Source   string                 `json:"source"`
}

type SearchResponse struct {
	Results      []SearchResult `json:"results"`
	TotalResults int            `json:"total_results"`
	QueryTimeMs  float64        `json:"query_time_ms"`
}

type AddRequest struct {
	Text     string                 `json:"text"`
	Vector   []float64              `json:"vector,omitempty"`
	Metadata map[string]interface{} `json:"metadata,omitempty"`
}

type AddResponse struct {
	NodeID string `json:"node_id"`
	Status string `json:"status"`
}

type BatchAddRequest struct {
	Documents []AddRequest `json:"documents"`
}

type BatchAddResponse struct {
	NodeIDs []string `json:"node_ids"`
	Count   int      `json:"count"`
}

type SearchRequest struct {
	Text          string                 `json:"query_text,omitempty"`
	Vector        []float64              `json:"query_vector,omitempty"`
	TopK          int                    `json:"k,omitempty"`
	Filters       map[string]interface{} `json:"metadata_filter,omitempty"`
	Namespace     string                 `json:"namespace,omitempty"`
	UseGraph      *bool                  `json:"use_graph,omitempty"`
	UseCache      *bool                  `json:"use_cache,omitempty"`
	MinSimilarity *float64               `json:"min_similarity,omitempty"`
}

type NamespaceInfo struct {
	Name          string `json:"name"`
	DocumentCount int    `json:"document_count"`
	Dimension     int    `json:"dimension"`
}

type Stats struct {
	TotalDocuments  int     `json:"total_documents"`
	TotalNamespaces int     `json:"total_namespaces"`
	Dimension       int     `json:"dimension"`
	IndexSizeBytes  int64   `json:"index_size_bytes"`
	CacheHitRate    float64 `json:"cache_hit_rate"`
}

type HealthStatus struct {
	Status        string  `json:"status"`
	Version       string  `json:"version"`
	UptimeSeconds float64 `json:"uptime_seconds"`
}

type WebhookConfig struct {
	URL         string   `json:"url"`
	Events      []string `json:"events"`
	Description string   `json:"description,omitempty"`
}

type Webhook struct {
	WebhookID    string   `json:"webhook_id"`
	URL          string   `json:"url"`
	Events       []string `json:"events"`
	Secret       string   `json:"secret,omitempty"`
	Description  string   `json:"description"`
	IsActive     bool     `json:"is_active"`
	CreatedAt    string   `json:"created_at"`
	FailureCount int      `json:"failure_count"`
}

type WebhookDelivery struct {
	DeliveryID string `json:"delivery_id"`
	EventType  string `json:"event_type"`
	StatusCode *int   `json:"status_code"`
	Attempt    int    `json:"attempt"`
	DeliveredAt string `json:"delivered_at"`
	LatencyMs  int    `json:"latency_ms"`
	Success    bool   `json:"success"`
}

// ── Errors ──

type Error struct {
	Message    string
	StatusCode int
	Code       string
}

func (e *Error) Error() string {
	return fmt.Sprintf("nerqon: %s (status %d)", e.Message, e.StatusCode)
}

func IsAuthError(err error) bool {
	e, ok := err.(*Error)
	return ok && (e.StatusCode == 401 || e.StatusCode == 403)
}

func IsNotFound(err error) bool {
	e, ok := err.(*Error)
	return ok && e.StatusCode == 404
}

func IsRateLimit(err error) bool {
	e, ok := err.(*Error)
	return ok && e.StatusCode == 429
}

// ── Client ──

type Client struct {
	apiKey    string
	baseURL   string
	ns        string
	retries   int
	client    *http.Client
}

func New(apiKey string, opts ...Option) *Client {
	cfg := &Config{
		APIKey:    apiKey,
		BaseURL:   DefaultBaseURL,
		Timeout:   DefaultTimeout,
		Retries:   DefaultRetries,
		Namespace: DefaultNamespace,
	}
	for _, o := range opts {
		o(cfg)
	}
	httpClient := cfg.Client
	if httpClient == nil {
		httpClient = &http.Client{Timeout: cfg.Timeout}
	}
	return &Client{
		apiKey:  cfg.APIKey,
		baseURL: cfg.BaseURL,
		ns:      cfg.Namespace,
		retries: cfg.Retries,
		client:  httpClient,
	}
}

// ── Documents ──

func (c *Client) Add(ctx context.Context, req AddRequest, namespace ...string) (*AddResponse, error) {
	ns := c.pickNS(namespace)
	var resp AddResponse
	err := c.do(ctx, "POST", fmt.Sprintf("/v1/documents?namespace=%s", url.QueryEscape(ns)), req, &resp)
	return &resp, err
}

func (c *Client) AddBatch(ctx context.Context, req BatchAddRequest, namespace ...string) (*BatchAddResponse, error) {
	ns := c.pickNS(namespace)
	var resp BatchAddResponse
	err := c.do(ctx, "POST", fmt.Sprintf("/v1/documents/batch?namespace=%s", url.QueryEscape(ns)), req, &resp)
	return &resp, err
}

func (c *Client) Get(ctx context.Context, id string, namespace ...string) (*Document, error) {
	ns := c.pickNS(namespace)
	var resp Document
	err := c.do(ctx, "GET", fmt.Sprintf("/documents/%s?namespace=%s", url.PathEscape(id), url.QueryEscape(ns)), nil, &resp)
	return &resp, err
}

func (c *Client) Update(ctx context.Context, id string, data map[string]interface{}, namespace ...string) (*AddResponse, error) {
	ns := c.pickNS(namespace)
	var resp AddResponse
	err := c.do(ctx, "PATCH", fmt.Sprintf("/documents/%s?namespace=%s", url.PathEscape(id), url.QueryEscape(ns)), data, &resp)
	return &resp, err
}

func (c *Client) Delete(ctx context.Context, id string, namespace ...string) (*AddResponse, error) {
	ns := c.pickNS(namespace)
	var resp AddResponse
	err := c.do(ctx, "DELETE", fmt.Sprintf("/documents/%s?namespace=%s", url.PathEscape(id), url.QueryEscape(ns)), nil, &resp)
	return &resp, err
}

// ── Search ──

func (c *Client) Search(ctx context.Context, req SearchRequest) (*SearchResponse, error) {
	if req.TopK == 0 {
		req.TopK = 10
	}
	if req.Namespace == "" {
		req.Namespace = c.ns
	}
	var resp SearchResponse
	err := c.do(ctx, "POST", "/v1/search", req, &resp)
	return &resp, err
}

// ── Namespaces ──

func (c *Client) ListNamespaces(ctx context.Context) ([]NamespaceInfo, error) {
	var wrapper struct {
		Namespaces []NamespaceInfo `json:"namespaces"`
	}
	err := c.do(ctx, "GET", "/namespaces", nil, &wrapper)
	return wrapper.Namespaces, err
}

func (c *Client) CreateNamespace(ctx context.Context, name string) error {
	return c.do(ctx, "POST", "/namespaces", map[string]string{"name": name}, nil)
}

func (c *Client) DeleteNamespace(ctx context.Context, name string) error {
	return c.do(ctx, "DELETE", fmt.Sprintf("/namespaces/%s", url.PathEscape(name)), nil, nil)
}

// ── Webhooks ──

func (c *Client) CreateWebhook(ctx context.Context, cfg WebhookConfig) (*Webhook, error) {
	var resp Webhook
	err := c.do(ctx, "POST", "/v1/webhooks", cfg, &resp)
	return &resp, err
}

func (c *Client) ListWebhooks(ctx context.Context) ([]Webhook, error) {
	var wrapper struct {
		Webhooks []Webhook `json:"webhooks"`
	}
	err := c.do(ctx, "GET", "/v1/webhooks", nil, &wrapper)
	return wrapper.Webhooks, err
}

func (c *Client) UpdateWebhook(ctx context.Context, webhookID string, data map[string]interface{}) error {
	return c.do(ctx, "PATCH", fmt.Sprintf("/v1/webhooks/%s", url.PathEscape(webhookID)), data, nil)
}

func (c *Client) DeleteWebhook(ctx context.Context, webhookID string) error {
	return c.do(ctx, "DELETE", fmt.Sprintf("/v1/webhooks/%s", url.PathEscape(webhookID)), nil, nil)
}

func (c *Client) GetWebhookDeliveries(ctx context.Context, webhookID string, limit int) ([]WebhookDelivery, error) {
	if limit == 0 {
		limit = 50
	}
	var wrapper struct {
		Deliveries []WebhookDelivery `json:"deliveries"`
	}
	err := c.do(ctx, "GET", fmt.Sprintf("/v1/webhooks/%s/deliveries?limit=%d", url.PathEscape(webhookID), limit), nil, &wrapper)
	return wrapper.Deliveries, err
}

// ── Health & Stats ──

func (c *Client) Health(ctx context.Context) (*HealthStatus, error) {
	var resp HealthStatus
	err := c.do(ctx, "GET", "/health", nil, &resp)
	return &resp, err
}

func (c *Client) Stats(ctx context.Context, namespace ...string) (*Stats, error) {
	ns := c.pickNS(namespace)
	var resp Stats
	err := c.do(ctx, "GET", fmt.Sprintf("/v1/stats?namespace=%s", url.QueryEscape(ns)), nil, &resp)
	return &resp, err
}

func (c *Client) Me(ctx context.Context) (map[string]interface{}, error) {
	var resp map[string]interface{}
	err := c.do(ctx, "GET", "/v1/me", nil, &resp)
	return resp, err
}

// ── Internal ──

func (c *Client) pickNS(ns []string) string {
	if len(ns) > 0 && ns[0] != "" {
		return ns[0]
	}
	return c.ns
}

func (c *Client) do(ctx context.Context, method, path string, body interface{}, target interface{}) error {
	fullURL := c.baseURL + path
	var lastErr error

	for attempt := 0; attempt <= c.retries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(math.Min(float64(time.Second)*math.Pow(2, float64(attempt-1)), 8000)) * time.Millisecond
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(backoff):
			}
		}

		var bodyReader io.Reader
		if body != nil && method != "GET" {
			data, err := json.Marshal(body)
			if err != nil {
				return fmt.Errorf("nerqon: encode body: %w", err)
			}
			bodyReader = bytes.NewReader(data)
		}

		req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
		if err != nil {
			return fmt.Errorf("nerqon: create request: %w", err)
		}
		req.Header.Set("X-API-Key", c.apiKey)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("User-Agent", userAgent)

		resp, err := c.client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("nerqon: request failed: %w", err)
			continue
		}

		respBody, _ := io.ReadAll(resp.Body)
		resp.Body.Close()

		if resp.StatusCode >= 200 && resp.StatusCode < 300 {
			if target != nil && len(respBody) > 0 {
				if err := json.Unmarshal(respBody, target); err != nil {
					return fmt.Errorf("nerqon: decode response: %w", err)
				}
			}
			return nil
		}

		detail := string(respBody)
		var errObj struct{ Detail string `json:"detail"` }
		if json.Unmarshal(respBody, &errObj) == nil && errObj.Detail != "" {
			detail = errObj.Detail
		}

		apiErr := &Error{Message: detail, StatusCode: resp.StatusCode, Code: "API_ERROR"}

		if resp.StatusCode < 500 {
			return apiErr
		}
		lastErr = apiErr
	}
	if lastErr != nil {
		return lastErr
	}
	return &Error{Message: "request failed after retries", StatusCode: 0}
}
