from core.menu_parser import MenuParser
from rag.chunkers.category_chunker import CategoryChunker
from rag.chunkers.discount_chunker import DiscountChunker
from rag.chunkers.item_chunker import ItemChunker
from rag.chunkers.nutrition_chunker import NutritionChunker

parser = MenuParser("data/MenuDataTest.json")

all_chunks = []
all_metadata = []
all_ids = []

for chunker in [
    ItemChunker(parser),
    CategoryChunker(parser),
    DiscountChunker(parser),
    NutritionChunker(parser),
]:
    chunks, metas, ids = chunker.build()

    all_chunks.extend(chunks)
    all_metadata.extend(metas)
    all_ids.extend(ids)

print("Chunks:")
for chunk in all_chunks:
    print(chunk)
    print("-" * 40)