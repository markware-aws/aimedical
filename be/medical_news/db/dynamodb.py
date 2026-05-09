from __future__ import annotations

import os
from typing import Any

import boto3

from medical_news.types import ProcessedRecord

_table = None


def _resource():
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))


def _get_table():
    global _table
    if _table is None:
        _table = _resource().Table(os.environ.get("DYNAMODB_TABLE", "aimedical_articles"))
    return _table


def exists(pk: str) -> bool:
    res: dict[str, Any] = _get_table().get_item(Key={"pk": pk}, ProjectionExpression="pk")
    return bool(res.get("Item"))


def put(record: ProcessedRecord) -> None:
    _get_table().put_item(Item=record)
