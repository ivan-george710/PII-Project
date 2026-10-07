from .models import DetectedPII


# Entity types that are currently relevant to the Cadence PII policy.
PII_ENTITY_TYPES = {
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "EMPLOYEE_ID",
    "US_SSN",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
    "US_ITIN",
    "US_BANK_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "MEDICAL_LICENSE",
}


def validate_detection(detection: DetectedPII) -> tuple[bool, str]:
    """
    Decide whether a Presidio candidate should be treated
    as confirmed PII.
    """

    if detection.entity_type not in PII_ENTITY_TYPES:
        return False, "entity_type_not_in_pii_policy"

    return True, "accepted"