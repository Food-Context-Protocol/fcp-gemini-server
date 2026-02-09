"""Robust JSON extraction from LLM responses.

LLMs often wrap JSON in markdown code fences or include extra text.
This module provides utilities to reliably extract JSON from such responses.
"""

import json
import re
from typing import Any


def extract_json(text: str | None) -> dict[str, Any] | list[Any] | None:
    """
    Extract JSON from LLM response text.

    Handles common LLM output patterns:
    1. Pure JSON response
    2. JSON wrapped in ```json ... ``` markdown code blocks
    3. JSON wrapped in ``` ... ``` generic code blocks
    4. JSON embedded in prose text
    5. Multiple JSON objects (returns first valid one)

    Args:
        text: The raw text response from the LLM (None returns None)

    Returns:
        Parsed JSON as dict or list, or None if extraction fails
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Strategy 1: Try parsing the whole text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    if json_block_match := re.search(r"```json\s*([\s\S]*?)```", text, re.IGNORECASE):
        try:
            return json.loads(json_block_match[1].strip())
        except json.JSONDecodeError:
            pass

    if code_block_match := re.search(r"```\s*([\s\S]*?)```", text):
        try:
            return json.loads(code_block_match[1].strip())
        except json.JSONDecodeError:
            pass

    obj_index = text.find("{")
    arr_index = text.find("[")
    if arr_index != -1 and (obj_index == -1 or arr_index < obj_index):
        if json_arr := _extract_balanced_json(text, "[", "]"):
            try:
                return json.loads(json_arr)
            except json.JSONDecodeError:
                pass

    if json_obj := _extract_balanced_json(text, "{", "}"):
        try:
            return json.loads(json_obj)
        except json.JSONDecodeError:
            pass

    if arr_index != -1 and (obj_index != -1 and arr_index > obj_index):
        if json_arr := _extract_balanced_json(text, "[", "]"):
            try:
                return json.loads(json_arr)
            except json.JSONDecodeError:
                pass

    # Strategy 6: Last resort - find anything that looks like JSON
    # This handles cases where JSON is embedded in explanatory text
    patterns = [
        r'(\{[\s\S]*"[^"]+"\s*:[\s\S]*\})',  # Object with at least one key
        r"(\[[\s\S]*\{[\s\S]*\}[\s\S]*\])",  # Array of objects
    ]

    for pattern in patterns:
        if match := re.search(pattern, text):
            try:
                return json.loads(match[1])
            except json.JSONDecodeError:
                continue

    return None


def _extract_balanced_json(text: str, open_char: str, close_char: str) -> str | None:
    """
    Extract a balanced JSON structure from text.

    Handles nested braces/brackets correctly.

    Args:
        text: The text to search
        open_char: Opening character ('{' or '[')
        close_char: Closing character ('}' or ']')

    Returns:
        The extracted JSON string or None
    """
    start = text.find(open_char)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def extract_json_with_key(text: str | None, required_key: str) -> dict[str, Any] | None:
    """
    Extract JSON from text, ensuring it contains a required key.

    Useful when you know the response should contain a specific key
    like "recommendations" or "results".

    Args:
        text: The raw text response (None returns None)
        required_key: Key that must be present in the extracted JSON

    Returns:
        Parsed JSON dict containing the key, or None
    """
    if not text or not isinstance(text, str):
        return None

    result = extract_json(text)

    if isinstance(result, dict) and required_key in result:
        return result

    # If extraction failed or key missing, try finding JSON with that key
    # Note: This fallback is rarely triggered because extract_json is thorough,
    # and the greedy regex usually matches more than the valid JSON object.
    pattern = rf'(\{{[\s\S]*"{re.escape(required_key)}"[\s\S]*\}})'
    match = re.search(pattern, text)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and required_key in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    return None
