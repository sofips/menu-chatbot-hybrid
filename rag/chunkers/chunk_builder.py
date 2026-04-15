from rag.chunkers.item_chunker import ItemChunker
from rag.chunkers.category_chunker import CategoryChunker
from rag.chunkers.discount_chunker import DiscountChunker
from rag.chunkers.nutrition_chunker import NutritionChunker


class ChunkBuilder:
    def __init__(self, parser):
        self.chunkers = [
            ItemChunker(parser),
            CategoryChunker(parser),
            DiscountChunker(parser),
            NutritionChunker(parser),
        ]

    def build_all(self):
        all_chunks, all_meta, all_ids = [], [], []

        for chunker in self.chunkers:
            chunks, meta, ids = chunker.build()

            all_chunks.extend(chunks)
            all_meta.extend(meta)
            all_ids.extend(ids)

        return all_chunks, all_meta, all_ids