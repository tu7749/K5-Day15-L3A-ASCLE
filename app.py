"""Việt Du: giao diện Streamlit và cầu nối form tới bộ lập lịch Python."""
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path

import streamlit as st

from codebase.ai import MODEL_PROVIDER, call_model
from config import DATA_CACHE_SECONDS, TIMEZONE
from data_loader import load_data
from llm import render_itinerary
from vietdu_planner import INTERESTS, STARTS, Request, build_trip

FRONTEND = Path(__file__).resolve().parent / "frontend"
LOG = logging.getLogger(__name__)
RAIN_PROMPT = (
    "Select the indoor activity with the shortest travel time. Choose the candidate whose numeric "
    "value is smallest. Return its ID in a JSON object with the single key candidate_id."
)
PAGE_CSS = """
<style>
[data-testid="stHeader"] { display:none; }
[data-testid="stAppViewContainer"] {background:#f7f4ed;}
[data-testid="stMainBlockContainer"] {max-width:none!important; padding:0!important;}
</style>
"""


@st.cache_resource(ttl=DATA_CACHE_SECONDS, show_spinner=False)
def cached_catalog(bucket, prefix, aws_region):
    return load_data()


def _catalog():
    return cached_catalog(os.environ.get("S3_BUCKET"), os.environ.get("S3_PREFIX"), os.environ.get("AWS_REGION"))


def _choose_indoor(candidates):
    try:
        return call_model(RAIN_PROMPT, json.dumps({"candidates": candidates}))
    except (OSError, RuntimeError, ValueError):
        LOG.warning("Model local chưa trả được gợi ý đổi lịch", exc_info=True)
        return None


def _summarize(plan):
    """Convert only verified facts into the existing checked Bedrock renderer."""
    cost = plan["total_known"] + plan["total_reserved"] if plan["budget_status"] == "within" else None
    days = [
        {"day": index, "slots": dict(zip(("morning", "afternoon", "evening"), day["items"])),
         "changed_because": day["reason"]}
        for index, day in enumerate(plan["days"], 1)
    ]
    return render_itinerary({
        "days": days, "errors": [], "lodging_selected": None,
        "total_cost_vnd": cost,
        "total_cost_range": {"expected_vnd": cost, "min_vnd": cost, "max_vnd": cost},
    })


def _submit():
    state = st.session_state
    payload = state["vietdu"].get("submitted")
    state["sequence"] = state.get("sequence", 0) + 1
    state["plan"] = None
    state["error"] = ""
    try:
        today = datetime.now(TIMEZONE).date()
        request = Request.parse(payload, today)
        state["values"] = payload
        catalog = _catalog()
        selector = _choose_indoor if MODEL_PROVIDER == "llamacpp" else None
        plan = build_trip(request, catalog, indoor_selector=selector)
        if os.environ.get("BEDROCK_MODEL_ID"):
            plan["summary"] = _summarize(plan)
        state["plan"] = plan
    except ValueError as error:
        state["error"] = str(error)
    except (OSError, TypeError, KeyError):
        LOG.exception("Không tạo được lịch Việt Du")
        state["error"] = "Chưa tải được dữ liệu lịch trình. Vui lòng thử lại."


def main():
    st.set_page_config(page_title="Việt Du · Lập lịch trình", page_icon="🧭", layout="wide")
    st.html(PAGE_CSS)
    leaflet = (FRONTEND / "leaflet.js").read_text(encoding="utf-8").split("//# sourceMappingURL=", 1)[0]
    css = "\n".join((FRONTEND / name).read_text(encoding="utf-8") for name in ("fonts.css", "leaflet.css", "style.css"))
    component = st.components.v2.component(
        "vietdu_planner",
        html=(FRONTEND / "index.html").read_text(encoding="utf-8"), css=css,
        js=leaflet + "\n" + (FRONTEND / "app.js").read_text(encoding="utf-8"), isolate_styles=False,
    )
    try:
        catalog = _catalog()
        names = {row["place_id"]: row["name"] for row in catalog.places if row["lat"] is not None}
    except (OSError, ValueError):
        names = {}
    origins = {region: [{"id": key, "name": names[key]} for key in keys if key in names] for region, keys in STARTS.items()}
    state = st.session_state
    today = datetime.now(TIMEZONE).date()
    component(
        key="vietdu", on_submitted_change=_submit,
        data={
            "asset_base": "/app/static/assets/",
            "today": today.isoformat(), "tomorrow": (today + timedelta(days=1)).isoformat(),
            "values": state.get("values", {}), "sequence": state.get("sequence", 0),
            "origins": origins, "interests": INTERESTS, "plan": state.get("plan"), "error": state.get("error"),
        },
    )


if __name__ == "__main__":
    main()
