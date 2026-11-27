"""Đọc một snapshot nhất quán từ S3 hoặc CSV local, rồi kiểm schema chuẩn."""
from concurrent.futures import ThreadPoolExecutor
import csv
from io import StringIO
import logging
import os
from pathlib import Path

import config as cfg
from data_adapter import CORE_COLUMNS, FIELD_MAP, Catalog, adapt
from validate_data import validate_data

DATA_PATH = Path(__file__).resolve().parent / "data"
LOG = logging.getLogger(__name__)
CORE_FILES = ("places", "costs", "routes")


def _parse(name, content):
    reader = csv.DictReader(StringIO(content.removeprefix("\ufeff"), newline=""))
    headers = reader.fieldnames or ()
    aliases = FIELD_MAP.get(name, {})
    missing = [field for field in CORE_COLUMNS[name] if field not in headers and aliases.get(field) not in headers]
    if missing or len(headers) != len(set(headers)):
        raise ValueError(f"{name}.csv thiếu cột hoặc trùng tiêu đề: {', '.join(missing)}")
    rows = list(reader)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"{name}.csv có dòng sai số cột")
    return rows


def _snapshot(read, source):
    optional = read("lodging")
    lodging_files = ("accommodations", "accommodation_prices")
    with ThreadPoolExecutor(max_workers=6) as executor:
        pending = {name: executor.submit(read, name) for name in (*CORE_FILES, "duration_overrides", *(lodging_files if optional is None else ()))}
        inputs = {name: task.result() for name, task in pending.items()}
    if optional is not None:
        inputs["lodging"] = optional
    elif sum(inputs[name] is None for name in lodging_files) == 1:
        raise ValueError("Hai bảng lưu trú hiện có phải đi cùng nhau.")
    elif all(inputs[name] is None for name in lodging_files):
        LOG.warning("Không có bảng lưu trú riêng. Dùng giá dự phòng từ costs.csv khi có.")
    missing = [name for name in CORE_FILES if inputs[name] is None]
    if missing:
        raise ValueError("Thiếu CSV: " + ", ".join(missing))
    tables = {name: _parse(name, value) for name, value in inputs.items() if value is not None}
    empty = [name for name in CORE_FILES if not tables[name]]
    if empty:
        raise ValueError("CSV không có bản ghi: " + ", ".join(empty))
    data = adapt(tables, source)
    errors = validate_data(data)
    if errors:
        raise ValueError("\n".join(errors[:10]))
    return data


def _load_s3(bucket):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3", region_name=os.environ.get("AWS_REGION"),
        config=Config(connect_timeout=cfg.S3_CONNECT_SECONDS, read_timeout=cfg.S3_READ_SECONDS,
                      retries={"total_max_attempts": 1}),
    )
    prefix = os.environ.get("S3_PREFIX", "data").strip("/")

    def read(name):
        filename = f"{name}.csv"
        key = f"{prefix}/{filename}" if prefix else filename
        try:
            body = client.get_object(Bucket=bucket, Key=key)["Body"]
        except ClientError as error:
            if error.response["Error"]["Code"] in {"NoSuchKey", "404", "NotFound"}:
                return None
            raise
        with body:
            return body.read().decode("utf-8-sig")

    return _snapshot(read, f"s3://{bucket}/{prefix}")


def load_data(path: Path = DATA_PATH, *, use_s3: bool = True) -> Catalog:
    bucket = os.environ.get("S3_BUCKET") if use_s3 else None
    if bucket:
        try:
            catalog = _load_s3(bucket)
        except Exception as error:
            LOG.warning("S3 không dùng được (%s). Đọc toàn bộ snapshot local.", type(error).__name__)
        else:
            LOG.info("Nguồn CSV: %s", catalog.source)
            return catalog

    def read(name):
        candidate = path / f"{name}.csv"
        return candidate.read_text(encoding="utf-8-sig") if candidate.is_file() else None

    catalog = _snapshot(read, "local")
    LOG.info("Nguồn CSV: local (%s)", path)
    return catalog
