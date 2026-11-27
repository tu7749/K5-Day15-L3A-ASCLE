"""Luồng CLI. Demo, eval và simulate đều gọi answer(text)."""
from datetime import date
from decimal import Decimal
import json
import re
import unicodedata

from ai import call_model
from tools import load_destination, search_lodging, weather_scenario
from tracing import note

SYSTEM = (
    "Choose the candidate whose numeric value is smallest. When values are equal, choose the smallest ID. "
    "Return its ID as a JSON object with the single key candidate_id."
)
DESTINATION_PATTERNS = {"ha_giang": r"\bha[ _]giang\b", "da_nang": r"\bda[ _]nang\b"}
MONEY = re.compile(
    r"(?<![\w.,+\-])([+-]?\d+(?:[.,]\d+)*)(?:\s*(trieu|tr|nghin|ngan|k|vnd|dong|d)(?!\w))"
)
BUDGET_PREFIX = re.compile(r"\bngan sach\b(?:\s+moi nguoi)?(?:\s+la)?\s*[:=]?\s*")
BARE_MONEY = re.compile(r"([+-]?\d+(?:[.,]\d+)*)(?=\s*(?:/|,\s|;|\.|$))")
WEATHER_DAYS = re.compile(
    r"\b(?:mua(?: lon)?|ngap|lu|sat lo|dong set|bao lon)\s+ngay\s+"
    r"(\d{1,2}(?:(?:\s*,\s*|\s+va\s+|\s+den\s+|\s*-\s*)(?:ngay\s+)?\d{1,2})*)(?!\d)"
)
LODGING_TYPES = {
    "hotel": r"\b(?:khach san|hotel)\b",
    "guesthouse": r"\b(?:nha nghi|guesthouse)\b",
    "homestay": r"\bhomestay\b",
}
LODGING_TIERS = {"budget": "Tiết kiệm", "mid": "Vừa", "comfort": "Thoải mái"}
LODGING_SCOPE_LABELS = {
    "room_night": "mỗi phòng mỗi đêm", "person_night": "mỗi người mỗi đêm",
    "person_total": "mỗi người cho cả kỳ", "group_night": "cả nhóm mỗi đêm", "group_total": "cả nhóm cho cả kỳ",
}


def _normalize(text):
    text = unicodedata.normalize("NFKD", text.casefold()).replace("đ", "d")
    return "".join(char for char in text if not unicodedata.combining(char))


def _budget(text):
    prefix = BUDGET_PREFIX.search(text)
    if prefix:
        tail = text[prefix.end():]
        amount = MONEY.match(tail)
        bare = BARE_MONEY.match(tail) if amount is None else None
    else:
        matches = list(MONEY.finditer(text))
        amount = matches[0] if len(matches) == 1 else None
        bare = None
    if amount is None and bare is None:
        return None
    number = (amount or bare)[1]
    unit = amount[2] if amount else "vnd"
    if unit in {"trieu", "tr", "nghin", "ngan", "k"}:
        if not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", number):
            return None
        multiplier = 1_000_000 if unit in {"trieu", "tr"} else 1_000
        value = Decimal(number.replace(",", ".")) * multiplier
    else:
        if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:[.,]\d{3})+)", number):
            return None
        value = int(number.replace(".", "").replace(",", ""))
    return int(value) if 0 < value <= 10**12 and value == int(value) else None


def _departure(text):
    month_match = re.search(r"\bthang\s*(\d{1,2})(?!\d)", text)
    exact = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    local = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\b", text)
    try:
        if exact:
            value = date(*map(int, exact.groups()))
            return value.strftime("%d/%m/%Y")
        if local:
            day, month, year = local.groups()
            date(int(year or 2000), int(month), int(day))
            return f"{day}/{month}/{year}" if year else f"{day}/{month}"
    except ValueError:
        return None
    if month_match and 1 <= int(month_match[1]) <= 12:
        return f"tháng {int(month_match[1])}"
    return None


def _money(value):
    return f"{value:,}".replace(",", ".") + " VNĐ"


def _price_range(value):
    low, high = value["min_vnd"], value["max_vnd"]
    return _money(low) if low == high else f"{_money(low)}–{_money(high)}"


