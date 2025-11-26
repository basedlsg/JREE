# Ingest Data

Run the data ingestion pipeline to process transcripts and index them in Pinecone.

## Steps:
1. Process raw transcripts into chunks
2. Generate embeddings with Cohere
3. Upsert vectors to Pinecone

```bash
cd /home/user/JREE

# Step 1: Process transcripts into chunks
python scripts/process_chunks.py

# Step 2: Embed and index chunks
python scripts/embed_and_index.py
```

Monitor progress and report any errors.
