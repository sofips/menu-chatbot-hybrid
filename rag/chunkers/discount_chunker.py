from textwrap import dedent
from .base_chunker import BaseChunker


class DiscountChunker(BaseChunker):
    def build(self):
        chunks = []
        metadatas = []
        ids = []

        for discount_id, discount_def in self.parser.discounts_by_id.items():
            title = (discount_def.get("checkTitle") or "").strip()

            if not title:
                continue

            if any(x in title.lower() for x in ["open", "loyalty"]):
                continue

            amount = discount_def.get("amount")
            percentage = discount_def.get("percentage")
            coupon = discount_def.get("couponCode")

            if "bogo" in title.lower():
                detail = "Buy one get one offer"
            elif percentage:
                detail = f"{percentage}% off"
            elif amount:
                detail = f"${amount} off"
            else:
                detail = "Discount available"

            coupon_line = ""
            if coupon and coupon.lower() not in ["openamount"]:
                coupon_line = f"This discount REQUIRES a coupon code: {coupon}."

            text = dedent(
                f"""
                Discount: {title}

                {detail}.
                {coupon_line}
                """
            ).strip()

            chunks.append(text)
            metadatas.append({
                "type": "discount",
                "discount_id": discount_id,
            })
            ids.append(f"discount_{discount_id}")

        return chunks, metadatas, ids