def _lodging_answer(text, destination, types):
    people_match = re.search(r"(?<![\w.,])([+-]?\d{1,4})\s*(?:nguoi|khach)\b", text)
    nights_match = re.search(r"(?<![\w.,])([+-]?\d{1,4})\s*dem\b", text)
    days_match = re.search(r"(?<![\w.,])([+-]?\d{1,4})\s*ngay\b", text)
    people = int(people_match[1]) if people_match else None
    nights = int(nights_match[1]) if nights_match else int(days_match[1]) - 1 if days_match else None
    if people is None or people <= 0 or nights is None or nights <= 0:
        return "Bạn có bao nhiêu người và ở mấy đêm? Ví dụ Đà Nẵng, 2 người, 2 đêm."

    budget_text = re.sub(r"\bngan sach\s+(?:luu tru|cho o|ca nhom|moi phong)\b", "ngan sach", text)
    budget = _budget(budget_text)
    nightly = bool(re.search(r"(?:/\s*dem\b|\b(?:mot|moi)\s+dem\b)", text))
    per_room = bool(re.search(r"(?:/\s*phong\b|\b(?:mot|moi)\s+phong\b|\bphong\s*/\s*dem\b)", text))
    per_person = bool(re.search(r"(?:/\s*nguoi\b|\b(?:mot|moi)\s+nguoi\b)", text))
    total = bool(re.search(r"\b(?:ca ky|ca chuyen|ca nhom|toan nhom|tong)\b", text))
    if budget is None or not (nightly or total) or (per_room and (per_person or not nightly)):
        return "Bạn muốn giới hạn ngân sách lưu trú thế nào? Ví dụ 500 nghìn/phòng/đêm hoặc tổng 2 triệu cho cả nhóm."

    if nightly:
        scope = "room_night" if per_room else "person_night" if per_person else "group_night"
    else:
        scope = "person_total" if per_person else "group_total"
    try:
        result = search_lodging(destination, nights, people, budget, scope, types)
    except (OSError, ValueError):
        return "Chưa đọc được bảng giá lưu trú đã kiểm tra. Bạn có thể thử lại sau."

    label = LODGING_SCOPE_LABELS[scope]
    lines = [f"{result['destination_name']} · {people} người · {nights} đêm · Trần lưu trú {_money(budget)} ({label})."]
    if result["uses_fallback"]:
        lines.append("Chỉ có bảng giá dự phòng theo vùng, chưa có danh mục giá của từng cơ sở.")
    if not any(result["groups"].values()):
        lines.append("Chưa có lựa chọn đủ dữ liệu với cận trên vừa ngân sách.")
        if cheapest := result["cheapest"]:
            lines.append(f"Lựa chọn có cận trên thấp nhất vượt {_money(cheapest['gap_vnd'])} ({label}).")
    else:
        for tier, options in result["groups"].items():
            if not options:
                continue
            lines.append(LODGING_TIERS[tier])
            for room in options:
                unit = "phòng" if room["price_unit"] == "per_room_night" else "suất"
                confidence = {"high": "cao", "medium": "vừa", "low": "thấp"}[room["confidence"]]
                area = f" · {room['area']}" if room["area"] else ""
                lines.append(
                    f"- {room['name']}{area} · {_price_range(room['price_range'])}/{unit}/đêm · "
                    f"{room['rooms']} {unit}, tổng {_price_range(room['predicted_total'])} cho cả kỳ · độ tin cậy {confidence}."
                )
                if room["price_unit_is_estimate"] or room["capacity_is_estimate"]:
                    lines.append("  Có giả định về đơn vị giá hoặc sức chứa.")
                lines.append(f"  Nguồn: {room['source']} (kiểm tra {room['source_date']}).")
    if result["unknown_count"]:
        lines.append("Các dòng chưa rõ đơn vị giá không được đưa vào dự toán.")
    lines.append("Giá là ước tính tham khảo. Hãy kiểm tra giá và tình trạng còn phòng với cơ sở.")
    return "\n".join(lines)


def _ticket_total(visits):
    return sum(visit["price_vnd"] for visit in visits if visit is not None)


