# Nerqon Go SDK

Official Go client for the [Nerqon](https://nidhitek.com) vector database API.

## Installation

```bash
go get github.com/nidhitek/nerqon-go
```

## Quick Start

```go
package main

import (
	"context"
	"fmt"
	"log"

	nerqon "github.com/nidhitek/nerqon-go"
)

func main() {
	client := nerqon.New("nidx_your_api_key")
	ctx := context.Background()

	// Add a document
	resp, err := client.Add(ctx, nerqon.AddRequest{
		Text:     "Machine learning transforms data into insights",
		Metadata: map[string]interface{}{"category": "ai"},
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Println("Added:", resp.NodeID)

	// Search
	results, err := client.Search(ctx, nerqon.SearchRequest{
		Text: "AI and data science",
		TopK: 5,
	})
	if err != nil {
		log.Fatal(err)
	}
	for _, r := range results.Results {
		fmt.Printf("Score: %.3f — %s\n", r.Score, r.Text)
	}
}
```

## Configuration

```go
client := nerqon.New("nidx_key",
	nerqon.WithBaseURL("https://your-instance.com"),
	nerqon.WithTimeout(60 * time.Second),
	nerqon.WithRetries(5),
	nerqon.WithNamespace("production"),
)
```

## License

MIT
