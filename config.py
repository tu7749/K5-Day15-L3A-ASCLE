"""Các ngưỡng và giả định công khai của Đi Vừa Túi."""
from zoneinfo import ZoneInfo

RAIN_THRESHOLD = 0.60  # Chỉ áp dụng với dự báo.
SEVERE_RAIN_PROBABILITY = 0.85  # Ngưỡng thận trọng của dự án, không phải cảnh báo chính thức.
FORECAST_DAYS = 16  # Cửa sổ dự báo do nhóm quy định.
WEATHER_TIMEOUT_SECONDS = 4
WEATHER_CACHE_SECONDS = 900
DATA_CACHE_SECONDS = 300
MAX_TRAVEL_HOURS_PER_DAY = 6
ROOM_CAPACITY_DEFAULT = 2  # Giả định khi giá tính theo phòng nhưng chưa biết sức chứa.
ONE_BED_PERSONS = 1  # Một giường tính cho một người.
PEOPLE_PER_MOTORBIKE = 1  # Dự toán một xe mỗi người, không tính xăng khi thiếu giá đúng loại.
MEALS_PER_DAY = 3  # Một đơn vị món tính cho một bữa tham khảo.
FALLBACK_TRAVEL_KMH = 20  # Quy đổi quãng đường chim bay thành phút ước tính, không dùng như thời gian thực.
FRESH_DAYS = 90
PRICE_WIDTH_MAX = 0.40
TIER_MIN_SAMPLE = 9
MAX_LODGING_OPTIONS = 3
DEFAULT_STYLE = "vua"
BUDGET_SPLIT = {
    "tiet_kiem": (30, 25, 30, 5, 10),
    "vua": (35, 25, 25, 5, 10),
    "thoai_mai": (40, 25, 20, 5, 10),
}
BUDGET_CATEGORIES = ("lodging", "food", "transport", "ticket", "reserve")
LODGING_WEIGHTS = {"fit": 0.55, "rating": 0.15, "distance": 0.20, "freshness": 0.10}
REGIONS = {
    "ha_giang": (22.82, 104.98),  # Tọa độ tâm dùng cho thời tiết, cần xác nhận khi tích hợp.
    "da_nang": (16.05, 108.20),
}
REGION_NAMES = {"ha_giang": "Hà Giang", "da_nang": "Đà Nẵng"}
BASE_PLACES = {"ha_giang": "H11", "da_nang": "D01"}  # Điểm quy chiếu tuyến nếu thiếu tọa độ chỗ ở.
TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
DURATION_HOURS = {
    "viewpoint": 1.0, "culture": 1.5, "nature": 2.0, "food": 1.0,
    "market": 1.5, "activity": 2.0, "other": 1.0,
}  # Toàn bộ là giả định; từng địa điểm dùng mặc định có cờ trong kết quả.
ASSUMED_ROOM_TYPES = frozenset({"hotel", "guesthouse"})
POINT_PRICE_CONFIDENCE_LIMIT = "medium"
UNKNOWN_UNIT_CONFIDENCE = "low"
AMBIGUOUS_NIGHT_UNITS = frozenset({"", "night_unspecified"})
SLOT_MINUTES = {"morning": 180, "afternoon": 240, "evening": 180}
MAX_DAYS = 5
EARTH_RADIUS_KM = 6371.0088  # Bán kính trung bình trong công thức haversine.
S3_CONNECT_SECONDS = 1
S3_READ_SECONDS = 2
BEDROCK_CONNECT_SECONDS = 1
BEDROCK_READ_SECONDS = 2
BEDROCK_MAX_TOKENS = 350
ASSUMPTION_SOURCE_DATE = "2026-11-27"  # Ngày nhóm ghi các giả định của bản thiết kế.
