"""Margin enforcement for physical and digital products.

Physical products: 40% minimum margin (sell = cost / 0.60 = cost * 1.6667)
Digital products:  70% minimum margin (sell = cost / 0.30 = cost * 3.333)

Margin calculation: margin% = (sell - cost) / sell * 100
For 40% margin: sell = cost / (1 - 0.40) = cost / 0.60 = cost * 1.6667
For 70% margin: sell = cost / (1 - 0.70) = cost / 0.30 = cost * 3.333
"""

PHYSICAL_MARKUP = 1.6667  # 40% margin floor on physical/dropship items
DIGITAL_MARKUP = 3.333    # 70% margin on digital products


def enforce_price(cost_price: float, is_digital: bool = False, custom_markup: float | None = None) -> float:
    """Return the recommended sell price enforcing minimum margin.

    If custom_markup is provided it must be >= the minimum for that category.
    """
    if cost_price is None or cost_price <= 0:
        return 0.0
    floor = DIGITAL_MARKUP if is_digital else PHYSICAL_MARKUP
    markup = max(custom_markup or floor, floor)
    # Round to nearest rupee (psychological pricing) ending in 9
    raw = cost_price * markup
    rounded = max(1, int(round(raw)))
    # Optional: round up to next .99 for retail feel
    if rounded < 100:
        return float(rounded)
    # Move to nearest 9 (e.g., 219 -> 219, 220 -> 229)
    last = rounded % 10
    if last == 9:
        return float(rounded)
    if last < 9:
        return float(rounded + (9 - last))
    return float(rounded + (19 - last))


def compute_margin(cost_price: float, sell_price: float) -> dict:
    if cost_price is None or cost_price <= 0:
        return {'margin_pct': 0.0, 'profit': sell_price or 0.0}
    profit = (sell_price or 0.0) - cost_price
    pct = (profit / sell_price * 100) if sell_price else 0.0
    return {'margin_pct': round(pct, 1), 'profit': round(profit, 2)}
