#!/usr/bin/env python3
"""Test chatbot against challenge questions."""

import sys
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.menu_parser import MenuParser
from core.query_executor import QueryExecutor
from rag.chunkers.chunk_builder import ChunkBuilder
from rag.embeddings import EmbeddingModel
from rag.vector_store import VectorStore
from rag.rag_engine import RAGEngine
from rag.llm_client import OllamaClient


class ChallengeTest:
    """Test suite for challenge questions."""
    
    def __init__(self):
        """Initialize chatbot."""
        print("Loading chatbot...")
        
        parser = MenuParser("data/MenuDataTest.json")
        chunk_builder = ChunkBuilder(parser)
        chunks, metadatas, ids = chunk_builder.build_all()
        
        embedding_model = EmbeddingModel()
        embeddings = embedding_model.embed_documents(chunks)
        
        vector_store = VectorStore()
        vector_store.add(chunks, embeddings, metadatas, ids)
        
        llm = OllamaClient()
        executor = QueryExecutor(parser)
        self.rag = RAGEngine(embedding_model, vector_store, llm, executor)
        self.history = []
        print("Chatbot ready!\n")
    
    def ask(self, question_num, question):
        """Ask a question and record response."""
        print(f"\nQ{question_num}: {question}")
        print("-" * 70)
        
        response = self.rag.run(question, history=self.history)
        self.history.append({"user": question, "assistant": response})
        
        print(f"A: {response}\n")
        
        return {
            "question_num": question_num,
            "question": question,
            "answer": response,
        }
    
    def run_challenge(self):
        """Run all challenge questions."""
        questions = [
            "What is the price of a small NUTTY BOWL?",
            "How many calories does the GO GREEN smoothie have?",
            "Which salads do you have?",
            "What discounts are available today?",
            "Which discounts include coupons?",
            "What items trigger a BOGO Any Smoothie discount?",
            "Is the price for Smoothie - ACAI ELIXIR the same in all channels?",
        ]
        
        results = []
        for i, question in enumerate(questions, 1):
            result = self.ask(i, question)
            results.append(result)
        
        # Save results to file
        self._save_results(results)
        return results
    
    def _save_results(self, results):
        """Save test results to file."""
        output_file = Path("tests/challenge_results.txt")
        
        with open(output_file, "w") as f:
            f.write("CHALLENGE QUESTIONS TEST RESULTS\n")
            f.write("=" * 70 + "\n\n")
            
            for result in results:
                f.write(f"Q{result['question_num']}: {result['question']}\n")
                f.write(f"{'-'*70}\n")
                f.write(f"A: {result['answer']}\n\n")
        
        print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    tester = ChallengeTest()
    results = tester.run_challenge()
    print(f"\nChallenge test completed: {len(results)} questions")