package com.nidhitek.nerqon;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.lang.reflect.Type;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;

/**
 * Official Java client for the Nerqon vector database API.
 *
 * <pre>{@code
 * NerqonClient client = new NerqonClient.Builder("nidx_your_key").build();
 * AddResponse resp = client.add(new AddRequest("Machine learning is great"));
 * SearchResponse results = client.search(new SearchRequest.Builder().text("ML").build());
 * }</pre>
 */
public class NerqonClient implements AutoCloseable {

    private static final String DEFAULT_BASE_URL = "https://api.nidhitek.com";
    private static final Duration DEFAULT_TIMEOUT = Duration.ofSeconds(30);
    private static final int DEFAULT_RETRIES = 3;
    private static final String USER_AGENT = "nerqon-java/1.0.0";

    private final String apiKey;
    private final String baseUrl;
    private final String defaultNamespace;
    private final int maxRetries;
    private final HttpClient httpClient;
    private final Gson gson;

    private NerqonClient(Builder builder) {
        this.apiKey = Objects.requireNonNull(builder.apiKey, "apiKey is required");
        this.baseUrl = builder.baseUrl.replaceAll("/+$", "");
        this.defaultNamespace = builder.namespace;
        this.maxRetries = builder.maxRetries;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(builder.timeout)
                .build();
        this.gson = new GsonBuilder().create();
    }

    // ── Documents ──

    public AddResponse add(AddRequest request) throws NerqonException {
        return add(request, null);
    }

    public AddResponse add(AddRequest request, String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        String body = gson.toJson(request);
        JsonObject resp = doRequest("POST", "/v1/documents?namespace=" + encode(ns), body);
        return new AddResponse(resp.get("node_id").getAsString(), resp.get("status").getAsString());
    }

    public BatchAddResponse addBatch(List<AddRequest> documents) throws NerqonException {
        return addBatch(documents, null);
    }

    public BatchAddResponse addBatch(List<AddRequest> documents, String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        Map<String, Object> body = new HashMap<>();
        body.put("documents", documents);
        JsonObject resp = doRequest("POST", "/v1/documents/batch?namespace=" + encode(ns), gson.toJson(body));
        Type listType = new TypeToken<List<String>>() {}.getType();
        List<String> nodeIds = gson.fromJson(resp.get("node_ids"), listType);
        return new BatchAddResponse(nodeIds, resp.get("count").getAsInt());
    }

    public Document get(String id) throws NerqonException {
        return get(id, null);
    }

    public Document get(String id, String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        JsonObject resp = doRequest("GET", "/documents/" + encode(id) + "?namespace=" + encode(ns), null);
        return gson.fromJson(resp, Document.class);
    }

    public AddResponse update(String id, Map<String, Object> data) throws NerqonException {
        return update(id, data, null);
    }

    public AddResponse update(String id, Map<String, Object> data, String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        JsonObject resp = doRequest("PATCH", "/documents/" + encode(id) + "?namespace=" + encode(ns), gson.toJson(data));
        return new AddResponse(resp.get("node_id").getAsString(), resp.get("status").getAsString());
    }

    public AddResponse delete(String id) throws NerqonException {
        return delete(id, null);
    }

    public AddResponse delete(String id, String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        JsonObject resp = doRequest("DELETE", "/documents/" + encode(id) + "?namespace=" + encode(ns), null);
        return new AddResponse(resp.get("node_id").getAsString(), resp.get("status").getAsString());
    }

    // ── Search ──

    public SearchResponse search(SearchRequest request) throws NerqonException {
        if (request.getNamespace() == null) {
            request.setNamespace(defaultNamespace);
        }
        if (request.getTopK() == 0) {
            request.setTopK(10);
        }
        JsonObject resp = doRequest("POST", "/v1/search", gson.toJson(request));
        return gson.fromJson(resp, SearchResponse.class);
    }

    // ── Namespaces ──

    public List<NamespaceInfo> listNamespaces() throws NerqonException {
        JsonObject resp = doRequest("GET", "/namespaces", null);
        Type listType = new TypeToken<List<NamespaceInfo>>() {}.getType();
        return gson.fromJson(resp.get("namespaces"), listType);
    }

    public void createNamespace(String name) throws NerqonException {
        doRequest("POST", "/namespaces", gson.toJson(Map.of("name", name)));
    }

    public void deleteNamespace(String name) throws NerqonException {
        doRequest("DELETE", "/namespaces/" + encode(name), null);
    }

    // ── Webhooks ──

    public Webhook createWebhook(WebhookConfig config) throws NerqonException {
        JsonObject resp = doRequest("POST", "/v1/webhooks", gson.toJson(config));
        return gson.fromJson(resp, Webhook.class);
    }

