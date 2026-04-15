from core.menu_parser import MenuParser
from core.query_executor import QueryExecutor
from rag.chunkers.chunk_builder import ChunkBuilder
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.rag_engine import RAGEngine
from rag.llm_client import OllamaClient


def build_index():
    parser = MenuParser("data/MenuDataTest.json")

    chunk_builder = ChunkBuilder(parser)
    chunks, metadatas, ids = chunk_builder.build_all()

    embedding_model = EmbeddingModel()
    embeddings = embedding_model.embed_documents(chunks)

    vector_store = VectorStore()
    vector_store.add(chunks, embeddings, metadatas, ids)

    return parser, embedding_model, vector_store


def main():
    parser, embedding_model, vector_store = build_index()

    llm = OllamaClient()
    executor = QueryExecutor(parser)
    rag = RAGEngine(embedding_model, vector_store, llm, executor)

    print("Menu chatbot ready! Type 'exit' to quit.\n")
    
    history = []

    while True:
        query = input("You: ").strip()

        if query.lower() in ["exit", "quit"]:
            break

        if not query:
            continue

        response = rag.run(query, history=history)

        print(f"\nBot: {response}\n")

        history.append({
            "user": query,
            "assistant": response
        })


if __name__ == "__main__":
    main()