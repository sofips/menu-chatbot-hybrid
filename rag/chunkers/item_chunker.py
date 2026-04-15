from textwrap import dedent

from .base_chunker import BaseChunker


class ItemChunker(BaseChunker):
    def build(self):
        chunks = []
        metadatas = []
        ids = []

        for item in self.parser.items_by_name.values():
            text = self._build_text(item)
            item_id = item.get("id") or item["key"]

            chunks.append(text)
            metadatas.append(
                {
                    "type": "item",
                    "item_name": item["name"],
                    "categories": item["categories"],
                }
            )
            ids.append(f"item_{item_id}")

        return chunks, metadatas, ids

    def _build_text(self, item):
        name = item["name"]
        categories = ", ".join(item["categories"])

        prices = item["prices"]["values"]

        if prices:
            price_lines = "\n".join(
                [f"- {size.capitalize()}: ${value:.2f}" for size, value in prices.items()]
            )
            price_text = f"""
    The item "{name}" has the following prices:
    {price_lines}
    """
        else:
            price_text = "Price information is not available."

        return dedent(
            f"""
            {name} is a menu item in the category: {categories}.

            {price_text}
            """
        ).strip()