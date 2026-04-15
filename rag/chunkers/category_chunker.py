from textwrap import dedent

from .base_chunker import BaseChunker


class CategoryChunker(BaseChunker):
    def build(self):
        chunks = []
        metadatas = []
        ids = []

        for category, item_keys in self.parser.items_by_category.items():
            items = [
                self.parser.items_by_name[k]["name"]
                for k in item_keys
                if k in self.parser.items_by_name
            ]
            category_id = category.replace(" ", "_")

            text = dedent(
                    f"""
                    The category "{category}" includes the following items:

                    {", ".join(items)}
                    """
                ).strip()

            chunks.append(text)
            metadatas.append(
                {
                    "type": "category",
                    "category": category,
                    "item_count": len(items),
                }
            )
            ids.append(f"category_{category_id}")

        return chunks, metadatas, ids