# Menu Chatbot

This project is a simple chatbot that answers questions about a restaurant menu using a RAG (Retrieval-Augmented Generation) approach.

The idea is straightforward: take structured menu data, turn it into something searchable, and use a language model to answer questions naturally.

---

## What it does

You can ask things like:

- "What is the price of a small NUTTY BOWL?"
- "How many calories does the GO GREEN smoothie have?"
- "Which salads do you have?"
- "What discounts are available today?"
- "Which discounts include coupons?"
- "What items trigger a BOGO discount?"

The chatbot will retrieve the relevant information and respond in natural language.

---

## How it works (high level)

1. The menu JSON is parsed into structured data
2. That data is turned into small text chunks by four specialized chunkers:
   - **ItemChunker**: Individual menu items with prices
   - **CategoryChunker**: Category overviews
   - **NutritionChunker**: Nutritional info (calories, dietary notes)
   - **DiscountChunker**: Discounts and coupon codes
3. Each chunk is embedded and stored in a vector database (ChromaDB)
4. When you ask a question:
   - The system finds the most relevant chunks
   - Builds a prompt with that context
   - Uses an LLM to generate the answer

For some queries (like prices or calories), the system uses a simple deterministic lookup via QueryExecutor instead of relying only on the model. This helps avoid mistakes.

For semi-structured queries (like coupon codes or BOGO triggers), the system retrieves relevant chunks from the vector store and has the LLM synthesize the answer.

---

## Main components

- `MenuParser`: reads and structures the menu data
- `ChunkBuilder`: creates the text chunks used for retrieval
- `EmbeddingModel`: generates embeddings
- `VectorStore`: stores and retrieves embeddings (ChromaDB)
- `RAGEngine`: ties everything together
- `QueryExecutor`: handles structured queries (price, nutrition)
- `OllamaClient`: interface with the LLM

---

## How to run

Prerequisites:
- Python 3.8+
- Ollama running locally (for LLM inference)
- Menu data file at `data/MenuDataTest.json`

```bash
python3 main.py
```

To run challenge tests:

```bash
python3 tests/test_challenge.py