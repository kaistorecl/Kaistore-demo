def score_product(signals: dict) -> int:
    weights = {"trend":0.35, "utility":0.35, "competition":0.15, "margin":0.15}
    s = sum(signals.get(k,0)*w for k,w in weights.items())
    return int(round(max(0, min(100, s))))