    public List<Webhook> listWebhooks() throws NerqonException {
        JsonObject resp = doRequest("GET", "/v1/webhooks", null);
        Type listType = new TypeToken<List<Webhook>>() {}.getType();
        return gson.fromJson(resp.get("webhooks"), listType);
    }

    public void deleteWebhook(String webhookId) throws NerqonException {
        doRequest("DELETE", "/v1/webhooks/" + encode(webhookId), null);
    }

    // ── Health & Stats ──

    public HealthStatus health() throws NerqonException {
        JsonObject resp = doRequest("GET", "/health", null);
        return gson.fromJson(resp, HealthStatus.class);
    }

    public Stats stats() throws NerqonException {
        return stats(null);
    }

    public Stats stats(String namespace) throws NerqonException {
        String ns = namespace != null ? namespace : defaultNamespace;
        JsonObject resp = doRequest("GET", "/v1/stats?namespace=" + encode(ns), null);
        return gson.fromJson(resp, Stats.class);
    }

    public Map<String, Object> me() throws NerqonException {
        JsonObject resp = doRequest("GET", "/v1/me", null);
        Type mapType = new TypeToken<Map<String, Object>>() {}.getType();
        return gson.fromJson(resp, mapType);
    }

    @Override
    public void close() {
        // HttpClient in Java 11 doesn't require explicit closing
    }

    // ── Internal ──

