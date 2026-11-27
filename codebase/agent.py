"""Luồng chính CP2. Demo, eval và simulate đều gọi answer(text)."""
from datetime import date
from decimal import Decimal
import json
import re
import unicodedata

from ai import call_model
from tools import load_destination, weather_scenario
from tracing import note

SYSTEM = (
    "Chọn một candidate_id từ danh sách đã kiểm tra. "
    "Dựa vào ưu tiên và dữ liệu JSON được cung cấp. "
    "Trả đúng một mã, không thêm giá, địa điểm hay lời giải thích."
)
DESTINATION_PATTERNS = {"ha_giang": r"\bha giang\b", "da_nang": r"\bda nang\b"}
MONEY = re.compile(
    r"(?<![\w.,+\-])([+-]?\d+(?:[.,]\d+)*)(?:\s*(trieu|tr|nghin|ngan|k|vnd|dong|d)(?!\w))"
)
BUDGET_PREFIX = re.compile(r"\bngan sach\b(?:\s+moi nguoi)?(?:\s+la)?\s*[:=]?\s*")
BARE_MONEY = re.compile(r"([+-]?\d+(?:[.,]\d+)*)(?=\s*(?:/|,\s|;|\.|$))")
WEATHER_DAYS = re.compile(
    r"\b(?:mua(?: lon)?|ngap|lu|sat lo|dong set|bao lon)\s+ngay\s+"
    r"(\d{1,2}(?:(?:\s*,\s*|\s+va\s+|\s+den\s+|\s*-\s*)(?:ngay\s+)?\d{1,2})*)(?!\d)"
)


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


def _ticket_total(visits):
    return sum(visit["price_vnd"] for visit in visits if visit is not None)


def _choose_rain_option(candidates, preference):
    payload = {
        "preference": preference,
        "candidates": [
            {"id": item["id"], "name": item["name"], "price_vnd": item["price_vnd"],
             "round_trip_minutes": item["round_trip_minutes"]}
            for item in candidates
        ],
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
