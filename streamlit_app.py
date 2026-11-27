"""Giao diện web Streamlit cho lịch trình Hà Giang.

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

from ui.validate import MAX_DAYS, MAX_PEOPLE, MIN_DAYS, MIN_PEOPLE, STYLES, check_plan, validate_input  # noqa: E402

MOCK_PATH = os.path.join(ROOT, "ui", "mock_plan.json")
WEATHER_ICON = {"nang": "☀️", "may": "☁️", "mua": "🌧️"}
SLOT_LABEL = [("sang", "Sáng"), ("chieu", "Chiều"), ("toi", "Tối")]
COST_LABEL = {"cho_o": "Chỗ ở", "an_uong": "Ăn uống", "di_lai": "Đi lại", "ve": "Vé tham quan", "du_phong": "Dự phòng"}


def vnd(n) -> str:
    return "{:,}đ".format(int(n)).replace(",", ".")


def get_plan(req: dict):
    """Trả (plan, is_mock)."""
    try:
        from planner import make_plan
    except ModuleNotFoundError as e:
        if e.name != "planner":      # lỗi import bên trong planner thì phải hiện ra, không che
            raise
        with open(MOCK_PATH, encoding="utf-8") as f:
            return json.load(f), True
    try:
        return make_plan(req), False
    except Exception as e:  # lỗi hệ thống (thời tiết, Bedrock…): báo rõ, không crash trang
        return {"ok": False, "error": "Hệ thống đang lỗi, thử lại sau ít phút (%s)." % type(e).__name__}, False


def render_form():
    with st.form("trip_input"):
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
        "so_ngay": so_ngay, "so_nguoi": so_nguoi, "phong_cach": phong_cach,
        "ngan_sach_moi_nguoi": ngan_sach, "ngay_di": ngay_di,
    })
    for msg in errors:
        st.error(msg)
    return True, req


def render_preview(plan: dict, is_mock: bool):
    """Hiển thị thử (việc 1). Trang kết quả đầy đủ làm ở việc 4."""
    problems = check_plan(plan)
    if problems:
        st.error("Kết quả từ planner sai định dạng (docs/schema.md) — báo người viết planner:")
        st.code("\n".join(problems))
        with st.expander("JSON nhận được"):
            st.json(plan)
        return
    if is_mock:
        st.warning("Đang hiển thị **dữ liệu giả** (ui/mock_plan.json) — chưa nối planner. "
                   "Kết quả không phụ thuộc đầu vào vừa nhập.")
    if not plan.get("ok"):
        st.error(plan.get("error") or "Không xếp được lịch với đầu vào này.")
        return

    used, total = plan["total_per_person"], plan["budget_per_person"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng chi phí / người", vnd(used))
    c2.metric("Ngân sách / người", vnd(total))
    c3.metric("Còn lại", vnd(total - used))

    if plan.get("text"):
        st.markdown(plan["text"])

    for d in plan["days"]:
        w = d.get("weather") or {}
        head = "Ngày %d · %s · %s mưa %d%%" % (
            d["day"], d.get("date", ""), WEATHER_ICON.get(w.get("condition"), ""), round((w.get("rain_prob") or 0) * 100))
        if d.get("changed_because"):
            head = "🔄 " + head
        with st.expander(head, expanded=True):
            if d.get("changed_because"):
                st.info("Đổi lịch: " + d["changed_because"])
            for msg in d.get("warnings") or []:
                st.warning(msg)
            for key, label in SLOT_LABEL:
                items = d.get("slots", {}).get(key) or []
                text = ", ".join("%s (%s)" % (i["name"], vnd(i.get("cost", 0))) for i in items) or "—"
                st.markdown("**%s:** %s" % (label, text))

    st.subheader("Chi phí mỗi người")
    st.table([{"Khoản": COST_LABEL.get(k, k), "Số tiền": vnd(v)} for k, v in plan["cost_breakdown"].items()])

    with st.expander("JSON gốc (debug)"):
        st.json(plan)


def main():
    st.set_page_config(page_title="Lịch trình Hà Giang", page_icon="🏔️", layout="wide")
    st.title("🏔️ Lịch trình Hà Giang theo ngân sách & thời tiết")
    st.caption("Nhập số ngày, ngân sách mỗi người và ngày đi. Lịch có ngày mưa sẽ được đổi sang hoạt động phù hợp, kèm lý do.")

    submitted, req = render_form()
    if submitted and req is None:          # đầu vào sai: bỏ lịch cũ để không hiện lẫn với lỗi
        st.session_state.pop("plan", None)
    elif req:
        st.session_state["req"] = req
        st.session_state["plan"] = get_plan(req)

    if "plan" in st.session_state:
        plan, is_mock = st.session_state["plan"]
        render_preview(plan, is_mock)


main()
