"""
Robust JSON parsing helpers for LLM responses.

LLMs sometimes wrap JSON in markdown fences or add preamble text.
These helpers extract the first JSON object/array and parse it safely.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


class LLMJSONParseError(ValueError):
    """Raised when we cannot parse expected JSON from an LLM response."""


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences from text."""
    t = (text or "").strip()
    if not t:
        return ""
    
    # Remove ```json ... ``` or ``` ... ``` or ```JSON ... ```
    if t.startswith("```"):
        # Drop first fence line (handles ```json, ```JSON, or just ```)
        lines = t.splitlines()
        if len(lines) >= 2:
            # remove opening fence
            first_line = lines[0].strip()
            if first_line.lower().startswith("```json") or first_line == "```":
                lines = lines[1:]
            # remove closing fence if present as last line
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            t = "\n".join(lines).strip()
    
    return t


def _try_repair_json(text: str) -> Optional[str]:
    """
    Attempt to repair common JSON issues in LLM responses.
    
    Returns repaired JSON string or None if repair not possible.
    """
    if not text:
        return None
    
    # Try to fix trailing commas (common LLM error)
    # Match patterns like: , ] or , }
    text = re.sub(r',(\s*[\]}])', r'\1', text)
    
    # Try to fix missing closing braces/brackets (if truncated response)
    # Count opening and closing braces
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    
    # Add missing closers (only if reasonable - max 3 missing)
    if open_braces > close_braces and (open_braces - close_braces) <= 3:
        text = text + ('}' * (open_braces - close_braces))
    if open_brackets > close_brackets and (open_brackets - close_brackets) <= 3:
        text = text + (']' * (open_brackets - close_brackets))
    
    return text


def extract_first_json(text: str) -> str:
    """
    Extract the first top-level JSON object/array substring from text.
    Works even if the response has preamble/epilogue text.
    """
    t = _strip_code_fences(text)
    if not t:
        return ""

    # Find first '{' or '['
    start_obj = t.find("{")
    start_arr = t.find("[")
    if start_obj == -1 and start_arr == -1:
        return ""
    start = min([i for i in (start_obj, start_arr) if i != -1])

    opener = t[start]
    closer = "}" if opener == "{" else "]"

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "\"":
                in_str = False
            continue
        else:
            if ch == "\"":
                in_str = True
                continue
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return t[start : i + 1].strip()
    
    # If we reach here, JSON might be incomplete/truncated
    # Return what we have
    return t[start:].strip()


def parse_llm_json(text: str, *, default: Optional[Any] = None) -> Any:
    """
    Parse JSON from an LLM response, tolerating code fences and extra text.

    Enhanced with repair attempts for common LLM JSON errors.
    """
    candidate = extract_first_json(text)
    if not candidate:
        # Try to find JSON-like content even if extract_first_json fails
        text_lower = (text or "").lower()
        if "{" in text_lower or "[" in text_lower:
            # Try a more aggressive extraction
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
            matches = re.findall(json_pattern, text, re.DOTALL)
            if matches:
                candidate = matches[0]
        if not candidate:
            if default is not None:
                return default
            raise LLMJSONParseError("No JSON object/array found in LLM response")

    # Try parsing as-is first
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        # Attempt repair
        repaired = _try_repair_json(candidate)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass  # Fall through to error handling

        # Try additional repair strategies
        try:
            # Remove any trailing commas before closing braces/brackets
            cleaned = re.sub(r',\s*([}\]])', r'\1', candidate)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        try:
            # Try to fix unterminated strings
            if candidate.count('"') % 2 != 0:
                # Add closing quote if needed
                cleaned = candidate.rstrip() + '"'
                return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # If default provided, return it
        if default is not None:
            return default

        # Otherwise raise with helpful context
        raise LLMJSONParseError(
            f"Failed to parse JSON: {e}. "
            f"Text starts with: {candidate[:200]}..."
        ) from e


