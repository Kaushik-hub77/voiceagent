"""
Safety validation rules for LLM outputs
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass

from app.core.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SafetyViolation:
    """Represents a safety violation"""
    rule_name: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    matched_content: str
    suggestion: str


class SafetyValidator:
    """Validates content for safety and appropriateness"""

    def __init__(self):
        self.violations = []

        # Define safety rules
        self._setup_safety_rules()

    def _setup_safety_rules(self):
        """Setup safety validation rules"""

        # Profanity and offensive language
        self.profanity_patterns = [
            r'\b(?:damn|hell|crap|shit|fuck|asshole|bastard|bitch)\b',
            r'\b(?:motherfucker|motherfucking|cocksucker|dickhead|pussy)\b',
            # Add more patterns as needed
        ]

        # Hate speech patterns
        self.hate_speech_patterns = [
            r'\b(?:nigger|chink|spic|wetback|sandnigger)\b',
            r'\b(?:fag|queer|tranny|homo)\b',  # Note: "queer" can be reclaimed, but often used offensively
            # Add more patterns as needed
        ]

        # Harmful content patterns
        self.harmful_patterns = [
            r'\b(?:kill|murder|suicide|self-harm|harm)\b.*\b(?:yourself|themselves)\b',
            r'\b(?:bomb|explosive|weapon)\b.*\b(?:make|build|create)\b',
            r'\b(?:drugs?|narcotics?|heroin|cocaine|meth)\b.*\b(?:make|produce|synthesize)\b',
        ]

        # Personal information patterns
        self.pii_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
            r'\b\d{3}[-]\d{2}[-]\d{4}\b',      # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4} \d{4} \d{4} \d{4}\b',    # Credit card
        ]

        # Sensitive topics that might need review
        self.sensitive_topics = [
            "violence", "abuse", "trauma", "death", "illness",
            "politics", "religion", "sexuality", "gender"
        ]

    async def validate_text(self, text: str) -> Optional[str]:
        """
        Validate text for safety violations

        Args:
            text: Text to validate

        Returns:
            Clean text if safe, None if violations found
        """

        if not text or not text.strip():
            return text

        violations = await self._check_violations(text)

        if violations:
            # Log violations
            for violation in violations:
                logger.warning(
                    "Safety violation detected",
                    rule=violation.rule_name,
                    severity=violation.severity,
                    description=violation.description
                )

            # Check if any critical violations
            critical_violations = [v for v in violations if v.severity == "critical"]
            if critical_violations:
                logger.error("Critical safety violation, blocking content")
                return None

            # For non-critical violations, attempt to clean
            cleaned_text = await self._clean_violations(text, violations)
            return cleaned_text

        return text

    async def _check_violations(self, text: str) -> List[SafetyViolation]:
        """Check text for safety violations"""

        violations = []
        lower_text = text.lower()

        # Check profanity
        for pattern in self.profanity_patterns:
            matches = re.findall(pattern, lower_text, re.IGNORECASE)
            if matches:
                violations.append(SafetyViolation(
                    rule_name="profanity",
                    severity="medium",
                    description="Contains profane language",
                    matched_content=", ".join(matches),
                    suggestion="Replace with appropriate language"
                ))

        # Check hate speech
        for pattern in self.hate_speech_patterns:
            matches = re.findall(pattern, lower_text, re.IGNORECASE)
            if matches:
                violations.append(SafetyViolation(
                    rule_name="hate_speech",
                    severity="critical",
                    description="Contains hate speech or discriminatory language",
                    matched_content=", ".join(matches),
                    suggestion="Remove discriminatory content"
                ))

        # Check harmful content
        for pattern in self.harmful_patterns:
            if re.search(pattern, lower_text, re.IGNORECASE):
                match = re.search(pattern, lower_text, re.IGNORECASE)
                violations.append(SafetyViolation(
                    rule_name="harmful_content",
                    severity="critical",
                    description="Contains instructions for harmful activities",
                    matched_content=match.group() if match else "",
                    suggestion="Remove harmful instructions"
                ))

        # Check PII
        for pattern in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                violations.append(SafetyViolation(
                    rule_name="pii",
                    severity="high",
                    description="Contains personal identifiable information",
                    matched_content="[REDACTED]",
                    suggestion="Remove personal information"
                ))

        # Check sensitive topics (warning only)
        for topic in self.sensitive_topics:
            if topic in lower_text:
                violations.append(SafetyViolation(
                    rule_name="sensitive_topic",
                    severity="low",
                    description=f"Contains sensitive topic: {topic}",
                    matched_content=topic,
                    suggestion="Review content for appropriateness"
                ))

        return violations

    async def _clean_violations(
        self,
        text: str,
        violations: List[SafetyViolation]
    ) -> str:
        """Attempt to clean violations from text"""

        cleaned_text = text

        for violation in violations:
            if violation.severity in ["low", "medium"]:
                # For less severe violations, try to replace
                if violation.rule_name == "profanity":
                    # Simple replacement - in production, use better methods
                    cleaned_text = re.sub(
                        r'\b(?:damn|hell|crap)\b',
                        "***",
                        cleaned_text,
                        flags=re.IGNORECASE
                    )

        return cleaned_text

    async def validate_batch(self, texts: List[str]) -> List[Optional[str]]:
        """Validate a batch of texts"""
        results = []
        for text in texts:
            result = await self.validate_text(text)
            results.append(result)
        return results

    def get_violation_summary(self) -> Dict[str, int]:
        """Get summary of violations found"""
        summary = {}
        for violation in self.violations:
            summary[violation.rule_name] = summary.get(violation.rule_name, 0) + 1
        return summary
