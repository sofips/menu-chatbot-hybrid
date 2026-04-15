import unittest

from core.menu_parser import MenuParser
from rag.chunkers.category_chunker import CategoryChunker
from rag.chunkers.discount_chunker import DiscountChunker
from rag.chunkers.item_chunker import ItemChunker
from rag.chunkers.nutrition_chunker import NutritionChunker


class ChunkerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = MenuParser("data/MenuDataTest.json")
        cls.chunkers = {
            "item": ItemChunker(parser),
            "category": CategoryChunker(parser),
            "nutrition": NutritionChunker(parser),
            "discount": DiscountChunker(parser),
        }

    def test_triplet_lengths_match(self):
        for name, chunker in self.chunkers.items():
            with self.subTest(chunker=name):
                chunks, metadatas, ids = chunker.build()
                self.assertEqual(len(chunks), len(metadatas))
                self.assertEqual(len(chunks), len(ids))

    def test_ids_are_unique_per_chunker(self):
        for name, chunker in self.chunkers.items():
            with self.subTest(chunker=name):
                _, _, ids = chunker.build()
                self.assertEqual(len(ids), len(set(ids)))

    def test_text_format_starts_with_entity(self):
        for name, chunker in self.chunkers.items():
            with self.subTest(chunker=name):
                chunks, _, _ = chunker.build()
                self.assertTrue(chunks, "Chunker returned no chunks")
                self.assertTrue(chunks[0].startswith("Entity:"))

    def test_metadata_contract(self):
        expected_keys = {
            "item": {"type", "item_name", "categories"},
            "category": {"type", "category", "item_count"},
            "nutrition": {"type", "item_name", "categories"},
            "discount": {"type", "item_name", "categories", "discount_id"},
        }

        for name, chunker in self.chunkers.items():
            with self.subTest(chunker=name):
                _, metadatas, _ = chunker.build()
                self.assertTrue(metadatas, "Chunker returned no metadata")
                self.assertTrue(expected_keys[name].issubset(metadatas[0].keys()))


if __name__ == "__main__":
    unittest.main()
