# Search Quotes

Run a semantic search query against the JRE Quote Search API.

Usage: /search <query>

```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "$ARGUMENTS", "top_k": 5}'
```

Parse and display the results in a readable format.
