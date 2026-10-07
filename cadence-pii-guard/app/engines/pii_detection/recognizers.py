from presidio_analyzer import Pattern, PatternRecognizer


class EmployeeIdRecognizer(PatternRecognizer):
    """
    Detects Cadence employee identifiers such as:
    EMP-38104
    EMP-40522
    """

    PATTERNS = [
        Pattern(
            name="cadence_employee_id",
            regex=r"\bEMP-\d{5}\b",
            score=0.95,
        )
    ]

    CONTEXT = [
        "employee",
        "employee id",
        "employee identifier",
        "staff",
        "personnel",
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="EMPLOYEE_ID",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
            name="CadenceEmployeeIdRecognizer",
        )