#!/usr/bin/env python3
"""
Unit tests for specs_filter module

Run with: python3 test_specs_filter.py
Or with pytest: pytest test_specs_filter.py -v
"""

import sys
from specs_filter import (
    ProductSpecs,
    TargetSpecs,
    extract_specs_from_name,
    calculate_match_score,
    filter_and_rank,
    format_match_result
)


def test_extract_specs_russian():
    """Test extraction from Russian product names"""
    name = "16.2\" Ноутбук Apple MacBook Pro M1 Pro [RAM 32 ГБ, SSD 512 ГБ]"
    specs = extract_specs_from_name(name)

    assert specs.screen == "16", f"Expected screen='16', got '{specs.screen}'"
    assert specs.cpu == "M1 Pro", f"Expected cpu='M1 Pro', got '{specs.cpu}'"
    assert specs.ram == 32, f"Expected ram=32, got {specs.ram}"
    assert specs.ssd == 512, f"Expected ssd=512, got {specs.ssd}"
    print("[PASS] test_extract_specs_russian")


def test_extract_specs_english():
    """Test extraction from English product names"""
    name = "MacBook Pro 16\" M4 Max 64GB 1TB Z14V0008D"
    specs = extract_specs_from_name(name)

    assert specs.screen == "16", f"Expected screen='16', got '{specs.screen}'"
    assert specs.cpu == "M4 Max", f"Expected cpu='M4 Max', got '{specs.cpu}'"
    assert specs.ram == 64, f"Expected ram=64, got {specs.ram}"
    assert specs.ssd == 1000, f"Expected ssd=1000, got {specs.ssd}"
    assert specs.article == "Z14V0008D", f"Expected article='Z14V0008D', got '{specs.article}'"
    print("[PASS] test_extract_specs_english")


def test_extract_specs_with_article():
    """Test article number extraction"""
    name = "MacBook Pro Z14V0008D 16\" M1 Pro 32GB"
    specs = extract_specs_from_name(name)

    assert specs.article == "Z14V0008D", f"Expected article='Z14V0008D', got '{specs.article}'"
    print("[PASS] test_extract_specs_with_article")


def test_extract_specs_m5_chip():
    """Test extraction of M5 chip (single word CPU)"""
    name = "MacBook Pro 14\" M5 16GB 256GB"
    specs = extract_specs_from_name(name)

    assert specs.cpu == "M5", f"Expected cpu='M5', got '{specs.cpu}'"
    assert specs.ram == 16, f"Expected ram=16, got {specs.ram}"
    assert specs.ssd == 256, f"Expected ssd=256, got {specs.ssd}"
    print("[PASS] test_extract_specs_m5_chip")


def test_perfect_match():
    """Test perfect match score (100%)"""
    specs = ProductSpecs(screen="16", cpu="M1 Pro", ram=32, ssd=512)
    target = TargetSpecs(screen="16", cpu="M1 Pro", ram=32, ssd=512)
    score = calculate_match_score(specs, target)

    assert score == 100.0, f"Expected score=100.0, got {score}"
    print("[PASS] test_perfect_match")


def test_article_override():
    """Test that article match gives 100% even with wrong specs"""
    specs = ProductSpecs(article="Z14V0008D", cpu="M2", ram=16, ssd=256)  # Wrong specs
    target = TargetSpecs(article="Z14V0008D", cpu="M1 Pro", ram=32, ssd=512)
    score = calculate_match_score(specs, target)

    assert score == 100.0, f"Article should give 100%, got {score}"
    print("[PASS] test_article_override")


def test_partial_match_cpu_family():
    """Test partial match with same CPU family (M1 Pro vs M1 Max)"""
    specs = ProductSpecs(cpu="M1 Max", ram=32, ssd=512, screen="16")
    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    score = calculate_match_score(specs, target)

    # CPU: 20% (family match)
    # RAM: 30% (exact)
    # SSD: 20% (exact)
    # Screen: 10% (exact)
    # Total: 80%
    assert score == 80.0, f"Expected score=80.0, got {score}"
    print("[PASS] test_partial_match_cpu_family")


def test_partial_match_ram_tolerance():
    """Test partial match with RAM within tolerance"""
    specs = ProductSpecs(cpu="M1 Pro", ram=24, ssd=512, screen="16")  # 24GB instead of 32GB
    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    score = calculate_match_score(specs, target)

    # CPU: 40% (exact)
    # RAM: 15% (within 8GB)
    # SSD: 20% (exact)
    # Screen: 10% (exact)
    # Total: 85%
    assert score == 85.0, f"Expected score=85.0, got {score}"
    print("[PASS] test_partial_match_ram_tolerance")


