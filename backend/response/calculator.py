import re
from typing import Any, Optional


class DeterministicCalculator:
    """
    Deterministic Calculation Engine.
    Performs all arithmetic on extracted numerical data so that charts, KPIs, and tables
    never rely on LLM arithmetic or hallucinated numbers.
    Preserves full precision internally.
    """

    @staticmethod
    def to_number(val: Any) -> Optional[float]:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
        if isinstance(val, str):
            cleaned = (
                val.replace(",", "")
                .replace("$", "")
                .replace("₹", "")
                .replace("%", "")
                .replace("(", "")
                .replace(")", "")
                .strip()
            )
            # Clean OCR prefix noise like 'I42000' -> '42000' or 'n42000' -> '42000'
            cleaned = re.sub(r"^[A-Za-z\s]+(?=\d)", "", cleaned).strip()
            # Handle strings like "4.85 Million"
            multiplier = 1.0
            lower = cleaned.lower()
            if "million" in lower or lower.endswith("m"):
                multiplier = 1_000_000.0
                cleaned = lower.replace("million", "").rstrip("m").strip()
            elif "cr" in lower or "crore" in lower:
                multiplier = 10_000_000.0
                cleaned = lower.replace("crore", "").replace("cr", "").strip()
            elif "lakh" in lower or lower.endswith("l"):
                multiplier = 100_000.0
                cleaned = lower.replace("lakh", "").rstrip("l").strip()
            elif lower.endswith("k"):
                multiplier = 1_000.0
                cleaned = lower.rstrip("k").strip()
            try:
                return float(cleaned) * multiplier
            except ValueError:
                return None
        return None

    @classmethod
    def compute_sum(cls, values: list[Any]) -> float:
        nums = [cls.to_number(v) for v in values]
        valid = [n for n in nums if n is not None]
        return sum(valid) if valid else 0.0

    @classmethod
    def compute_average(cls, values: list[Any]) -> float:
        nums = [cls.to_number(v) for v in values]
        valid = [n for n in nums if n is not None]
        return (sum(valid) / len(valid)) if valid else 0.0

    @classmethod
    def compute_min(cls, values: list[Any]) -> Optional[float]:
        nums = [cls.to_number(v) for v in values]
        valid = [n for n in nums if n is not None]
        return min(valid) if valid else None

    @classmethod
    def compute_max(cls, values: list[Any]) -> Optional[float]:
        nums = [cls.to_number(v) for v in values]
        valid = [n for n in nums if n is not None]
        return max(valid) if valid else None

    @classmethod
    def compute_count(cls, rows: list[Any]) -> int:
        return len(rows)

    @classmethod
    def compute_percentage(cls, part: Any, whole: Any) -> Optional[float]:
        p = cls.to_number(part)
        w = cls.to_number(whole)
        if p is None or w is None or w == 0:
            return None
        return (p / w) * 100.0

    @classmethod
    def compute_percentage_change(cls, from_val: Any, to_val: Any) -> Optional[float]:
        f = cls.to_number(from_val)
        t = cls.to_number(to_val)
        if f is None or t is None or f == 0:
            return None
        return ((t - f) / abs(f)) * 100.0

    @classmethod
    def compute_difference(cls, from_val: Any, to_val: Any) -> Optional[float]:
        f = cls.to_number(from_val)
        t = cls.to_number(to_val)
        if f is None or t is None:
            return None
        return t - f

    @classmethod
    def compute_ratio(cls, a_val: Any, b_val: Any) -> Optional[float]:
        a = cls.to_number(a_val)
        b = cls.to_number(b_val)
        if a is None or b is None or b == 0:
            return None
        return a / b

    @classmethod
    def group_by(
        cls,
        rows: list[dict[str, Any]],
        group_key: str,
        value_key: str,
        agg: str = "sum",
    ) -> list[dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        for r in rows:
            g = str(r.get(group_key, "Unknown"))
            v = cls.to_number(r.get(value_key))
            if v is not None:
                buckets.setdefault(g, []).append(v)

        out: list[dict[str, Any]] = []
        for g, vals in buckets.items():
            if agg == "average":
                agg_val = sum(vals) / len(vals)
            elif agg == "max":
                agg_val = max(vals)
            elif agg == "min":
                agg_val = min(vals)
            elif agg == "count":
                agg_val = float(len(vals))
            else:
                agg_val = sum(vals)
            out.append({group_key: g, value_key: agg_val})
        return out

    @classmethod
    def sort_rows(
        cls,
        rows: list[dict[str, Any]],
        sort_key: str,
        descending: bool = True,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        def key_fn(item: dict[str, Any]):
            v = item.get(sort_key)
            num = cls.to_number(v)
            return (0, num) if num is not None else (1, str(v or ""))

        sorted_list = sorted(rows, key=key_fn, reverse=descending)
        if limit is not None and limit > 0:
            return sorted_list[:limit]
        return sorted_list

    @classmethod
    def execute_operation(cls, spec: dict[str, Any]) -> Any:
        op = spec.get("operation", "").lower()
        if op == "percentage_change":
            return cls.compute_percentage_change(spec.get("from"), spec.get("to"))
        if op == "percentage":
            return cls.compute_percentage(spec.get("part"), spec.get("whole"))
        if op == "difference":
            return cls.compute_difference(spec.get("from"), spec.get("to"))
        if op == "ratio":
            return cls.compute_ratio(spec.get("a"), spec.get("b"))
        if op == "sum":
            return cls.compute_sum(spec.get("values", []))
        if op == "average":
            return cls.compute_average(spec.get("values", []))
        if op == "min":
            return cls.compute_min(spec.get("values", []))
        if op == "max":
            return cls.compute_max(spec.get("values", []))
        if op == "count":
            return cls.compute_count(spec.get("values", []))
        raise ValueError(f"Unsupported calculation operation: {op}")


calculator = DeterministicCalculator()
