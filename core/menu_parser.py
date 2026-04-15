import json
import re
from pathlib import Path
from typing import Optional


SIZE_ALIASES = {
    "s": "small",
    "sm": "small",
    "small": "small",
    "m": "medium",
    "md": "medium",
    "medium": "medium",
    "l": "large",
    "lg": "large",
    "large": "large",
}


def normalize_string(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s]", "", value)
    return value


def normalize_size(size: str) -> str:
    key = normalize_string(size)
    return SIZE_ALIASES.get(key, key)

class MenuParser:

    def __init__(self, json_path: str):
        self.source_path = self._resolve_source_path(json_path)
        with self.source_path.open(encoding="utf-8") as handle:
            menu_data = json.load(handle)

        raw_discounts = menu_data.get("value", {}).get("discounts", {})
        self.discounts_by_id = {}
        if isinstance(raw_discounts, dict):
            for key, discount in raw_discounts.items():
                if not isinstance(discount, dict):
                    continue
                discount_id = discount.get("id", key)
                self.discounts_by_id[str(discount_id)] = discount

        root_children = menu_data.get("value", {}).get("children", [])
        if not isinstance(root_children, list):
            raise ValueError("Invalid menu payload: 'value.children' must be a list")

        all_items_with_categories = []
        for root in root_children:
            all_items_with_categories.extend(self._extract_items(root))

        self.items = []
        self.items_by_id = {}
        self.items_by_name = {}
        self.items_by_category = {}
        self.categories = {}
        self.name_collisions = {}

        for item_data in all_items_with_categories:
            raw_item = item_data["item"]
            category = item_data["category"] or "uncategorized"
            category_key = normalize_string(category)

            item_id = raw_item.get("itemMasterId")
            if item_id in self.items_by_id:
                existing_item = self.items_by_id[item_id]
                if category_key not in existing_item["categories"]:
                    existing_item["categories"].append(category_key)
                    self._index_item_in_category(existing_item["key"], category_key)
                continue

            name = self._extract_item_name(raw_item)
            if not name:
                continue

            key = normalize_string(name)

            item = {
                "id": item_id,
                "key": key,
                "name": name,
                "prices": self._extract_prices(raw_item),
                "nutrition": raw_item.get("nutritionInfo", {}),
                "categories": [category_key],
                "raw": raw_item,
            }

            self.items.append(raw_item)
            self.items_by_id[item_id] = item
            self._index_item_in_category(key, category_key)

            if key in self.items_by_name:
                collisions = self.name_collisions.setdefault(
                    key, [self.items_by_name[key]]
                )
                collisions.append(item)
            else:
                self.items_by_name[key] = item

    def _resolve_source_path(self, json_path: str) -> Path:
        path = Path(json_path)
        if path.exists():
            return path

        fallback = Path(__file__).resolve().parent / json_path
        if fallback.exists():
            return fallback

        raise FileNotFoundError(json_path)

    def _extract_item_name(self, raw_item) -> Optional[str]:
        display_name = raw_item.get("displayAttribute", {}).get("itemTitle")
        if display_name and normalize_string(display_name):
            return display_name.strip()

        fallback_title = (raw_item.get("title") or "").strip()
        if not fallback_title:
            return None

        if " - " in fallback_title:
            fallback_title = fallback_title.split(" - ", 1)[1]

        return fallback_title.strip() or None

    def _index_item_in_category(self, item_key: str, category_key: str) -> None:
        self.items_by_category.setdefault(category_key, [])
        if item_key not in self.items_by_category[category_key]:
            self.items_by_category[category_key].append(item_key)

        self.categories.setdefault(category_key, {"title": category_key, "items": []})
        if item_key not in self.categories[category_key]["items"]:
            self.categories[category_key]["items"].append(item_key)

    def _extract_items(self, node, parent_category=None):
        """
        Extract items recursively, tracking parent category.
        
        Returns list of dicts: {"item": raw_item, "category": category_name}
        """
        items = []
        category_name = None

        if isinstance(node, dict):
            node_type = node.get("itemType")

            if node_type == 6:
                category_title = (
                    node.get("displayAttribute", {}).get("itemTitle")
                    or node.get("title")
                    or ""
                )
                category_name = normalize_string(category_title)

            if node_type == 1:
                items.append({
                    "item": node,
                    "category": parent_category or category_name or "uncategorized",
                })

            for child in node.get("children", []):
                items.extend(
                    self._extract_items(
                        child,
                        parent_category=category_name or parent_category,
                    )
                )

        return items

    def _extract_prices(self, item):
        prices = {}
        default_size = None

        for p in item.get("priceAttribute", {}).get("prices", []):
            portion = p.get("portionTypeId")
            price = p.get("price")
            if price is None:
                continue

            if portion:
                key = normalize_string(portion)
                prices[key] = price

                if p.get("default"):
                    default_size = key

            else:
                prices["default"] = price
                default_size = "default"

        return {"values": prices, "default": default_size}

    # ----------- API functions -----------

    def get_item(self, name: str):
        
        key = normalize_string(name)

        if key in self.name_collisions:
            options = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "categories": item["categories"],
                }
                for item in self.name_collisions[key]
            ]
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "ambiguous_item_name",
                    "message": f"Item '{name}' maps to multiple menu entries",
                    "options": options,
                },
            }

        item = self.items_by_name.get(key)

        if not item:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "item_not_found",
                    "message": f"Item '{name}' not found",
                },
            }

        return {"success": True, "data": item, "error": None}

    def get_price(self, name: str, size: Optional[str] = None):
        item_result = self.get_item(name)

        if not item_result["success"]:
            return item_result

        item = item_result["data"]
        prices = item["prices"]["values"]
        default = item["prices"]["default"]

        if not prices:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "price_not_available",
                    "message": f"No price data found for '{item['name']}'",
                },
            }

        if size:
            size_key = normalize_size(size)

            if size_key not in prices:
                if len(prices) == 1:
                    return {
                        "success": False,
                        "data": None,
                        "error": {
                            "type": "size_not_applicable",
                            "message": f"'{item['name']}' is a single-size item (no size variants)",
                            "available_price": next(iter(prices.values())),
                        },
                    }
                else:
                    return {
                        "success": False,
                        "data": None,
                        "error": {
                            "type": "invalid_size",
                            "message": f"Size '{size}' not available for '{item['name']}'",
                            "available_sizes": list(prices.keys()),
                        },
                    }

            return {
                "success": True,
                "data": {
                    "price": prices[size_key],
                    "size": size_key,
                },
                "error": None,
            }

        # No explicit size requested.

        if default and default in prices:
            return {
                "success": True,
                "data": {
                    "price": prices[default],
                    "size": default,
                },
                "error": None,
            }

        if len(prices) > 1:
            return {
                "success": False,
                "data": None,
                "error": {
                    "type": "size_required",
                    "available_sizes": list(prices.keys()),
                },
            }

        return {
            "success": True,
            "data": {
                "price": next(iter(prices.values())),
                "size": next(iter(prices.keys())),
            },
            "error": None,
        }