"""Giao diện Streamlit của Đi Vừa Túi."""
from datetime import datetime
import logging
import os

import streamlit as st

import config as cfg
from data_loader import load_data
from llm import render_itinerary
from output import SLOT_LABELS, WEATHER_LABELS, vnd
from planner import TripRequest, build_plan
from weather_service import trip_weather

STYLES = {"tiet_kiem": "Tiết kiệm", "vua": "Vừa", "thoai_mai": "Thoải mái"}
TIERS = {"budget": "Tiết kiệm", "mid": "Vừa", "comfort": "Thoải mái"}
CONFIDENCES = {"high": "Cao", "medium": "Vừa", "low": "Thấp"}
COST_NAMES = {"food": "Ăn uống", "transport": "Thuê xe", "ticket": "Vé", "lodging": "Lưu trú"}


@st.cache_data(ttl=cfg.WEATHER_CACHE_SECONDS, max_entries=64, show_spinner=False)
def cached_weather(region, start_day, days):
    return trip_weather(region, start_day, days)


@st.cache_resource(ttl=cfg.DATA_CACHE_SECONDS, show_spinner=False)
def cached_catalog(bucket, prefix, region):
    # Các tham số cache phản ánh cấu hình S3. Loader đọc credential chain của boto3.
    return load_data()


def show_lodging(room):
    st.text(room["name"] + (f" · {room['area']}" if room["area"] else ""))
    totals = room["predicted_total"]
    if totals:
        st.caption(
            f"Ước tính {vnd(totals['min_vnd'])}–{vnd(totals['max_vnd'])} cho {room['rooms']} phòng/suất, "
            f"độ tin cậy {CONFIDENCES[room['confidence']].lower()}."
        )
    else:
        st.caption(f"Độ tin cậy {CONFIDENCES[room['confidence']].lower()}. Chưa tính được giá cho nhóm.")
    st.text(" ".join(room["reasons"]))
    if room["source"].startswith("https://") or room["source"].startswith("http://"):
        st.link_button("Xem nguồn giá", room["source"])
    st.caption(f"Ngày kiểm tra nguồn {room['source_date']}.")


