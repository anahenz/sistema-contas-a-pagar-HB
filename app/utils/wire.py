"""JSON transport preserving dates without executing serialized code."""
from datetime import date, datetime


def encode(value):
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(v) for v in value]
    return value


def decode(value):
    if isinstance(value, dict):
        if set(value) == {"$date"}:
            return date.fromisoformat(value["$date"])
        if set(value) == {"$datetime"}:
            return datetime.fromisoformat(value["$datetime"])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value
