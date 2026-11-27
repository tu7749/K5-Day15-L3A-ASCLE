"""Kiểm tra đầu vào form trước khi gửi cho planner.

Không phụ thuộc Streamlit để test được bằng python thuần.
validate_input(raw) -> (req, errors)
    raw:    dict giá trị thô từ form (chuỗi hoặc số)
    req:    dict đúng schema đầu vào planner nếu hợp lệ, None nếu có lỗi
    errors: danh sách câu báo lỗi tiếng Việt, dễ hiểu cho người dùng
"""
import datetime as dt
import re

MIN_DAYS, MAX_DAYS = 1, 5
MIN_PEOPLE, MAX_PEOPLE = 1, 20
MAX_BUDGET = 100_000_000          # 100 triệu / người: trên mức này coi là gõ nhầm
MAX_DAYS_AHEAD = 365
STYLES = {"tiet_kiem": "Tiết kiệm", "vua": "Vừa", "thoai_mai": "Thoải mái"}


def parse_budget(text) -> int:
    """'3000000', '3.000.000', '3,000,000', '3tr', '3.5tr', '3,5 triệu', '2500k' -> số VND.
    Sai định dạng thì ValueError."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return int(text)
    s = str(text or "").strip().lower().replace(" ", "")
    s = s.replace("vnđ", "").replace("vnd", "").replace("đ", "")
    if not s:
        raise ValueError("rỗng")
    m = re.fullmatch(r"(-?\d+(?:[.,]\d+)?)(tr|triệu|trieu|m|k|nghìn|nghin)", s)
    if m:
        num = float(m.group(1).replace(",", "."))
        unit = 1_000_000 if m.group(2) in ("tr", "triệu", "trieu", "m") else 1_000
        return int(round(num * unit))
    if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", s):      # 3.000.000 hoặc 3,000,000
        return int(re.sub(r"[.,]", "", s))
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    raise ValueError("không phải số")


def _to_int(value):
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    s = str(value or "").strip()
    if not re.fullmatch(r"-?\d+", s):
        raise ValueError
    return int(s)


def _to_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value or "").strip())


def validate_input(raw: dict, today: dt.date = None):
    today = today or dt.date.today()
    errors = []

    try:
        so_ngay = _to_int(raw.get("so_ngay"))
        if not MIN_DAYS <= so_ngay <= MAX_DAYS:
            errors.append("Số ngày phải từ %d đến %d (bản này chỉ lên lịch chuyến %d–%d ngày)."
                          % (MIN_DAYS, MAX_DAYS, MIN_DAYS, MAX_DAYS))
    except ValueError:
        errors.append("Số ngày phải là số nguyên, ví dụ 3.")
        so_ngay = None

    try:
        so_nguoi = _to_int(raw.get("so_nguoi"))
        if not MIN_PEOPLE <= so_nguoi <= MAX_PEOPLE:
            errors.append("Số người phải từ %d đến %d." % (MIN_PEOPLE, MAX_PEOPLE))
    except ValueError:
        errors.append("Số người phải là số nguyên, ví dụ 4.")
        so_nguoi = None

    try:
        budget = parse_budget(raw.get("ngan_sach_moi_nguoi"))
        if budget <= 0:
            errors.append("Ngân sách mỗi người phải lớn hơn 0.")
        elif budget > MAX_BUDGET:
            errors.append("Ngân sách mỗi người lớn bất thường (trên 100 triệu) — kiểm lại số 0.")
    except ValueError as e:
        if str(e) == "rỗng":
            errors.append("Chưa nhập ngân sách mỗi người.")
        else:
            errors.append("Ngân sách phải là số tiền, ví dụ 3000000, 3.000.000 hoặc 3tr.")
        budget = None

    try:
        ngay_di = _to_date(raw.get("ngay_di"))
        if ngay_di < today:
            errors.append("Ngày đi không được ở quá khứ.")
        elif (ngay_di - today).days > MAX_DAYS_AHEAD:
            errors.append("Ngày đi quá xa (trên 1 năm) — chưa có dữ liệu thời tiết để xếp lịch.")
    except ValueError:
        errors.append("Ngày đi không hợp lệ, định dạng YYYY-MM-DD.")
        ngay_di = None

    phong_cach = raw.get("phong_cach") or "vua"
    if phong_cach not in STYLES:
        errors.append("Phong cách phải là một trong: %s." % ", ".join(STYLES.values()))

    if errors:
        return None, errors
    return {
        "so_ngay": so_ngay,
        "ngan_sach_moi_nguoi": budget,
        "ngay_di": ngay_di.isoformat(),
        "so_nguoi": so_nguoi,
        "phong_cach": phong_cach,
    }, []
