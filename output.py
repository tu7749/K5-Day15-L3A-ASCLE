"""Văn bản an toàn sinh trực tiếp từ kế hoạch có cấu trúc."""

SLOT_LABELS = {"morning": "Sáng", "afternoon": "Chiều", "evening": "Tối"}
WEATHER_LABELS = {
    "forecast": "Dự báo", "climatology": "Ước tính theo thống kê nhiều năm",
    "cache": "Bản lưu thời tiết", "unavailable": "Chưa có dữ liệu thời tiết",
}


def vnd(value):
    return f"{value:,}".replace(",", ".") + " VNĐ"


def format_plan(plan):
    lines = []
    for error in plan["errors"]:
        lines.append(error["message"])
        if minimum := error.get("minimum_required_vnd"):
            lines.append(f"Mức tối thiểu theo các khoản có dữ liệu là {vnd(minimum)} cho cả nhóm.")
    if plan["total_cost_vnd"] is not None:
        totals = plan["total_cost_range"]
        lines.append(f"Tổng chi phí ước tính {vnd(totals['expected_vnd'])} cho cả nhóm.")
        lines.append(f"Khoảng chi phí tham khảo từ {vnd(totals['min_vnd'])} đến {vnd(totals['max_vnd'])}.")
    for day in plan["days"]:
        lines.append(f"Ngày {day['day']}")
        for slot, label in SLOT_LABELS.items():
            if item := day["slots"][slot]:
                lines.append(f"{label} · {item['name']}")
        if day["changed_because"]:
            lines.append(day["changed_because"])
    if room := plan["lodging_selected"]:
        lines.append(f"Chỗ ở tham khảo · {room['name']}. Giá là ước tính.")
    return "\n".join(lines)