    private JsonObject doRequest(String method, String path, String body) throws NerqonException {
        String url = baseUrl + path;
        NerqonException lastErr = null;

        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            if (attempt > 0) {
                try {
                    Thread.sleep(Math.min((long)(1000 * Math.pow(2, attempt - 1)), 8000));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new NerqonException("Interrupted", 0);
                }
            }

            try {
                HttpRequest.Builder reqBuilder = HttpRequest.newBuilder()
                        .uri(URI.create(url))
                        .header("X-API-Key", apiKey)
                        .header("Content-Type", "application/json")
                        .header("User-Agent", USER_AGENT)
                        .timeout(DEFAULT_TIMEOUT);

                switch (method) {
                    case "GET": reqBuilder.GET(); break;
                    case "POST": reqBuilder.POST(body != null ? HttpRequest.BodyPublishers.ofString(body) : HttpRequest.BodyPublishers.noBody()); break;
                    case "PATCH": reqBuilder.method("PATCH", body != null ? HttpRequest.BodyPublishers.ofString(body) : HttpRequest.BodyPublishers.noBody()); break;
                    case "DELETE": reqBuilder.DELETE(); break;
                }

                HttpResponse<String> response = httpClient.send(reqBuilder.build(), HttpResponse.BodyHandlers.ofString());
                int status = response.statusCode();

                if (status >= 200 && status < 300) {
                    String respBody = response.body();
                    if (respBody == null || respBody.isEmpty()) {
                        return new JsonObject();
                    }
                    return JsonParser.parseString(respBody).getAsJsonObject();
                }

                String detail = response.body();
                try {
                    JsonObject errObj = JsonParser.parseString(detail).getAsJsonObject();
                    if (errObj.has("detail")) detail = errObj.get("detail").getAsString();
                } catch (Exception ignored) {}

                if (status < 500) {
                    throw new NerqonException(detail, status);
                }
                lastErr = new NerqonException(detail, status);

            } catch (NerqonException e) {
                if (e.getStatusCode() != 0 && e.getStatusCode() < 500) throw e;
                lastErr = e;
            } catch (IOException | InterruptedException e) {
                lastErr = new NerqonException("Request failed: " + e.getMessage(), 0);
            }
        }
        throw lastErr != null ? lastErr : new NerqonException("Request failed after retries", 0);
    }

    private static String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    // ── Builder ──

    public static class Builder {
        private final String apiKey;
        private String baseUrl = DEFAULT_BASE_URL;
        private Duration timeout = DEFAULT_TIMEOUT;
        private int maxRetries = DEFAULT_RETRIES;
        private String namespace = "default";

        public Builder(String apiKey) { this.apiKey = apiKey; }
        public Builder baseUrl(String url) { this.baseUrl = url; return this; }
        public Builder timeout(Duration t) { this.timeout = t; return this; }
        public Builder maxRetries(int n) { this.maxRetries = n; return this; }
        public Builder namespace(String ns) { this.namespace = ns; return this; }
        public NerqonClient build() { return new NerqonClient(this); }
    }

    // ── Model Classes ──

    public static class AddRequest {
        private String text;
        private double[] vector;
        private Map<String, Object> metadata;

        public AddRequest(String text) { this.text = text; }
        public AddRequest(String text, Map<String, Object> metadata) { this.text = text; this.metadata = metadata; }
        public AddRequest(String text, double[] vector, Map<String, Object> metadata) {
            this.text = text; this.vector = vector; this.metadata = metadata;
        }
    }

    public static class AddResponse {
        private final String nodeId;
        private final String status;
        public AddResponse(String nodeId, String status) { this.nodeId = nodeId; this.status = status; }
        public String getNodeId() { return nodeId; }
        public String getStatus() { return status; }
    }

    public static class BatchAddResponse {
        private final List<String> nodeIds;
        private final int count;
        public BatchAddResponse(List<String> nodeIds, int count) { this.nodeIds = nodeIds; this.count = count; }
        public List<String> getNodeIds() { return nodeIds; }
        public int getCount() { return count; }
    }

    public static class Document {
        private String node_id;
        private String text;
        private Map<String, Object> metadata;
        private String namespace;
        private int version;
        private String created_at;
        private String updated_at;

        public String getId() { return node_id; }
        public String getText() { return text; }
        public Map<String, Object> getMetadata() { return metadata; }
        public String getNamespace() { return namespace; }
        public int getVersion() { return version; }
        public String getCreatedAt() { return created_at; }
        public String getUpdatedAt() { return updated_at; }
    }

    public static class SearchRequest {
        private String query_text;
        private double[] query_vector;
        private int k;
        private Map<String, Object> metadata_filter;
        private String namespace;
        private Boolean use_graph;
        private Boolean use_cache;
        private Double min_similarity;

        public String getNamespace() { return namespace; }
        public void setNamespace(String ns) { this.namespace = ns; }
        public int getTopK() { return k; }
        public void setTopK(int k) { this.k = k; }

        public static class Builder {
            private final SearchRequest req = new SearchRequest();
            public Builder text(String t) { req.query_text = t; return this; }
            public Builder vector(double[] v) { req.query_vector = v; return this; }
            public Builder topK(int k) { req.k = k; return this; }
            public Builder filters(Map<String, Object> f) { req.metadata_filter = f; return this; }
            public Builder namespace(String ns) { req.namespace = ns; return this; }
            public Builder useGraph(boolean b) { req.use_graph = b; return this; }
            public Builder useCache(boolean b) { req.use_cache = b; return this; }
            public Builder minSimilarity(double s) { req.min_similarity = s; return this; }
            public SearchRequest build() { return req; }
        }
    }

    public static class SearchResult {
        private String node_id;
        private String text;
        private double similarity;
        private Map<String, Object> metadata;
        private String source;

        public String getId() { return node_id; }
        public String getText() { return text; }
        public double getScore() { return similarity; }
        public Map<String, Object> getMetadata() { return metadata; }
        public String getSource() { return source; }
    }

    public static class SearchResponse {
        private List<SearchResult> results;
        private int total_results;
        private double query_time_ms;

        public List<SearchResult> getResults() { return results; }
        public int getTotalResults() { return total_results; }
        public double getQueryTimeMs() { return query_time_ms; }
    }

    public static class NamespaceInfo {
        private String name;
        private int document_count;
        private int dimension;

        public String getName() { return name; }
        public int getDocumentCount() { return document_count; }
        public int getDimension() { return dimension; }
    }

    public static class Stats {
        private int total_documents;
        private int total_namespaces;
        private int dimension;
        private long index_size_bytes;
        private double cache_hit_rate;

        public int getTotalDocuments() { return total_documents; }
        public int getTotalNamespaces() { return total_namespaces; }
    }

    public static class HealthStatus {
        private String status;
        private String version;
        private double uptime_seconds;

        public String getStatus() { return status; }
        public String getVersion() { return version; }
    }

    public static class WebhookConfig {
        private String url;
        private List<String> events;
        private String description;

        public WebhookConfig(String url, List<String> events) { this.url = url; this.events = events; }
        public WebhookConfig(String url, List<String> events, String desc) {
            this.url = url; this.events = events; this.description = desc;
        }
    }

    public static class Webhook {
        private String webhook_id;
        private String url;
        private List<String> events;
        private String secret;
        private String description;
        private boolean is_active;
        private String created_at;
        private int failure_count;

        public String getId() { return webhook_id; }
        public String getSecret() { return secret; }
        public boolean isActive() { return is_active; }
    }

    public static class NerqonException extends Exception {
        private final int statusCode;
        public NerqonException(String message, int statusCode) {
            super(message);
            this.statusCode = statusCode;
        }
        public int getStatusCode() { return statusCode; }
        public boolean isAuthError() { return statusCode == 401 || statusCode == 403; }
        public boolean isNotFound() { return statusCode == 404; }
        public boolean isRateLimit() { return statusCode == 429; }
    }
}
