from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer


EMPLOYEE_ID_PATTERN = r"(?<![\w-])EMP-[0-9]{5}(?![\w-])"


class EmployeeIdRecognizer(PatternRecognizer):
    """Cadence's uppercase EMP-five-ASCII-digit identifier, adapted from prototype."""

    def __init__(self) -> None:
        super().__init__(
            supported_entity="EMPLOYEE_ID",
            name="CadenceEmployeeIdRecognizer",
            patterns=[Pattern("cadence_employee_id", EMPLOYEE_ID_PATTERN, 0.95)],
            context=["employee", "staff", "personnel"],
            supported_language="en",
            global_regex_flags=re.MULTILINE,
        )
