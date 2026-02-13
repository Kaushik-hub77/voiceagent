"""
JSON validation utilities for LLM structured outputs
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from jsonschema import validate, ValidationError, SchemaError
import re

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


class JSONValidator:
    """Validates JSON outputs from LLMs"""

    def __init__(self):
        self.schemas = self._load_default_schemas()

    def _load_default_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load default JSON schemas"""

        return {
            "draft_assistance_response": {
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["general", "grammar", "style", "content"]},
                                "description": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "category": {"type": "string"}
                            },
                            "required": ["description"]
                        }
                    },
                    "improved_content": {"type": "string"},
                    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                },
                "required": ["suggestions", "improved_content", "confidence_score"]
            },

            "bias_checker_response": {
                "type": "object",
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "bias_type": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "description": {"type": "string"},
                                "context": {"type": "string"},
                                "suggestion": {"type": "string"}
                            },
                            "required": ["bias_type", "description"]
                        }
                    },
                    "overall_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "summary": {"type": "string"}
                },
                "required": ["issues", "overall_score"]
            },

            "review_summarizer_response": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "improvements": {"type": "array", "items": {"type": "string"}},
                    "overall_sentiment": {"type": "string", "enum": ["positive", "negative", "neutral", "mixed"]},
                    "sentiment_score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "key_themes": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["summary", "overall_sentiment"]
            }
        }

    def validate_json_string(
        self,
        json_string: str,
        schema_name: Optional[str] = None,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a JSON string against a schema

        Args:
            json_string: JSON string to validate
            schema_name: Name of predefined schema to use
            custom_schema: Custom JSON schema to validate against

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """

        try:
            # Parse JSON
            data = json.loads(json_string)

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {str(e)}"
            logger.warning("JSON parsing failed", error=error_msg)
            return False, None, error_msg

        # Validate against schema
        if custom_schema or schema_name:
            schema = custom_schema or self.schemas.get(schema_name)

            if schema:
                try:
                    validate(instance=data, schema=schema)
                    logger.debug("JSON schema validation passed", schema=schema_name)
                except (ValidationError, SchemaError) as e:
                    error_msg = f"Schema validation failed: {str(e)}"
                    logger.warning("JSON schema validation failed", error=error_msg)
                    return False, data, error_msg

        return True, data, None

    def extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON from LLM response text

        Args:
            text: Raw text that may contain JSON

        Returns:
            Extracted JSON string or None
        """

        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find JSON between curly braces (simple approach)
        brace_count = 0
        start_idx = -1

        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    json_candidate = text[start_idx:i+1]
                    # Quick validation
                    try:
                        json.loads(json_candidate)
                        return json_candidate
                    except json.JSONDecodeError:
                        continue

        return None

    def repair_json(self, json_string: str) -> Optional[str]:
        """
        Attempt to repair common JSON issues

        Args:
            json_string: Potentially malformed JSON string

        Returns:
            Repaired JSON string or None if unrepairable
        """

        try:
            # Try parsing as-is first
            json.loads(json_string)
            return json_string

        except json.JSONDecodeError:
            # Attempt simple repairs
            repaired = json_string.strip()

            # Fix trailing commas
            repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

            # Fix missing quotes around keys (basic)
            repaired = re.sub(r'(\w+):', r'"\1":', repaired)

            # Try parsing again
            try:
                json.loads(repaired)
                logger.debug("JSON repair successful")
                return repaired
            except json.JSONDecodeError:
                logger.warning("JSON repair failed")
                return None

    def validate_and_extract(
        self,
        text: str,
        schema_name: Optional[str] = None,
        custom_schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract JSON from text and validate it

        Args:
            text: Raw text containing JSON
            schema_name: Name of schema to validate against
            custom_schema: Custom schema for validation

        Returns:
            Tuple of (is_valid, parsed_data, error_message)
        """

        # Extract JSON from text
        json_string = self.extract_json_from_text(text)

        if not json_string:
            return False, None, "No JSON found in response"

        # Try to repair if needed
        is_valid, data, error = self.validate_json_string(
            json_string, schema_name, custom_schema
        )

        if not is_valid and error and "Invalid JSON" in error:
            # Try to repair
            repaired_json = self.repair_json(json_string)
            if repaired_json:
                is_valid, data, error = self.validate_json_string(
                    repaired_json, schema_name, custom_schema
                )

        return is_valid, data, error

    def add_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Add a custom schema"""
        self.schemas[name] = schema
        logger.info("Schema added", schema_name=name)

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a schema by name"""
        return self.schemas.get(name)
