"""Giao diện web Streamlit cho lịch trình Hà Giang / Đà Nẵng.

Chạy: streamlit run streamlit_app.py
(python run.py vẫn là bản chạy thử dòng lệnh của khung chấm; file này không thay nó.)

Nguồn kế hoạch:
    - Có codebase/planner.py với hàm make_plan(req) -> dùng planner thật.
    - Chưa có -> đọc ui/mock_plan.json (dữ liệu giả, có ghi rõ trên giao diện).
Giao diện chỉ hiển thị, không tự tính tiền hay xếp lịch.
"""
import datetime as dt
import json
import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "codebase"))
sys.path.insert(0, ROOT)

from ui.result_page import render_result  # noqa: E402
from ui.validate import MAX_DAYS, MAX_PEOPLE, MIN_DAYS, MIN_PEOPLE, STYLES, DESTINATIONS, check_plan, validate_input  # noqa: E402

MOCK_PATHS = {"ha_giang": os.path.join(ROOT, "ui", "mock_plan.json"),
              "da_nang": os.path.join(ROOT, "ui", "mock_plan_da_nang.json")}


def get_plan(req: dict):
    """Trả (plan, is_mock)."""
    try:
        from planner import make_plan
    except ModuleNotFoundError as e:
        if e.name != "planner":      # lỗi import bên trong planner thì phải hiện ra, không che
            raise
        with open(MOCK_PATHS.get(req.get("diem_den"), MOCK_PATHS["ha_giang"]), encoding="utf-8") as f:
            return json.load(f), True
    try:
        return make_plan(req), False
    except Exception as e:  # lỗi hệ thống (thời tiết, Bedrock…): báo rõ, không crash trang
        return {"ok": False, "error": "Hệ thống đang lỗi, thử lại sau ít phút (%s)." % type(e).__name__}, False


def render_form():
    with st.form("trip_input"):
        diem_den = st.radio("Điểm đến", list(DESTINATIONS), format_func=DESTINATIONS.get, horizontal=True)
        c1, c2, c3 = st.columns(3)
        so_ngay = c1.number_input("Số ngày", min_value=MIN_DAYS, max_value=MAX_DAYS, value=3, step=1)
        so_nguoi = c2.number_input("Số người", min_value=MIN_PEOPLE, max_value=MAX_PEOPLE, value=4, step=1)
        phong_cach = c3.selectbox("Phong cách", list(STYLES), index=1, format_func=STYLES.get)
        c4, c5 = st.columns(2)
        ngan_sach = c4.text_input("Ngân sách mỗi người (VND)", value="3000000",
                                  help="Ví dụ: 3000000, 3.000.000, 3tr, 2,5 triệu")
        ngay_di = c5.date_input("Ngày đi", value=dt.date.today() + dt.timedelta(days=14),
                                min_value=dt.date.today(), format="DD/MM/YYYY")
        submitted = st.form_submit_button("Lên lịch", type="primary", use_container_width=True)
    if not submitted:
        return False, None
    req, errors = validate_input({
        "diem_den": diem_den, "so_ngay": so_ngay, "so_nguoi": so_nguoi, "phong_cach": phong_cach,
        "ngan_sach_moi_nguoi": ngan_sach, "ngay_di": ngay_di,
    })
    for msg in errors:
        st.error(msg)
    return True, req


def render_plan(plan: dict, is_mock: bool):
    problems = check_plan(plan)
    if problems:
        st.error("Kết quả từ planner sai định dạng (docs/schema.md) — báo người viết planner:")
        st.code("\n".join(problems))
        with st.expander("JSON nhận được"):
            st.json(plan)
        return
    if is_mock:
        st.warning("Đang hiển thị **dữ liệu giả** (ui/mock_plan*.json) — chưa nối planner. "
                   "Lịch không phụ thuộc số ngày, ngân sách vừa nhập.")
    if not plan.get("ok"):
        st.error(plan.get("error") or "Không xếp được lịch với đầu vào này.")
        return
    render_result(plan)
    with st.expander("JSON gốc (debug)"):
        st.json(plan)


def main():
    st.set_page_config(page_title="Lịch trình du lịch", page_icon="🏔️", layout="wide")
    st.title("🏔️ Lịch trình Hà Giang · Đà Nẵng theo ngân sách & thời tiết")
    st.caption("Chọn điểm đến, nhập số ngày, ngân sách mỗi người và ngày đi. Lịch có ngày mưa sẽ được đổi sang hoạt động phù hợp, kèm lý do.")

    submitted, req = render_form()
    if submitted and req is None:          # đầu vào sai: bỏ lịch cũ để không hiện lẫn với lỗi
        st.session_state.pop("plan", None)
    elif req:
        st.session_state["req"] = req
        st.session_state["plan"] = get_plan(req)

    if "plan" in st.session_state:
        plan, is_mock = st.session_state["plan"]
        render_plan(plan, is_mock)


main()