def show_plan(plan):
    for error in plan["errors"]:
        st.error(error["message"])
        if amount := error.get("minimum_required_vnd"):
            st.write(f"Cần ít nhất **{vnd(amount)}** cho cả nhóm theo các khoản có dữ liệu.")
    for warning in plan["warnings"]:
        st.warning(warning)
    if plan["total_cost_range"]:
        totals = plan["total_cost_range"]
        budget = plan["budget_vnd"]
        first, second = st.columns(2)
        first.metric("Chi phí ước tính cho nhóm", vnd(plan["total_cost_vnd"]))
        second.metric("Còn lại theo cận trên", vnd(budget - totals["max_vnd"]))
        st.progress(totals["max_vnd"] / budget, text=f"Dự toán tối đa {vnd(totals['max_vnd'])} trên {vnd(budget)}")
        if plan["cost_breakdown"]:
            with st.expander("Xem các khoản chi"):
                st.dataframe([{
                    "Khoản": COST_NAMES[row["category"]], "Chi tiết": row["label"],
                    "Thấp": vnd(row["min_vnd"]), "Cao": vnd(row["max_vnd"]), "Nguồn": row["source"],
                } for row in plan["cost_breakdown"]], hide_index=True)
    for adjustment in plan["adjustments"]:
        st.caption(adjustment)
    if plan["days"]:
        st.subheader("Lịch trình")
        if plan["base_name"]:
            st.text("Điểm quy chiếu di chuyển mỗi ngày · " + plan["base_name"])
    for day in plan["days"]:
        weather = day["weather"]
        label = WEATHER_LABELS.get(weather["source"], WEATHER_LABELS["unavailable"])
        icon = {"forecast": "🌦️", "climatology": "📊", "cache": "🕒", "unavailable": "—"}.get(weather["source"], "—")
        if weather["rain_prob"] is not None:
            label += f" · Mưa {weather['rain_prob']:.0%}"
        with st.expander(f"Ngày {day['day']} · {icon} {label}", expanded=bool(day["changed_because"])):
            for slot, title in SLOT_LABELS.items():
                activity = day["slots"][slot]
                if activity:
                    duration_notice = " (ước tính)" if activity["duration_is_estimate"] else ""
                    st.text(f"{title} · {activity['name']} · {activity['duration_hours']:g} giờ{duration_notice}")
                else:
                    st.text(f"{title} · Thời gian linh hoạt")
            if day["changed_because"]:
                st.info(day["changed_because"])
            if day["travel_minutes"]:
                label = "quy đổi từ đường chim bay ở một số chặng" if day["route_estimated"] else "tham khảo từ dữ liệu tuyến"
                st.caption(f"Di chuyển khoảng {day['travel_minutes']} phút, {label}.")
    if plan["input"].get("days", 1) > 1:
        st.subheader("Gợi ý chỗ ở")
        if room := plan["lodging_selected"]:
            st.caption("Chỗ ở đang dùng để tính chi phí")
            show_lodging(room)
        for tier, options in plan["lodging_options"].items():
            with st.expander(TIERS[tier], expanded=bool(options)):
                if not options:
                    st.caption("Chưa có lựa chọn đủ dữ liệu trong mức giá này.")
                for option in options:
                    show_lodging(option)
        for room in plan["lodging_unpriced"]:
            show_lodging(room)
        if room := plan["lodging_gap"]:
            st.info(f"Chênh lệch giá thấp nhất với ngân sách lưu trú là {vnd(room['gap_vnd'])}.")
            show_lodging(room)
    if os.environ.get("BEDROCK_MODEL_ID") and plan["total_cost_vnd"] is not None:
        with st.expander("Xem tóm tắt lịch"):
            st.text(render_itinerary(plan))


def main():
    logging.basicConfig(level=logging.INFO)
    st.set_page_config(page_title="Đi Vừa Túi", page_icon="🧭", layout="centered")
    st.title("Đi Vừa Túi")
    st.caption("Lên lịch Hà Giang hoặc Đà Nẵng trong ngân sách của nhóm.")
    today = datetime.now(cfg.TIMEZONE).date()
    with st.form("trip"):
        first, second = st.columns(2)
        region = first.selectbox("Điểm đến", tuple(cfg.REGIONS), format_func=cfg.REGION_NAMES.get)
        days = first.number_input("Số ngày", min_value=1, max_value=cfg.MAX_DAYS, value=3, step=1)
        people = second.number_input("Số người", min_value=1, value=2, step=1)
        style = second.selectbox("Phong cách", tuple(STYLES), index=1, format_func=STYLES.get)
        budget = first.number_input("Ngân sách (VNĐ)", min_value=1, value=3_000_000, step=100_000)
        scope = second.radio("Ngân sách tính theo", ("Mỗi người", "Cả nhóm"), horizontal=True)
        departure = first.date_input("Ngày đi (có thể bỏ trống)", value=None, min_value=today)
        month = second.selectbox("Tháng đi nếu chưa chọn ngày", tuple(range(1, 13)), index=today.month - 1)
        submitted = st.form_submit_button("Lên lịch", type="primary", use_container_width=True)
    if submitted:
        try:
            catalog = cached_catalog(os.environ.get("S3_BUCKET"), os.environ.get("S3_PREFIX"), os.environ.get("AWS_REGION"))
        except (OSError, ValueError):
            st.error("Chưa đọc được dữ liệu đã kiểm tra. Thử lại sau khi cập nhật bộ CSV.")
            return
        with st.spinner("Đang kiểm tra lịch và chi phí…"):
            plan = build_plan(
                TripRequest(region, days, budget, people, month, departure, style,
                            "per_person" if scope == "Mỗi người" else "total"),
                catalog=catalog, weather=cached_weather,
            )
        show_plan(plan)


if __name__ == "__main__":
    main()
