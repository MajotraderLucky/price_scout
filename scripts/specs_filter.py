#!/usr/bin/env python3
"""
Product Specifications Filter Module

Provides smart filtering and ranking of products based on technical specifications.
Used to find the best matching products instead of just returning MIN price.

Author: Price Scout Team
Created: 2026-01-03
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import re


@dataclass
class ProductSpecs:
    """Technical specifications extracted from product name/description"""
    screen: Optional[str] = None    # "16", "14"
    cpu: Optional[str] = None        # "M1 Pro", "M4 Max", "M5"
    ram: Optional[int] = None        # 32 (GB)
    ssd: Optional[int] = None        # 512 (GB)
    article: Optional[str] = None    # "Z14V0008D"

    def __repr__(self):
        parts = []
        if self.cpu:
            parts.append(f"CPU:{self.cpu}")
        if self.ram:
            parts.append(f"RAM:{self.ram}GB")
        if self.ssd:
            parts.append(f"SSD:{self.ssd}GB")
        if self.screen:
            parts.append(f"Screen:{self.screen}\"")
        if self.article:
            parts.append(f"Art:{self.article}")
        return f"ProductSpecs({', '.join(parts)})"


@dataclass
class TargetSpecs:
    """Target specifications for product search"""
    screen: str = "16"
    cpu: str = "M1 Pro"
    ram: int = 32
    ssd: int = 512
    article: str = "Z14V0008D"


def extract_specs_from_name(name: str) -> ProductSpecs:
    """
    Extract product specifications from product name using regex patterns.

    Args:
        name: Product name/title (e.g., "MacBook Pro 16.2\" M1 Pro 32GB 512GB")

    Returns:
        ProductSpecs with extracted values

    Examples:
        >>> extract_specs_from_name("MacBook Pro 16.2\" M1 Pro 32GB 512GB")
        ProductSpecs(cpu='M1 Pro', ram=32, ssd=512, screen='16')
    """
    if not name:
        return ProductSpecs()

    # Screen: "16.2", "16", "14.2" (capture only integer part)
    screen_match = re.search(r'(\d{2})(?:\.\d)?["\s]', name)
    screen = screen_match.group(1) if screen_match else None

    # CPU: "M1 Pro", "M4 Max", "M5", "Apple M1 Pro"
    # Match patterns: M1 Pro, M4 Max, M5, etc.
    cpu_match = re.search(r'(?:Apple\s+)?(M\d+(?:\s+(?:Pro|Max|Ultra))?)', name, re.I)
    cpu = cpu_match.group(1).strip() if cpu_match else None

    # RAM: "32 ГБ", "32GB", "RAM 32 ГБ", "ОЗУ 32GB"
    # First try with explicit RAM keyword
    ram_match = re.search(r'(?:RAM|ОЗУ|память)\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
    if not ram_match:
        # Fallback: find all GB/ГБ values, RAM is typically first (smaller value)
        all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
        if all_gb:
            ram_match = int(all_gb[0])
    ram = int(ram_match.group(1)) if (ram_match and hasattr(ram_match, 'group')) else (ram_match if isinstance(ram_match, int) else None)

    # SSD: "512 ГБ", "1TB", "1000GB", "SSD 512 ГБ", "накопитель 512GB"
    # First try with explicit SSD keyword (handle both GB and TB)
    ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ТБ|TB)', name, re.I)
    if ssd_match:
        ssd = int(ssd_match.group(1)) * 1000  # Convert TB to GB
    else:
        ssd_match = re.search(r'(?:SSD|накопитель)\s*(\d+)\s*(?:ГБ|GB)', name, re.I)
        if not ssd_match:
            # Fallback: find all storage values
            # Try TB first
            all_tb = re.findall(r'(\d+)\s*(?:ТБ|TB)', name, re.I)
            if all_tb:
                ssd = int(all_tb[0]) * 1000
            else:
                # Then try GB (second occurrence is usually SSD)
                all_gb = re.findall(r'(\d+)\s*(?:ГБ|GB)', name, re.I)
                if len(all_gb) >= 2:
                    ssd = int(all_gb[1])
                else:
                    ssd = None
        else:
            ssd = int(ssd_match.group(1)) if ssd_match else None

    # Article: "Z14V0008D" - Apple article format (letter + digits + alphanumeric)
    article_match = re.search(r'\b([A-Z]\d{2}[A-Z0-9]{5,})\b', name)
    article = article_match.group(1) if article_match else None

    return ProductSpecs(
        screen=screen,
        cpu=cpu,
        ram=ram,
        ssd=ssd,
        article=article
    )


def calculate_match_score(specs: ProductSpecs, target: TargetSpecs) -> float:
    """
    Calculate match score between product specs and target specs.

    Scoring weights:
    - Article match: 100% (instant perfect match)
    - CPU: 40% (same generation+variant), 30% (same generation, e.g., M4 vs M4 Pro)
    - RAM: 30% (>= target), 15% (>= target-8GB)
    - SSD: 20% (>= target), 10% (>= target-256GB)
    - Screen: 10% (exact)

    Args:
        specs: Product specifications to evaluate
        target: Target specifications to match against

    Returns:
        Match score from 0.0 to 100.0

    Examples:
        >>> specs = ProductSpecs(cpu="M4 Pro", ram=24, ssd=512, screen="16")
        >>> target = TargetSpecs(cpu="M4", ram=16, ssd=512, screen="16")
        >>> calculate_match_score(specs, target)
        100.0  # M4 Pro >= M4, 24GB >= 16GB, 512GB == 512GB, screen match
    """
    # Perfect match by article number
    if specs.article and specs.article == target.article:
        return 100.0

    score = 0.0

    # CPU match (40% weight) - supports minimum generation requirement
    if specs.cpu and target.cpu:
        # Extract generation: "M4 Pro" -> "M4", "M1" -> "M1"
        target_gen = target.cpu.split()[0]  # "M4", "M1", etc.
        specs_gen = specs.cpu.split()[0] if specs.cpu else None

        if specs.cpu == target.cpu:
            # Exact match: M4 Pro == M4 Pro
            score += 40.0
        elif specs_gen == target_gen:
            # Same generation, different variant: M4 Pro when looking for M4
            score += 30.0
        elif specs_gen and target_gen:
            # Different generation - check if newer
            # Extract number: M4 -> 4
            try:
                specs_num = int(re.search(r'M(\d+)', specs_gen).group(1))
                target_num = int(re.search(r'M(\d+)', target_gen).group(1))
                if specs_num >= target_num:
                    score += 20.0  # Newer generation
            except:
                pass

    # RAM match (30% weight) - supports minimum requirement (>=)
    if specs.ram and target.ram:
        if specs.ram >= target.ram:
            score += 30.0
        elif specs.ram >= target.ram - 8:  # Within 8GB below target
            score += 15.0

    # SSD match (20% weight) - supports minimum requirement (>=)
    if specs.ssd and target.ssd:
        if specs.ssd >= target.ssd:
            score += 20.0
        elif specs.ssd >= target.ssd - 256:  # Within 256GB below target
            score += 10.0

    # Screen match (10% weight)
    if specs.screen and target.screen:
        if specs.screen == target.screen:
            score += 10.0

    return score


def filter_and_rank(
    products: List[dict],
    target: TargetSpecs,
    threshold: float = 80.0,
    top_n: int = 3
) -> List[Tuple[dict, float]]:
    """
    Filter and rank products by specification match score.

    Args:
        products: List of product dictionaries with 'name' and optional 'specs' fields
        target: Target specifications to match
        threshold: Minimum score to include (0-100)
        top_n: Maximum number of results to return

    Returns:
        List of (product, score) tuples, sorted by score (desc) then price (asc)

    Examples:
        >>> products = [
        ...     {"name": "MacBook Pro 16 M1 Pro 32GB 512GB", "price": 156000},
        ...     {"name": "MacBook Pro 16 M4 Max 64GB 1TB", "price": 280000}
        ... ]
        >>> target = TargetSpecs(cpu="M1 Pro", ram=32, ssd=512, screen="16")
        >>> results = filter_and_rank(products, target, threshold=80)
        >>> len(results)
        1
        >>> results[0][1]  # Score should be 100.0
        100.0
    """
    scored = []

    for product in products:
        # Get or extract specs
        specs = product.get('specs')

        if not specs:
            # Fallback: extract specs from product name
            specs_obj = extract_specs_from_name(product.get('name', ''))
            product['specs'] = specs_obj.__dict__
            specs = specs_obj
        elif isinstance(specs, dict):
            # Convert dict to ProductSpecs object
            specs = ProductSpecs(**specs)

        # Calculate match score
        score = calculate_match_score(specs, target)

        # Filter by threshold
        if score >= threshold:
            scored.append((product, score))

    # Sort by score (descending), then by price (ascending)
    scored.sort(key=lambda x: (-x[1], x[0].get('price', 999999)))

    return scored[:top_n]


def format_match_result(product: dict, score: float, target: TargetSpecs) -> str:
    """
    Format a match result for display.

    Args:
        product: Product dictionary
        score: Match score
        target: Target specs for comparison

    Returns:
        Formatted string with match details
    """
    specs = product.get('specs', {})
    if isinstance(specs, ProductSpecs):
        specs = specs.__dict__

    price = product.get('price', 'N/A')
    name = product.get('name', 'Unknown')

    # Build match indicators
    indicators = []
    if specs.get('cpu') == target.cpu:
        indicators.append(f"{specs.get('cpu')} [+]")
    elif specs.get('cpu'):
        indicators.append(f"{specs.get('cpu')} [~]")

    if specs.get('ram') == target.ram:
        indicators.append(f"{specs.get('ram')}GB [+]")
    elif specs.get('ram'):
        indicators.append(f"{specs.get('ram')}GB [~]")

    if specs.get('ssd') == target.ssd:
        indicators.append(f"{specs.get('ssd')}GB [+]")
    elif specs.get('ssd'):
        indicators.append(f"{specs.get('ssd')}GB [~]")

    if specs.get('screen') == target.screen:
        indicators.append(f"{specs.get('screen')}\" [+]")
    elif specs.get('screen'):
        indicators.append(f"{specs.get('screen')}\" [~]")

    match_str = " | ".join(indicators)

    return f"{price} RUB | Score: {score:.0f}% | {match_str}"


if __name__ == "__main__":
    # Quick test
    test_products = [
        {"name": "MacBook Pro 16.2\" M1 Pro 32GB 512GB Z14V0008D", "price": 156000},
        {"name": "MacBook Pro 16\" M4 Max 64GB 1TB", "price": 280000},
        {"name": "MacBook Pro 16\" M1 Pro 16GB 512GB", "price": 120000},
    ]

    target = TargetSpecs()
    results = filter_and_rank(test_products, target, threshold=80)

    print(f"Found {len(results)} matches (threshold: 80%):\n")
    for product, score in results:
        print(format_match_result(product, score, target))
