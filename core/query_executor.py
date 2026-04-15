from difflib import get_close_matches


class QueryExecutor:
    def __init__(self, parser):
        self.parser = parser

    def execute(self, query: dict) -> str:
        intent = query.get("intent")

        if intent == "item_price":
            return self._handle_price(query)

        if intent == "item_nutrition":
            return self._handle_nutrition(query)

        if intent == "category_list":
            return self._handle_category(query)

        if intent == "discount_coupons":
            return self._handle_coupons(query)

        if intent == "discount_active":
            return self._handle_active_discounts(query)

        return self._fallback()
    
    def _normalize_item_name(self, name: str) -> str:
        """Match user input to actual item names using fuzzy matching."""
        if not name:
            return name
        
        name_norm = name.lower().strip()
        candidates = list(self.parser.items_by_name.keys())
        
        # Direct match first
        if name_norm in candidates:
            return name_norm
        
        # Fuzzy match (top 1 result with cutoff 0.6)
        matches = get_close_matches(name_norm, candidates, n=1, cutoff=0.6)
        if matches:
            return matches[0]
        
        return name_norm
    
    def _handle_price(self, query):
        name = query.get("item_name")
        size = query.get("size")

        # Normalize before lookup
        name = self._normalize_item_name(name)
        
        result = self.parser.get_price(name, size)

        if result["success"]:
            price = result['data']['price']
            size_str = result['data']['size']
            return f"${price:.2f} ({size_str})"

        error = result.get("error", {})
        error_type = error.get("type", "unknown")

        if error_type == "item_not_found":
            return None  # Fallback to RAG
        
        if error_type == "size_required":
            sizes = ", ".join(error.get("available_sizes", []))
            return f"Available sizes: {sizes}"

        if error_type == "invalid_size":
            # Still return available sizes, don't fallback to RAG
            sizes = error.get("available_sizes", [])
            if sizes:
                return f"'{size}' not available. Available sizes: {', '.join(sizes)}"
            return None

        return None
    
    def _handle_nutrition(self, query):
        name = query.get("item_name")
        name = self._normalize_item_name(name)

        result = self.parser.get_item(name)

        if not result["success"]:
            return None  # Fallback to RAG

        nutrition = result["data"].get("nutrition", {})
        calories = nutrition.get("calories")
        
        item = result["data"]
        category = item["categories"][0].lower()

        if category.endswith("s"):
            category = category[:-1]
               

        if calories:
            return  f"""
                The item "{item["name"]}" is a {category}.
                It has {nutrition.get("calories")} calories."""
        
        if not calories:
            return None  # Fallback to RAG for items without nutritional data
        
        return None

    
    def _handle_category(self, query):
        category = query.get("category")

        if not category:
            return "Please specify a category"

        category_key = category.lower().strip()

        items = self.parser.items_by_category.get(category_key)

        if not items:
            return f"No items found in category '{category}'"

        return f"{category.title()}:\n- " + "\n- ".join(items[:10])

    def _handle_coupons(self, query):
        """Return all available coupon codes."""
        coupons = self.parser.get_discounts_with_coupons()
        
        if not coupons:
            return "No coupon codes available."
        
        lines = ["Available coupon codes:"]
        for coupon in coupons:
            lines.append(f"- {coupon['code']}: {coupon['title']}")
        
        return "\n".join(lines)

    def _handle_active_discounts(self, query):
        """Return discounts that apply today."""
        discounts = self.parser.get_active_discounts()
        
        if not discounts:
            return "No active discounts available today."
        
        lines = ["Active discounts today:"]
        for discount in discounts:
            desc = discount['title']
            if discount.get('amount'):
                desc += f" (${discount['amount']} off)"
            elif discount.get('percentage'):
                desc += f" ({discount['percentage']}% off)"
            lines.append(f"- {desc}")
        
        return "\n".join(lines)
    
    def _fallback(self):
        return (
            "I didn't understand the request.\n"
            "You can ask about:\n"
            "- item prices\n"
            "- nutrition info\n"
            "- menu categories"
        )