def _choose_rain_option(candidates, preference):
    field = "price_vnd" if preference == "tiết kiệm" else "round_trip_minutes"
    payload = {
        "candidates": [{"id": item["id"], "value": item[field]} for item in candidates],
    }
    reply = call_model(SYSTEM, json.dumps(payload, ensure_ascii=False))
    chosen_id = reply["text"].strip()
    return next((item for item in candidates if item["id"] == chosen_id), None)


def _plan(destination, days, budget, departure, rain_day, severe, preference):
    data = load_destination(destination)
    weather = weather_scenario(rain_day, severe)
    if data["lodging_vnd"] is None or data["rental_vnd"] is None or not data["base_name"]:
        return "Chưa đủ dữ liệu giá chỗ ở, phương tiện hoặc điểm xuất phát để lập lịch."

    visits = [data["activities"].get(place_id) for place_id in data["visits"][:days]]
    if any(visit is None for visit in visits):
        return "Chưa đủ dữ liệu vé hoặc cung đường để lập lịch cho số ngày này."

    lodging = (days - 1) * data["lodging_vnd"]
    rental = days * data["rental_vnd"]
    fixed_cost = lodging + rental
    reason = ""
    if rain_day:
        index = rain_day - 1
        original = visits[index]
        other_visits = visits[:index] + visits[index + 1:]
        if severe:
            visits[index] = None
            reason = "Kịch bản có thời tiết nguy hiểm. Tạm hoãn hoạt động và kiểm tra cảnh báo địa phương trước khi di chuyển."
        elif not original["indoor"]:
            used = {visit["id"] for visit in other_visits}
            available = budget - fixed_cost - _ticket_total(other_visits)
            candidates = [
                visit for place_id in data["rain_options"]
                if (visit := data["activities"].get(place_id))
                and visit["indoor"] and visit["id"] not in used and visit["price_vnd"] <= available
            ]
            chosen = _choose_rain_option(candidates, preference) if candidates else None
            visits[index] = chosen
            if chosen:
                reason = f"Đổi {original['name']} sang {chosen['name']} vì kịch bản mưa, với vé và đường đi có trong dữ liệu."
            elif candidates:
                note("Model trả mã ngoài danh sách đã kiểm.")
                reason = "Chưa xác nhận được lựa chọn trong nhà. Giữ trống hoạt động ngày mưa."
            else:
                reason = "Chưa có hoạt động trong nhà đủ căn cứ, phù hợp tuyến và ngân sách. Giữ trống hoạt động ngày mưa."
        else:
            reason = "Hoạt động đã ở trong nhà. Kiểm tra đường đi và tình trạng mở cửa trước khi khởi hành."

    tickets = _ticket_total(visits)
    total = fixed_cost + tickets
    if total > budget:
        return (
            f"Ngân sách {_money(budget)}/người không đủ cho lịch mẫu này. "
            f"Chỗ ở, thuê xe và vé của lịch mẫu cần {_money(total)}/người. "
            "Bạn có thể giảm số ngày hoặc tăng ngân sách."
        )

    output = [
        f"{data['name']} · {days} ngày · {departure} · xuất phát mỗi ngày từ {data['base_name']}.",
        f"Thời tiết: {weather['source']}.",
    ]
    for index, visit in enumerate(visits, 1):
        if visit:
            output.append(
                f"Ngày {index} · {visit['name']} [{visit['id']}] · "
                f"vé {_money(visit['price_vnd'])} [{visit['cost_id']}] · "
                f"đi về khoảng {visit['round_trip_minutes']} phút theo OSRM."
            )
        else:
            output.append(f"Ngày {index} · Tạm để trống hoạt động.")
    if reason:
        output.append(f"Ngày {rain_day} · {reason}")
    output.extend([
        f"Chỗ ở {_money(lodging)} [{data['lodging_id']}] · thuê xe {_money(rental)} [{data['rental_id']}] · vé {_money(tickets)}.",
        f"Tổng ước tính: {_money(total)}/người · Ngân sách: {_money(budget)}/người · Còn lại: {_money(budget - total)}/người.",
        "Ước tính dùng giá vé tham khảo cho người lớn, một suất lưu trú và một xe thuê mỗi người. Ăn uống, xăng và đi đến điểm xuất phát tính riêng.",
        "Giá và thời gian là tham khảo. Kiểm tra giờ mở cửa, thời tiết và tình trạng đường trước khi đi.",
    ])
    return "\n".join(output)


