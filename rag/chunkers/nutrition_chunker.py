from textwrap import dedent

from .base_chunker import BaseChunker


class NutritionChunker(BaseChunker):
    def build(self):
        chunks = []
        metadatas = []
        ids = []

        for item in self.parser.items_by_name.values():
            nutrition = item["nutrition"]

            if not nutrition or not nutrition.get("calories"):
                continue

            item_id = item.get("id") or item["key"]
            dietaries = nutrition.get("dietaries") or []
            dietary_text = ", ".join([str(x) for x in dietaries]) if dietaries else "none"
            category = item["categories"][0].lower()

            if category.endswith("s"):
                category = category[:-1]


            text = dedent(
                f"""
                The item "{item["name"]}" is a {category}.
                It has {nutrition.get("calories")} calories.
                Category: {", ".join(item["categories"])}.
                Dietaries: {dietary_text}.
                """
            ).strip()

            chunks.append(text)
            metadatas.append(
                {
                    "type": "nutrition",
                    "item_name": item["name"],
                    "categories": item["categories"],
                }
            )
            ids.append(f"nutrition_{item_id}")

        return chunks, metadatas, ids