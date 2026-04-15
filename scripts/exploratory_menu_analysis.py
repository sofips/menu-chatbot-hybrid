"""Exploratory analysis for menu parsing readiness.

This script validates the parser output and highlights dataset quality issues
before using the menu as the chatbot's source of truth.
"""

from collections import Counter
from pathlib import Path
import json

from core.menu_parser import MenuParser

REPORT_WIDTH = 70


def print_section(title: str) -> None:
    print("\n" + "=" * REPORT_WIDTH)
    print(title)
    print("=" * REPORT_WIDTH)


def build_parser() -> MenuParser:
    return MenuParser(str('../data/MenuDataTest.json'))


def analyze_inventory(parser: MenuParser) -> None:
    print_section("1. DATA INVENTORY")
    print(f"Total raw item entries: {len(parser.items)}")
    print(f"Total unique items by id: {len(parser.items_by_id)}")
    print(f"Total indexed names: {len(parser.items_by_name)}")

    print("\nSample indexed item keys (first 10):")
    for idx, name in enumerate(list(parser.items_by_name.keys())[:10], start=1):
        print(f"  {idx}. {name}")

    print(f"\nName collisions: {len(parser.name_collisions)}")
    if parser.name_collisions:
        for key, variants in parser.name_collisions.items():
            variant_ids = [item["id"] for item in variants]
            print(f"  - {key}: ids={variant_ids}")


def analyze_price_coverage(parser: MenuParser):
    print_section("2. PRICE EDGE CASES")

    all_prices = []
    single_price_items = []
    multi_price_items = []
    zero_price_items = []

    for name, item in parser.items_by_name.items():
        values = item["prices"]["values"]
        all_prices.extend(values.values())
        if len(values) == 1:
            single_price_items.append(name)
        elif len(values) > 1:
            multi_price_items.append(name)
        if any(p <= 0 for p in values.values()):
            zero_price_items.append(name)

    if all_prices:
        print(f"Price range: ${min(all_prices):.2f} - ${max(all_prices):.2f}")
    else:
        print("Price range: no prices found")

    zero_prices = [price for price in all_prices if price <= 0]
    print(f"Zero/negative prices: {len(zero_prices)}")
    if zero_price_items:
        print("  WARNING: Items with zero/negative prices should be reviewed.")
        print("  They may need to be updated or removed from the menu.")
        print(f"  Items: {zero_price_items}")
    print(f"Single-price items: {len(single_price_items)}")
    print(f"Multi-price items: {len(multi_price_items)}")
    print(f"  Examples single: {single_price_items[:3]}")
    print(f"  Examples multi: {multi_price_items[:3]}")



    return multi_price_items


def analyze_normalization_and_lookup(parser: MenuParser) -> None:
    print_section("3. NORMALIZATION AND LOOKUP CHECKS")

    test_names = [
        "NUTTY  BOWL",
        "GO GREEN!",
        "go green",
        "Go Green",
        "  NUTTY BOWL  ",
    ]

    print("Name normalization checks:")
    for test_name in test_names:
        result = parser.get_item(test_name)
        status = "OK" if result["success"] else "FAIL"
        item_name = result["data"]["name"] if result["success"] else result["error"]["type"]
        print(f"  {status}: '{test_name}' -> {item_name}")

    size_variants = ["small", "Small", "SMALL", "sm", "SM", "S", "s"]
    print("\nSize alias checks for 'nutty bowl':")
    for size in size_variants:
        result = parser.get_price("nutty bowl", size)
        status = "OK" if result["success"] else "FAIL"
        price = result["data"]["price"] if result["success"] else result["error"]["type"]
        print(f"  {status}: size='{size}' -> {price}")


def analyze_nutrition_and_discounts(parser: MenuParser) -> None:
    print_section("4. NUTRITION AND DISCOUNTS")

    items_with_nutrition = []
    items_without_nutrition = []
    items_with_discounts = []

    for key, item in parser.items_by_name.items():
        nutrition = item["nutrition"]
        if nutrition.get("calories") or nutrition.get("dietaries"):
            items_with_nutrition.append(key)
        else:
            items_without_nutrition.append(key)

        discounts = item["raw"].get("applicableDiscounts", [])
        if discounts:
            items_with_discounts.append((key, len(discounts)))

    print(f"Items WITH nutrition data: {len(items_with_nutrition)}")
    print(f"Items WITHOUT nutrition data: {len(items_without_nutrition)}")
    print(f"  Examples without nutrition: {items_without_nutrition[:5]}")

    print(f"\nItems with applicable discounts: {len(items_with_discounts)}")
    for name, count in items_with_discounts[:5]:
        print(f"  - {name}: {count} discounts")


def analyze_categories(parser: MenuParser) -> None:
    print_section("5. CATEGORY STRUCTURE")

    print(f"Categories indexed: {len(parser.items_by_category)}")
    for category, item_keys in sorted(parser.items_by_category.items()):
        print(f"  - {category}: {len(item_keys)} items")


def analyze_error_quality(parser: MenuParser) -> None:
    print_section("6. ERROR QUALITY")

    test_cases = [
        {
            "method": "get_item",
            "name": "nonexistent_item",
            "size": None,
            "expect_success": False,
            "expect_error": "item_not_found",
        },
        {
            "method": "get_price",
            "name": "nutty bowl",
            "size": "xl",
            "expect_success": False,
            "expect_error": "invalid_size",
        },
        {
            "method": "get_price",
            "name": "GO GREEN",
            "size": "medium",
            "expect_success": False,
            "expect_error": "size_not_applicable",
        },
        {
            "method": "get_price",
            "name": "GO GREEN",
            "size": None,
            "expect_success": True,
            "expect_error": None,
        },
    ]

    for case in test_cases:
        method = case["method"]
        name = case["name"]
        size = case["size"]
        result = parser.get_price(name, size) if method == "get_price" else parser.get_item(name)

        matches_expectation = result["success"] == case["expect_success"]
        if not result["success"] and case["expect_error"]:
            matches_expectation = (
                matches_expectation
                and result.get("error", {}).get("type") == case["expect_error"]
            )

        status = "OK" if matches_expectation else "FAIL"
        print(f"  {status}: {method}(name='{name}', size={size})")

        if result["success"]:
            print(f"     Data={result['data']}")
        else:
            error = result.get("error", {})
            print(f"     Error type={error.get('type')}")
            print(f"     Error message={error.get('message')}")

        if not matches_expectation:
            print(f"     expected.success={case['expect_success']}")
            print(f"     actual.success={result['success']}")
            print(f"     expected.error={case['expect_error']}")
            print(f"     actual.error={result.get('error', {}).get('type')}")
                

def print_summary(parser: MenuParser, multi_price_items) -> None:
    print_section("SUMMARY")

    print(f"Indexed names: {len(parser.items_by_name)}")
    print(f"Unique item ids: {len(parser.items_by_id)}")
    print(f"Name collisions: {len(parser.name_collisions)}")
    print(f"Categories: {len(parser.items_by_category)}")
    print(f"Multi-price items: {len(multi_price_items)}")


def run_exploratory_analysis() -> None:
    parser = build_parser()
    analyze_inventory(parser)
    multi_price_items = analyze_price_coverage(parser)
    analyze_normalization_and_lookup(parser)
    analyze_nutrition_and_discounts(parser)
    analyze_categories(parser)
    analyze_error_quality(parser)
    print_summary(parser, multi_price_items)