def answer(text: str) -> dict:
    """Nhận yêu cầu chuyến đi và trả về khóa output chứa lịch hoặc phản hồi."""
    normalized = _normalize(text)
    if re.search(r"\b(?:dat|mua|thanh toan|xac nhan)\s+(?:ho\s+|giup\s+)?(?:ve|phong|tour|khach san)\b", normalized):
        return {"output": "Bản thử chỉ đề xuất lịch trình. Bạn tự kiểm tra và đặt vé hoặc phòng qua nhà cung cấp."}
    if re.search(r"\b(?:sua|doi|ghi de|gan|bo qua)\s+(?:bang\s+)?(?:gia ve|gia csv|du lieu gia|kiem tra ngan sach)\b", normalized):
        return {"output": "Giá vé và giới hạn ngân sách lấy từ dữ liệu đã kiểm tra. Mình không áp dụng yêu cầu sửa giá hoặc bỏ kiểm ngân sách."}

    destinations = [key for key, pattern in DESTINATION_PATTERNS.items() if re.search(pattern, normalized)]
    if len(destinations) != 1:
        return {"output": "Bản thử hỗ trợ một điểm đến mỗi lần. Bạn chọn Hà Giang hoặc Đà Nẵng nhé."}

    types = tuple(kind for kind, pattern in LODGING_TYPES.items() if re.search(pattern, normalized))
    if types or re.search(r"\b(?:cho o|luu tru|phong nghi)\b", normalized):
        return {"output": _lodging_answer(normalized, destinations[0], types)}

    day_match = re.search(r"(?<![\w/.,])([+-]?\d+)\s*ngay\b", normalized)
    days = int(day_match[1]) if day_match and len(day_match[1]) <= 3 else None
    if days is None or not 2 <= days <= 5:
        return {"output": "Bạn dự định đi bao nhiêu ngày? Bản thử hỗ trợ từ 2 đến 5 ngày."}
    if re.search(r"\b(?:ca nhom|tong nhom|toan nhom)\b", normalized) and not re.search(
        r"\b(?:moi nguoi|mot nguoi|\w+\s*/\s*nguoi)\b", normalized
    ):
        return {"output": "Bạn quy đổi ngân sách cả nhóm sang số tiền mỗi người giúp mình nhé."}
    budget = _budget(normalized)
    if budget is None:
        return {"output": "Bạn cho biết ngân sách dương mỗi người, ví dụ 3 triệu VNĐ/người."}
    departure = _departure(normalized)
    if departure is None:
        return {"output": "Bạn đi vào tháng nào hoặc ngày khởi hành nào? Ví dụ tháng 10 hoặc 08/10/2027."}

    rain_days = {int(day) for match in WEATHER_DAYS.finditer(normalized) for day in re.findall(r"\d+", match[1])}
    if len(rain_days) > 1:
        return {"output": "Bản thử xử lý một ngày có mưa. Bạn muốn đổi hoạt động cho ngày nào?"}
    rain_day = next(iter(rain_days), None)
    severe = bool(
        re.search(r"\bbão\b", unicodedata.normalize("NFC", text.casefold()))
        or re.search(r"\b(?:co bao|bao lon|lu|ngap|sat lo|dong set|mua lon)\b", normalized)
    )
    if severe and rain_day is None:
        return {"output": "Tạm hoãn hoạt động và kiểm tra cảnh báo địa phương. Bạn cho biết ngày bị ảnh hưởng để cập nhật lịch nếu cần."}
    if rain_day is not None and not 1 <= rain_day <= days:
        return {"output": f"Ngày mưa phải nằm trong chuyến đi {days} ngày. Bạn muốn kiểm tra ngày nào?"}
    preference = "tiết kiệm" if "tiet kiem" in normalized else "đường đi ngắn"
    return {"output": _plan(destinations[0], days, budget, departure, rain_day, severe, preference)}
