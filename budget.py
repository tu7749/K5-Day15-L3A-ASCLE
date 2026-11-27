"""Phân bổ và kiểm trần chi phí bằng số nguyên VNĐ."""
import config as cfg


def allocate_budget(total_vnd, style):
    weights = cfg.BUDGET_SPLIT[style]
    parts = [total_vnd * weight // 100 for weight in weights[:-1]]
    # Giữ phần dư làm dự phòng để tổng phân bổ đúng từng đồng.
    return dict(zip(cfg.BUDGET_CATEGORIES, [*parts, total_vnd - sum(parts)]))


def estimate_band(lower, upper, *, source, source_date, confidence="medium"):
    return {
        "min_vnd": lower, "max_vnd": upper, "expected_vnd": (lower + upper + 1) // 2,
        "source": source, "source_date": source_date, "confidence": confidence, "is_estimate": True,
    }


def check_budget(budget_vnd, recompute, adjustments):
    """Thử tuần tự các điều chỉnh. recompute trả chi phí và kết quả hiện tại."""
    estimate = recompute()
    applied = []
    for message, change in adjustments:
        if estimate["max_vnd"] <= budget_vnd:
            break
        if change():
            applied.append(message)
            estimate = recompute()
    return {
        "fits_budget": estimate["max_vnd"] <= budget_vnd, "estimate": estimate, "adjustments": applied,
    }