def test_no_match_threshold():
    """Test that completely different specs score below threshold"""
    specs = ProductSpecs(cpu="M4", ram=16, ssd=256, screen="14")
    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    score = calculate_match_score(specs, target)

    assert score < 80.0, f"Different specs should score < 80%, got {score}"
    print("[PASS] test_no_match_threshold")


def test_filter_and_rank_basic():
    """Test basic filtering and ranking"""
    products = [
        {"name": "MacBook Pro 16\" M1 Pro 32GB 512GB", "price": 156000},
        {"name": "MacBook Pro 16\" M4 Max 64GB 1TB", "price": 280000},
        {"name": "MacBook Pro 14\" M4 16GB 256GB", "price": 90000},
    ]

    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    results = filter_and_rank(products, target, threshold=80, top_n=3)

    assert len(results) == 1, f"Expected 1 result, got {len(results)}"

    best_product, best_score = results[0]
    assert best_score == 100.0, f"Expected score=100.0, got {best_score}"
    assert best_product['price'] == 156000, f"Expected price=156000, got {best_product['price']}"
    print("[PASS] test_filter_and_rank_basic")


def test_filter_and_rank_top_n():
    """Test that top_n limits results"""
    products = [
        {"name": "MacBook Pro 16\" M1 Pro 32GB 512GB", "price": 156000},
        {"name": "MacBook Pro 16\" M1 Max 32GB 512GB", "price": 180000},
        {"name": "MacBook Pro 16\" M1 Pro 24GB 512GB", "price": 140000},
        {"name": "MacBook Pro 16\" M1 Pro 32GB 256GB", "price": 145000},
    ]

    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    results = filter_and_rank(products, target, threshold=70, top_n=2)

    assert len(results) == 2, f"Expected 2 results (top_n=2), got {len(results)}"

    # First result should be perfect match
    assert results[0][1] == 100.0, f"First result should be 100%, got {results[0][1]}"
    print("[PASS] test_filter_and_rank_top_n")


def test_filter_and_rank_sort_by_price():
    """Test that results are sorted by price when scores are equal"""
    products = [
        {"name": "MacBook Pro 16\" M1 Pro 32GB 512GB", "price": 180000},
        {"name": "MacBook Pro 16\" M1 Pro 32GB 512GB", "price": 156000},  # Cheaper
        {"name": "MacBook Pro 16\" M1 Pro 32GB 512GB", "price": 200000},
    ]

    target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
    results = filter_and_rank(products, target, threshold=80, top_n=3)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    # All have same score, should be sorted by price
    assert results[0][0]['price'] == 156000, "Cheapest should be first"
    assert results[1][0]['price'] == 180000, "Mid price should be second"
    assert results[2][0]['price'] == 200000, "Most expensive should be third"
    print("[PASS] test_filter_and_rank_sort_by_price")


def test_format_match_result():
    """Test match result formatting"""
    product = {
        "name": "MacBook Pro 16\" M1 Pro 32GB 512GB",
        "price": 156000,
        "specs": {"cpu": "M1 Pro", "ram": 32, "ssd": 512, "screen": "16"}
    }
    target = TargetSpecs()

    result = format_match_result(product, 100.0, target)

    assert "156000 RUB" in result, "Should contain price"
    assert "100%" in result, "Should contain score"
    assert "[+]" in result, "Should contain match indicators"
    print("[PASS] test_format_match_result")


def test_empty_name():
    """Test handling of empty product names"""
    specs = extract_specs_from_name("")

    assert specs.cpu is None, "CPU should be None for empty name"
    assert specs.ram is None, "RAM should be None for empty name"
    assert specs.ssd is None, "SSD should be None for empty name"
    print("[PASS] test_empty_name")


def test_malformed_name():
    """Test handling of malformed product names"""
    specs = extract_specs_from_name("Random text without specs")

    # Should not crash, should return empty specs
    assert isinstance(specs, ProductSpecs), "Should return ProductSpecs object"
    print("[PASS] test_malformed_name")


def run_all_tests():
    """Run all tests and report results"""
    tests = [
        test_extract_specs_russian,
        test_extract_specs_english,
        test_extract_specs_with_article,
        test_extract_specs_m5_chip,
        test_perfect_match,
        test_article_override,
        test_partial_match_cpu_family,
        test_partial_match_ram_tolerance,
        test_no_match_threshold,
        test_filter_and_rank_basic,
        test_filter_and_rank_top_n,
        test_filter_and_rank_sort_by_price,
        test_format_match_result,
        test_empty_name,
        test_malformed_name,
    ]

    failed = 0
    for test_func in tests:
        try:
            test_func()
        except AssertionError as e:
            print(f"[FAIL] {test_func.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test_func.__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Tests run: {len(tests)}")
    print(f"Passed: {len(tests) - failed}")
    print(f"Failed: {failed}")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
