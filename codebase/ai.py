"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI. NHÓM VIẾT phần gọi model thật.

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
    @model_call (từ tracing.py) tự ghi mỗi lần gọi vào trace; agent.py gọi call_model bao nhiêu lần
    cũng được, khung tự cộng token.
    Lỗi gọi model (hết lượt, sai key, mất mạng): cứ để exception bay ra — khung ghi lỗi vào cột error.

Chế độ giả (mặc định khi .env chưa có MODEL_PROVIDER, hoặc MODEL_PROVIDER=fake):
    chọn một mã từ danh sách đã kiểm, model "fake", token 0 — để luồng chạy hết từ trước CP2 (guide bước 3.2).
    Lượt `run.py eval` / `run.py simulate` chạy bằng model giả KHÔNG được tính.

Nối model thật qua llama.cpp trên máy. Xem docs/connect-model.md.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __package__:
    from .tracing import model_call
else:
    from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=os.path.join(ROOT, ".env")):
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có. Khung — không cần sửa."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()


def _call_llamacpp(system: str, user: str) -> dict:
    if not MODEL_NAME:
        raise RuntimeError("Chưa đặt MODEL_NAME cho llama.cpp. Xem docs/connect-model.md.")
    port = os.environ.get("LLAMA_CPP_PORT", "8087")
    if not port.isascii() or not port.isdecimal() or len(port) > 5 or not 1 <= int(port) <= 65535:
        raise ValueError("LLAMA_CPP_PORT phải là cổng từ 1 đến 65535.")

    candidates = json.loads(user)["candidates"]
    schema = {
        "type": "object",
        "properties": {"candidate_id": {"type": "string", "enum": [candidate["id"] for candidate in candidates]}},
        "required": ["candidate_id"], "additionalProperties": False,
    }
    request = Request(
        f"http://127.0.0.1:{int(port)}/v1/chat/completions",
        data=json.dumps({
            "model": MODEL_NAME,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": 256, "stream": False,
            "response_format": {"type": "json_object", "schema": schema},
        }, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"llama.cpp trả HTTP {error.code}. Kiểm tra tên model và cấu hình server.") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Chưa kết nối được llama.cpp tại cổng {int(port)}. Kiểm tra server local.") from error

    try:
        usage, model = payload["usage"], payload["model"]
        tokens_in, tokens_out = usage["prompt_tokens"], usage["completion_tokens"]
        body = payload["choices"][0]["message"]["content"]
        if not isinstance(model, str) or not model or type(tokens_in) is not int or type(tokens_out) is not int or min(tokens_in, tokens_out) < 0:
            raise ValueError("model hoặc usage không hợp lệ")
    except (KeyError, TypeError, IndexError, ValueError) as error:
        raise RuntimeError("llama.cpp trả phản hồi thiếu model, nội dung hoặc số token.") from error

    try:
        choice = json.loads(body)
    except (ValueError, TypeError):
        choice = {}
    chosen = choice.get("candidate_id") if isinstance(choice, dict) else None
    return {"text": chosen if isinstance(chosen, str) else "", "model": model,
            "tokens_in": tokens_in, "tokens_out": tokens_out}


@model_call
def call_model(system: str, user: str) -> dict:
    if MODEL_PROVIDER == "fake":
        candidates = json.loads(user)["candidates"]
        chosen = min(candidates, key=lambda item: (item["value"], item["id"]), default=None)
        return {"text": chosen["id"] if chosen else "", "model": "fake", "tokens_in": 0, "tokens_out": 0}

    if MODEL_PROVIDER == "llamacpp":
        return _call_llamacpp(system, user)

    raise NotImplementedError(
        "chưa viết phần gọi model thật cho MODEL_PROVIDER=%s trong codebase/ai.py — xem docs/connect-model.md"
        % MODEL_PROVIDER)
