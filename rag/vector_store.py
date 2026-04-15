import chromadb

class VectorStore:
    def __init__(self, collection_name="menu"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)

    def add(self, documents, embeddings, metadatas=None, ids=None):
        metadatas = metadatas or [{}] * len(documents)
    
        self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

    def query(self, query_embedding, n_results=5, where=None):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )