"""Trang kết quả (việc 4): lịch từng ngày sáng / chiều / tối, bảng chi phí, tổng tiền.

Chỉ hiển thị JSON planner trả về (docs/schema.md). Không tự tính tiền hay xếp lịch:
mọi con số lấy nguyên từ planner. Phép cộng duy nhất ở đây là để PHÁT HIỆN planner
trả tổng không khớp các khoản, rồi cảnh báo.
"""
import datetime as dt

import streamlit as st

from ui.validate import DESTINATIONS, STYLES

WEATHER = {"nang": ("☀️", "Nắng"), "may": ("☁️", "Nhiều mây"), "mua": ("🌧️", "Mưa")}
SLOTS = [("sang", "🌅 Sáng"), ("chieu", "🌇 Chiều"), ("toi", "🌙 Tối")]
COST_LABEL = {"cho_o": "🏨 Chỗ ở", "an_uong": "🍜 Ăn uống", "di_lai": "🛵 Đi lại",
              "ve": "🎫 Vé tham quan", "du_phong": "🧰 Dự phòng"}
WEEKDAY = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


def vnd(n) -> str:
    return "{:,}đ".format(int(n)).replace(",", ".")


def nice_date(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return "%s %s" % (WEEKDAY[d.weekday()], d.strftime("%d/%m"))


def render_summary(plan: dict):
    inp = plan.get("input") or {}
    if inp:
        parts = [DESTINATIONS.get(inp.get("diem_den"), ""),
                 "%s ngày" % inp.get("so_ngay", "?"),
                 "từ %s" % nice_date(inp.get("ngay_di", "")),
                 "%s người" % inp.get("so_nguoi", "?"),
                 STYLES.get(inp.get("phong_cach"), "")]
        st.markdown("#### " + " · ".join(p for p in parts if p))

    used, budget = plan["total_per_person"], plan["budget_per_person"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng chi phí ước tính / người", vnd(used))
    c2.metric("Ngân sách / người", vnd(budget))
    if used <= budget:
        c3.metric("Còn lại / người", vnd(budget - used))
    else:   # planner không nên trả thế này, nhưng nếu có thì phải lộ ra
        c3.metric("Vượt ngân sách / người", vnd(used - budget), delta="vượt", delta_color="inverse")

    changed = [d["day"] for d in plan["days"] if d.get("changed_because")]
    if changed:
        st.info("🔄 Đã đổi lịch vì mưa ở ngày: %s. Lý do ghi ở từng ngày bên dưới." % ", ".join(map(str, changed)))


def render_activity(a: dict):
    kind = "🏠 Trong nhà" if a.get("indoor") else "🌤️ Ngoài trời"
    cost = vnd(a.get("cost", 0)) if a.get("cost") else "Miễn phí"
    st.markdown("**%s**  \n%s · 🎫 %s" % (a.get("name", "?"), kind, cost))


def render_day(d: dict):
    w = d.get("weather") or {}
    icon, cond = WEATHER.get(w.get("condition"), ("", w.get("condition") or ""))
    rain = round((w.get("rain_prob") or 0) * 100)
    temp = " · %s°C" % w["temp_c"] if w.get("temp_c") is not None else ""
    with st.container(border=True):
        head = "### Ngày %d · %s" % (d["day"], nice_date(d.get("date", "")))
        if d.get("changed_because"):
            head += " · 🔄 đã đổi lịch"
        st.markdown(head)
        st.caption("%s %s%s · khả năng mưa %d%%" % (icon, cond, temp, rain))
        if d.get("changed_because"):
            st.info("**Lý do đổi lịch:** " + d["changed_because"])
        for msg in d.get("warnings") or []:
            st.warning("⚠️ " + msg)
        cols = st.columns(3)
        for col, (key, label) in zip(cols, SLOTS):
            with col:
                st.markdown("**%s**" % label)
                items = (d.get("slots") or {}).get(key) or []
                if not items:
                    st.markdown("_Tự do / nghỉ ngơi_")
                for a in items:
                    render_activity(a)


def render_costs(plan: dict):
    st.subheader("💰 Chi phí ước tính mỗi người")
    cb = plan["cost_breakdown"]
    rows = [{"Khoản": COST_LABEL.get(k, k), "Số tiền": vnd(v)} for k, v in cb.items()]
    rows.append({"Khoản": "**Tổng / người**", "Số tiền": "**%s**" % vnd(plan["total_per_person"])})
    st.table(rows)
    if sum(cb.values()) != plan["total_per_person"]:
        st.warning("Tổng các khoản (%s) không khớp tổng planner trả về (%s) — báo người viết planner."
                   % (vnd(sum(cb.values())), vnd(plan["total_per_person"])))
    st.caption("Giá là ước tính từ nguồn công khai (xem data/DATA_CARD.md), có thể thay đổi theo mùa.")


def render_result(plan: dict):
    """plan đã qua check_plan() và ok=True."""
    render_summary(plan)
    if plan.get("text"):
        with st.container(border=True):
            st.markdown(plan["text"])
    st.subheader("🗓️ Lịch từng ngày")
    for d in plan["days"]:
        render_day(d)
    render_costs(plan)
