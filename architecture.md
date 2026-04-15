
---

# Architecture

## Overview

The system follows a simple hybrid approach:

- RAG for flexible, natural language queries
- A small deterministic layer for structured data (like prices or calories)

The idea is to use the LLM where it helps, and avoid it where it might introduce errors.

---

## Flow

User question
→ embed query
→ retrieve relevant chunks (ChromaDB)
→ (optional) structured lookup
→ build prompt
→ LLM generates answer

---

## Components

### MenuParser
Loads the raw JSON and organizes it into something easier to work with (items, discounts, categories, etc.)

---

### ChunkBuilder
Transforms structured data into text chunks.

Each chunk is designed to be self-contained (for example: including item name, category, and values in the same sentence).  
This makes retrieval more reliable.

---

### EmbeddingModel
Converts text into vectors so we can do similarity search.

---

### VectorStore (ChromaDB)
Stores embeddings and retrieves the most relevant chunks for a query.

---

### RAGEngine
This is the core of the system.

It:
- decides how to handle the query
- retrieves relevant chunks
- builds the prompt
- calls the LLM

---

### QueryExecutor
Handles simple structured queries directly (like price or calories).

This avoids relying on the model for things that should be exact.

---

### LLM (Ollama)
Generates the final answer using the retrieved context.

---

## Design decisions

### Why RAG?
Because the data is semi-structured and we want flexible queries.

### Why hybrid?
Because LLMs are great for language, but not always reliable for exact values.

So:
- RAG → flexibility
- executor → correctness

---

## Trade-offs

- Slightly more complex than a pure RAG system
- But much more reliable for factual questions

---

## Summary

The system keeps things simple:

- retrieve relevant information
- use the model to phrase it nicely
- fall back to deterministic logic when precision matters