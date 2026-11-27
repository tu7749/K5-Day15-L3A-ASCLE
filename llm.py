"""Bedrock diễn đạt dữ liệu đã kiểm. Python luôn dựng được nội dung thay thế."""
import json
import logging
import os
from pathlib import Path

import config as cfg
from output import format_plan

LOG = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().with_name("prompt.md")
INTRO_LINES = ("Đây là gợi ý cho chuyến đi của bạn.", "Bạn có thể tham khảo lịch sau.")


def _allowed(plan):
    return {*INTRO_LINES, *format_plan(plan).splitlines()}


def validate_output(plan, llm_text):
    """Chấp nhận câu theo cấu trúc được cấp từ plan để chặn cả số lẫn địa danh mới."""
    if not isinstance(llm_text, str):
        return False
    lines = [line.strip() for line in llm_text.splitlines() if line.strip()]
    return bool(lines and any(line not in INTRO_LINES for line in lines)
                and len(lines) == len(set(lines)) and all(line in _allowed(plan) for line in lines)
                and (not plan["lodging_selected"] or any(line.startswith("Chỗ ở tham khảo · ") for line in lines)))


def _bedrock():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime", region_name=os.environ.get("AWS_REGION"),
        config=Config(connect_timeout=cfg.BEDROCK_CONNECT_SECONDS, read_timeout=cfg.BEDROCK_READ_SECONDS,
                      retries={"total_max_attempts": 2, "mode": "standard"}),
    )


def render_itinerary(plan, *, client=None, model_id=None):
    fallback = format_plan(plan)
    model_id = model_id or os.environ.get("BEDROCK_MODEL_ID")
    if not model_id or plan["errors"]:
        return fallback
    try:
        active = client if client is not None else _bedrock()
        response = active.converse(
            modelId=model_id,
            system=[{"text": PROMPT_PATH.read_text(encoding="utf-8")}],
            messages=[{
                "role": "user", "content": [{
                    "text": json.dumps({"allowed_lines": sorted(_allowed(plan))}, ensure_ascii=False)
                }],
            }],
            inferenceConfig={"maxTokens": cfg.BEDROCK_MAX_TOKENS, "temperature": 0},
        )
        content = response["output"]["message"]["content"]
        summary = "\n".join(block["text"] for block in content if "text" in block).strip()
    except Exception as error:
        LOG.warning("Dùng phần trình bày từ code do Bedrock lỗi (%s).", type(error).__name__)
        return fallback
    return summary if validate_output(plan, summary) else fallback
