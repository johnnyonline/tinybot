import os
from typing import Any


def event_signature(abi: list[dict[str, Any]], event_name: str) -> str:
    for item in abi:
        if item.get("type") == "event" and item.get("name") == event_name:
            types = ",".join(inp["type"] for inp in item["inputs"])
            return f"{event_name}({types})"
    raise ValueError(f"event '{event_name}' not found in ABI")


def event_id(log) -> str:
    return f"{log.transactionHash.hex()}:{log.logIndex}"


DEBUG = os.getenv("DEBUG", False)


def debug(msg: str):
    if DEBUG:
        print(f"DEBUG: {msg}")
