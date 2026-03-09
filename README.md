<p align="center">
  <img src="https://nidhitek.com/nidhitek_logo.png" alt="Nerqon" width="80" />
</p>

<h1 align="center">Nerqon SDK — Official Multi-Language Client Libraries</h1>

<p align="center">
  <strong>Open-source client libraries for the Nerqon Hybrid Vector + Graph Database</strong>
</p>

<p align="center">
  <a href="https://nidhitek.com">Website</a> &bull;
  <a href="https://nidhitek.com/documentation.html">Documentation</a> &bull;
  <a href="https://nidhitek.com/dashboard.html">Get API Key</a>
</p>

---

## Available SDKs

| Language | Directory | Install | Status |
|----------|-----------|---------|:------:|
| **Python** | [`python/`](python/) | `pip install nerqon` | ✅ v1.1.0 (PyPI) |
| **JavaScript / TypeScript** | [`javascript/`](javascript/) | `npm install nerqon` | ✅ v1.0.0 |
| **Go** | [`go/`](go/) | `go get github.com/nidhitek/nerqon-go` | ✅ v1.0.0 |
| **Java** | [`java/`](java/) | Maven: `com.nidhitek:nerqon:1.0.0` | ✅ v1.0.0 |
| **Rust** | [`rust/`](rust/) | `cargo add nerqon` | ✅ v1.0.0 |

## Quick Start

Every SDK follows the same pattern: create a client with your API key, then call methods.

### Python
```python
from nerqon import Nerqon

client = Nerqon(api_key="nidx_your_key")
client.add(id="doc-1", text="Machine learning transforms data", vector=[0.1, 0.2, ...])
results = client.search(text="AI and data science", top_k=5)
```

### JavaScript / TypeScript
```typescript
import { Nerqon } from 'nerqon';

const client = new Nerqon({ apiKey: 'nidx_your_key' });
await client.add({ text: 'Machine learning transforms data' });
const results = await client.search({ text: 'AI and data science', topK: 5 });
```

### Go
```go
client := nerqon.New("nidx_your_key")
client.Add(ctx, nerqon.AddRequest{Text: "Machine learning transforms data"})
results, _ := client.Search(ctx, nerqon.SearchRequest{Text: "AI and data science", TopK: 5})
```

### Java
```java
NerqonClient client = new NerqonClient.Builder("nidx_your_key").build();
client.add(new NerqonClient.AddRequest("Machine learning transforms data"));
var results = client.search(new NerqonClient.SearchRequest.Builder().text("AI and data science").topK(5).build());
```

### Rust
```rust
let client = NerqonClient::new("nidx_your_key");
client.add("Machine learning transforms data", None, None).await?;
let results = client.search_text("AI and data science", 5, None).await?;
```

## Features (All SDKs)

- Document CRUD (add, get, update, delete)
- Batch operations
- Upsert (create-or-update)
- Vector search & text search
- Namespace management (multi-tenancy)
- Webhook management
- Health checks & stats
- Automatic retry with exponential backoff
- Typed error handling
- Configurable base URL, timeout, retries

## License

MIT — See [LICENSE](python/LICENSE) for details.

© 2026 NidhiTek. All rights reserved.
