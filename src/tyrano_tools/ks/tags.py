from __future__ import annotations

import re

BRACKET_TAG_PATTERN = re.compile(r"^\[(\w+)\s*(.*?)\]\s*$")
AT_TAG_PATTERN = re.compile(r"^@(\w+)\s*(.*?)\s*$")
ATTR_PATTERN = re.compile(r"(\w+)=\"([^\"]*)\"|(\w+)=([^\s]+)")


def parse_tag_attributes(attr_blob: str) -> dict[str, str]:
    attributes: dict[str, str] = {}

    for attr_match in ATTR_PATTERN.finditer(attr_blob):
        key = attr_match.group(1) or attr_match.group(3)
        value = attr_match.group(2) or attr_match.group(4) or ""
        attributes[key] = value

    return attributes


def parse_bracket_tag_line(line: str) -> tuple[str, dict[str, str]] | None:
    match = BRACKET_TAG_PATTERN.match(line.strip())
    if not match:
        return None

    return match.group(1), parse_tag_attributes(match.group(2))


def parse_tyrano_tag_line(line: str) -> tuple[str, dict[str, str]] | None:
    stripped = line.strip()
    match = BRACKET_TAG_PATTERN.match(stripped)
    if not match:
        match = AT_TAG_PATTERN.match(stripped)
    if not match:
        return None

    return match.group(1), parse_tag_attributes(match.group(2))
