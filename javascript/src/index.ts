/**
 * Nerqon SDK — Official JavaScript/TypeScript Client
 *
 * Usage:
 *   import { Nerqon } from 'nerqon';
 *   const client = new Nerqon({ apiKey: 'nidx_your_key' });
 *   await client.add({ id: 'doc-1', text: 'Hello world' });
 *   const results = await client.search({ text: 'Hello' });
 *
 * @packageDocumentation
 */

// ── Types ──────────────────────────────────────────────

export interface NerqonConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  maxRetries?: number;
  namespace?: string;
}

export interface Document {
  id: string;
  text?: string;
  vector?: number[];
  metadata?: Record<string, unknown>;
  namespace?: string;
  version?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface SearchResult {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, unknown>;
  source: string;
}

export interface SearchResponse {
  results: SearchResult[];
  totalResults: number;
  queryTimeMs: number;
}

export interface SearchOptions {
  vector?: number[];
  text?: string;
  topK?: number;
  filters?: Record<string, unknown>;
  advancedFilters?: MetadataFilter[];
  namespace?: string;
  useGraph?: boolean;
  useCache?: boolean;
  minSimilarity?: number;
}

export interface MetadataFilter {
  field: string;
  operator: 'eq' | 'ne' | 'in' | 'nin' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains';
  value: unknown;
}

export interface Namespace {
  name: string;
  documentCount: number;
  dimension: number;
}

export interface Stats {
  totalDocuments: number;
  totalNamespaces: number;
  dimension: number;
  indexSizeBytes: number;
  cacheHitRate: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  uptimeSeconds: number;
}

export interface WebhookConfig {
  url: string;
  events: string[];
  description?: string;
}

export interface Webhook {
  webhookId: string;
  url: string;
  events: string[];
  secret?: string;
  description: string;
  isActive: boolean;
  createdAt: string;
  failureCount: number;
}

export interface WebhookDelivery {
  deliveryId: string;
  eventType: string;
  statusCode: number | null;
  attempt: number;
  deliveredAt: string;
  latencyMs: number;
  success: boolean;
}

// ── Errors ─────────────────────────────────────────────

export class NerqonError extends Error {
  statusCode?: number;
  code: string;
  constructor(message: string, statusCode?: number, code = 'NERQON_ERROR') {
    super(message);
    this.name = 'NerqonError';
    this.statusCode = statusCode;
    this.code = code;
  }
}

export class AuthenticationError extends NerqonError {
  constructor(message = 'Invalid API key') {
    super(message, 401, 'AUTH_ERROR');
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends NerqonError {
  retryAfter?: number;
  constructor(message = 'Rate limit exceeded', retryAfter?: number) {
    super(message, 429, 'RATE_LIMIT');
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class NotFoundError extends NerqonError {
  constructor(message = 'Resource not found') {
    super(message, 404, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

export class ValidationError extends NerqonError {
  constructor(message: string) {
    super(message, 422, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

// ── Client ─────────────────────────────────────────────

const DEFAULT_BASE_URL = 'https://api.nidhitek.com';
const DEFAULT_TIMEOUT = 30_000;
const MAX_RETRIES = 3;

export class Nerqon {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private readonly defaultNamespace: string;

  constructor(config: NerqonConfig) {
    if (!config.apiKey) throw new Error('apiKey is required');
    this.apiKey = config.apiKey;
    this.baseUrl = (config.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;
    this.maxRetries = config.maxRetries ?? MAX_RETRIES;
    this.defaultNamespace = config.namespace ?? 'default';
  }

  // ── Documents ──

  async add(doc: { id?: string; text: string; vector?: number[]; metadata?: Record<string, unknown> }, namespace?: string): Promise<{ nodeId: string; status: string }> {
    const ns = namespace ?? this.defaultNamespace;
    const body: Record<string, unknown> = { text: doc.text };
    if (doc.vector) body.vector = doc.vector;
    if (doc.metadata) body.metadata = doc.metadata;
    const resp = await this.request('POST', `/v1/documents?namespace=${encodeURIComponent(ns)}`, body);
    return { nodeId: resp.node_id, status: resp.status };
  }

  async addBatch(documents: Array<{ text: string; vector?: number[]; metadata?: Record<string, unknown> }>, namespace?: string): Promise<{ nodeIds: string[]; count: number }> {
    const ns = namespace ?? this.defaultNamespace;
    const resp = await this.request('POST', `/v1/documents/batch?namespace=${encodeURIComponent(ns)}`, { documents });
    return { nodeIds: resp.node_ids, count: resp.count };
  }

  async get(id: string, namespace?: string): Promise<Document> {
    const ns = namespace ?? this.defaultNamespace;
    const resp = await this.request('GET', `/documents/${encodeURIComponent(id)}?namespace=${encodeURIComponent(ns)}`);
    return this.mapDocument(resp);
  }

  async update(id: string, data: { text?: string; vector?: number[]; metadata?: Record<string, unknown> }, namespace?: string): Promise<{ nodeId: string; status: string }> {
    const ns = namespace ?? this.defaultNamespace;
    const resp = await this.request('PATCH', `/documents/${encodeURIComponent(id)}?namespace=${encodeURIComponent(ns)}`, data);
    return { nodeId: resp.node_id, status: resp.status };
  }

  async delete(id: string, namespace?: string): Promise<{ nodeId: string; status: string }> {
    const ns = namespace ?? this.defaultNamespace;
    const resp = await this.request('DELETE', `/documents/${encodeURIComponent(id)}?namespace=${encodeURIComponent(ns)}`);
    return { nodeId: resp.node_id, status: resp.status };
  }

  // ── Search ──

  async search(options: SearchOptions): Promise<SearchResponse> {
    const body: Record<string, unknown> = {};
    if (options.text) body.query_text = options.text;
    if (options.vector) body.query_vector = options.vector;
    body.k = options.topK ?? 10;
    if (options.filters) body.metadata_filter = options.filters;
    if (options.advancedFilters) body.filters = options.advancedFilters;
    if (options.useGraph !== undefined) body.use_graph = options.useGraph;
    if (options.useCache !== undefined) body.use_cache = options.useCache;
    if (options.minSimilarity !== undefined) body.min_similarity = options.minSimilarity;
    const ns = options.namespace ?? this.defaultNamespace;
    body.namespace = ns;

    const resp = await this.request('POST', '/v1/search', body);
    return {
      results: (resp.results ?? []).map((r: Record<string, unknown>) => ({
        id: r.node_id as string,
        text: r.text as string,
        score: r.similarity as number,
        metadata: (r.metadata ?? {}) as Record<string, unknown>,
        source: (r.source ?? 'faiss') as string,
      })),
      totalResults: resp.total_results ?? 0,
      queryTimeMs: resp.query_time_ms ?? 0,
    };
  }

  // ── Namespaces ──

  async listNamespaces(): Promise<Namespace[]> {
    const resp = await this.request('GET', '/namespaces');
    return (resp.namespaces ?? resp ?? []).map((n: Record<string, unknown>) => ({
      name: n.name as string,
      documentCount: (n.document_count ?? 0) as number,
      dimension: (n.dimension ?? 0) as number,
    }));
  }

  async createNamespace(name: string): Promise<void> {
    await this.request('POST', '/namespaces', { name });
  }

  async deleteNamespace(name: string): Promise<void> {
    await this.request('DELETE', `/namespaces/${encodeURIComponent(name)}`);
  }

  // ── Webhooks ──

  async createWebhook(config: WebhookConfig): Promise<Webhook & { secret: string }> {
    const resp = await this.request('POST', '/v1/webhooks', config);
    return this.mapWebhook(resp) as Webhook & { secret: string };
  }

  async listWebhooks(): Promise<Webhook[]> {
    const resp = await this.request('GET', '/v1/webhooks');
    return (resp.webhooks ?? []).map((w: Record<string, unknown>) => this.mapWebhook(w));
  }

  async getWebhook(webhookId: string): Promise<Webhook> {
    return this.mapWebhook(await this.request('GET', `/v1/webhooks/${encodeURIComponent(webhookId)}`));
  }

  async updateWebhook(webhookId: string, data: Partial<WebhookConfig> & { isActive?: boolean }): Promise<void> {
    await this.request('PATCH', `/v1/webhooks/${encodeURIComponent(webhookId)}`, data);
  }

  async deleteWebhook(webhookId: string): Promise<void> {
    await this.request('DELETE', `/v1/webhooks/${encodeURIComponent(webhookId)}`);
  }

  async getWebhookDeliveries(webhookId: string, limit = 50): Promise<WebhookDelivery[]> {
    const resp = await this.request('GET', `/v1/webhooks/${encodeURIComponent(webhookId)}/deliveries?limit=${limit}`);
    return (resp.deliveries ?? []).map((d: Record<string, unknown>) => ({
      deliveryId: d.delivery_id as string,
      eventType: d.event_type as string,
      statusCode: d.status_code as number | null,
      attempt: d.attempt as number,
      deliveredAt: d.delivered_at as string,
      latencyMs: d.latency_ms as number,
      success: d.success as boolean,
    }));
  }

  // ── Account ──

  async me(): Promise<Record<string, unknown>> {
    return this.request('GET', '/v1/me');
  }

  // ── Health & Stats ──

  async health(): Promise<HealthStatus> {
    const resp = await this.request('GET', '/health');
    return { status: resp.status, version: resp.version, uptimeSeconds: resp.uptime_seconds ?? 0 };
  }

  async stats(namespace?: string): Promise<Stats> {
    const ns = namespace ?? this.defaultNamespace;
    const resp = await this.request('GET', `/v1/stats?namespace=${encodeURIComponent(ns)}`);
    return {
      totalDocuments: resp.total_documents ?? 0,
      totalNamespaces: resp.total_namespaces ?? 0,
      dimension: resp.dimension ?? 0,
      indexSizeBytes: resp.index_size_bytes ?? 0,
      cacheHitRate: resp.cache_hit_rate ?? 0,
    };
  }

  // ── Internal ──

  private async request(method: string, path: string, body?: unknown): Promise<Record<string, unknown>> {
    const url = `${this.baseUrl}${path}`;
    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      if (attempt > 0) {
        await new Promise(r => setTimeout(r, Math.min(1000 * 2 ** (attempt - 1), 8000)));
      }

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeout);

      try {
        const fetchOptions: RequestInit = {
          method,
          headers: {
            'X-API-Key': this.apiKey,
            'Content-Type': 'application/json',
            'User-Agent': 'nerqon-js/1.0.0',
          },
          signal: controller.signal,
        };
        if (body && method !== 'GET') {
          fetchOptions.body = JSON.stringify(body);
        }

        const resp = await fetch(url, fetchOptions);
        clearTimeout(timer);

        if (resp.ok) {
          return (await resp.json()) as Record<string, unknown>;
        }

        // Handle error responses
        const errorBody = await resp.text();
        let detail = errorBody;
        try { detail = JSON.parse(errorBody).detail ?? errorBody; } catch { /* keep raw */ }

        if (resp.status === 401 || resp.status === 403) throw new AuthenticationError(detail);
        if (resp.status === 404) throw new NotFoundError(detail);
        if (resp.status === 422) throw new ValidationError(detail);
        if (resp.status === 429) {
          const retryAfter = parseInt(resp.headers.get('retry-after') ?? '60', 10);
          throw new RateLimitError(detail, retryAfter);
        }
        if (resp.status >= 500) {
          lastError = new NerqonError(detail, resp.status, 'SERVER_ERROR');
          continue; // Retry on 5xx
        }

        throw new NerqonError(detail, resp.status);

      } catch (err) {
        clearTimeout(timer);
        if (err instanceof NerqonError) {
          if (err.statusCode && err.statusCode < 500) throw err;
          lastError = err;
        } else {
          lastError = err as Error;
        }
      }
    }

    throw lastError ?? new NerqonError('Request failed after retries');
  }

  private mapDocument(d: Record<string, unknown>): Document {
    return {
      id: (d.node_id ?? d.id) as string,
      text: d.text as string,
      metadata: (d.metadata ?? {}) as Record<string, unknown>,
      namespace: (d.namespace ?? 'default') as string,
      version: d.version as number | undefined,
      createdAt: d.created_at as string | undefined,
      updatedAt: d.updated_at as string | undefined,
    };
  }

  private mapWebhook(w: Record<string, unknown>): Webhook {
    return {
      webhookId: w.webhook_id as string,
      url: w.url as string,
      events: w.events as string[],
      secret: w.secret as string | undefined,
      description: (w.description ?? '') as string,
      isActive: (w.is_active ?? true) as boolean,
      createdAt: w.created_at as string,
      failureCount: (w.failure_count ?? 0) as number,
    };
  }
}

export default Nerqon;
