# Detector evaluation

Version: 1.1

Exact-span automated metrics and separate potential recall:

```json
{
  "overall": {
    "cases": 299,
    "gold_spans": 224,
    "raw_candidates": 486,
    "decisions": {
      "CONFIRM": 193,
      "REJECT": 251,
      "REVIEW": 42
    },
    "rates": {
      "CONFIRM": 0.39711934156378603,
      "REJECT": 0.5164609053497943,
      "REVIEW": 0.08641975308641975
    },
    "duplicate_candidates": 0,
    "tp": 189,
    "fp": 4,
    "fn": 35,
    "precision": 0.9792746113989638,
    "recall": 0.84375,
    "f1": 0.906474820143885,
    "potential_recall": 0.90625,
    "review_true_spans": 14,
    "review_false_spans": 28,
    "per_entity": {
      "EMAIL_ADDRESS": {
        "tp": 42,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "potential_recall": 1.0,
        "review_true_spans": 0,
        "review_false_spans": 0
      },
      "EMPLOYEE_ID": {
        "tp": 28,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "potential_recall": 1.0,
        "review_true_spans": 0,
        "review_false_spans": 0
      },
      "PERSON": {
        "tp": 91,
        "fp": 0,
        "fn": 21,
        "precision": 1.0,
        "recall": 0.8125,
        "f1": 0.896551724137931,
        "potential_recall": 0.8125,
        "review_true_spans": 0,
        "review_false_spans": 1
      },
      "PHONE_NUMBER": {
        "tp": 14,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "potential_recall": 1.0,
        "review_true_spans": 0,
        "review_false_spans": 0
      },
      "US_BANK_NUMBER": {
        "tp": 0,
        "fp": 0,
        "fn": 14,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "potential_recall": 1.0,
        "review_true_spans": 14,
        "review_false_spans": 4
      },
      "US_DRIVER_LICENSE": {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "potential_recall": 0.0,
        "review_true_spans": 0,
        "review_false_spans": 23
      },
      "US_PASSPORT": {
        "tp": 0,
        "fp": 4,
        "fn": 0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "potential_recall": 0.0,
        "review_true_spans": 0,
        "review_false_spans": 0
      },
      "US_SSN": {
        "tp": 14,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
        "potential_recall": 1.0,
        "review_true_spans": 0,
        "review_false_spans": 0
      }
    },
    "review_categories": {
      "context_sensitive_identifier": 41,
      "ambiguous_person": 1
    },
    "review_reasons": {
      "identifier_requires_contextual_review": 14,
      "identifier_without_supporting_context": 27,
      "person_requires_contextual_review": 1
    },
    "false_positive_categories": {
      "person": 0,
      "header": 0,
      "title_name": 0,
      "email": 0,
      "phone": 0,
      "employee": 0,
      "table": 0,
      "adjacent_email": 0,
      "duplicate_context": 0,
      "ocr_name": 0,
      "malformed_employee": 0,
      "malformed_email": 0,
      "numeric_business": 4,
      "code": 0,
      "account": 0,
      "department": 0,
      "committee": 0,
      "organization": 0,
      "role": 0,
      "business": 0,
      "abbreviation": 0,
      "ambiguous_capitals": 0,
      "footer": 0,
      "address": 0,
      "date": 0,
      "project": 0,
      "ssn": 0
    },
    "false_negative_categories": {
      "person": 0,
      "header": 1,
      "title_name": 0,
      "email": 0,
      "phone": 0,
      "employee": 0,
      "table": 5,
      "adjacent_email": 1,
      "duplicate_context": 0,
      "ocr_name": 14,
      "malformed_employee": 0,
      "malformed_email": 0,
      "numeric_business": 0,
      "code": 0,
      "account": 14,
      "department": 0,
      "committee": 0,
      "organization": 0,
      "role": 0,
      "business": 0,
      "abbreviation": 0,
      "ambiguous_capitals": 0,
      "footer": 0,
      "address": 0,
      "date": 0,
      "project": 0,
      "ssn": 0
    }
  },
  "splits": {
    "development": {
      "cases": 299,
      "gold_spans": 224,
      "raw_candidates": 486,
      "decisions": {
        "CONFIRM": 193,
        "REJECT": 251,
        "REVIEW": 42
      },
      "rates": {
        "CONFIRM": 0.39711934156378603,
        "REJECT": 0.5164609053497943,
        "REVIEW": 0.08641975308641975
      },
      "duplicate_candidates": 0,
      "tp": 189,
      "fp": 4,
      "fn": 35,
      "precision": 0.9792746113989638,
      "recall": 0.84375,
      "f1": 0.906474820143885,
      "potential_recall": 0.90625,
      "review_true_spans": 14,
      "review_false_spans": 28,
      "per_entity": {
        "EMAIL_ADDRESS": {
          "tp": 42,
          "fp": 0,
          "fn": 0,
          "precision": 1.0,
          "recall": 1.0,
          "f1": 1.0,
          "potential_recall": 1.0,
          "review_true_spans": 0,
          "review_false_spans": 0
        },
        "EMPLOYEE_ID": {
          "tp": 28,
          "fp": 0,
          "fn": 0,
          "precision": 1.0,
          "recall": 1.0,
          "f1": 1.0,
          "potential_recall": 1.0,
          "review_true_spans": 0,
          "review_false_spans": 0
        },
        "PERSON": {
          "tp": 91,
          "fp": 0,
          "fn": 21,
          "precision": 1.0,
          "recall": 0.8125,
          "f1": 0.896551724137931,
          "potential_recall": 0.8125,
          "review_true_spans": 0,
          "review_false_spans": 1
        },
        "PHONE_NUMBER": {
          "tp": 14,
          "fp": 0,
          "fn": 0,
          "precision": 1.0,
          "recall": 1.0,
          "f1": 1.0,
          "potential_recall": 1.0,
          "review_true_spans": 0,
          "review_false_spans": 0
        },
        "US_BANK_NUMBER": {
          "tp": 0,
          "fp": 0,
          "fn": 14,
          "precision": 0.0,
          "recall": 0.0,
          "f1": 0.0,
          "potential_recall": 1.0,
          "review_true_spans": 14,
          "review_false_spans": 4
        },
        "US_DRIVER_LICENSE": {
          "tp": 0,
          "fp": 0,
          "fn": 0,
          "precision": 0.0,
          "recall": 0.0,
          "f1": 0.0,
          "potential_recall": 0.0,
          "review_true_spans": 0,
          "review_false_spans": 23
        },
        "US_PASSPORT": {
          "tp": 0,
          "fp": 4,
          "fn": 0,
          "precision": 0.0,
          "recall": 0.0,
          "f1": 0.0,
          "potential_recall": 0.0,
          "review_true_spans": 0,
          "review_false_spans": 0
        },
        "US_SSN": {
          "tp": 14,
          "fp": 0,
          "fn": 0,
          "precision": 1.0,
          "recall": 1.0,
          "f1": 1.0,
          "potential_recall": 1.0,
          "review_true_spans": 0,
          "review_false_spans": 0
        }
      },
      "review_categories": {
        "context_sensitive_identifier": 41,
        "ambiguous_person": 1
      },
      "review_reasons": {
        "identifier_requires_contextual_review": 14,
        "identifier_without_supporting_context": 27,
        "person_requires_contextual_review": 1
      },
      "false_positive_categories": {
        "person": 0,
        "header": 0,
        "title_name": 0,
        "email": 0,
        "phone": 0,
        "employee": 0,
        "table": 0,
        "adjacent_email": 0,
        "duplicate_context": 0,
        "ocr_name": 0,
        "malformed_employee": 0,
        "malformed_email": 0,
        "numeric_business": 4,
        "code": 0,
        "account": 0,
        "department": 0,
        "committee": 0,
        "organization": 0,
        "role": 0,
        "business": 0,
        "abbreviation": 0,
        "ambiguous_capitals": 0,
        "footer": 0,
        "address": 0,
        "date": 0,
        "project": 0,
        "ssn": 0
      },
      "false_negative_categories": {
        "person": 0,
        "header": 1,
        "title_name": 0,
        "email": 0,
        "phone": 0,
        "employee": 0,
        "table": 5,
        "adjacent_email": 1,
        "duplicate_context": 0,
        "ocr_name": 14,
        "malformed_employee": 0,
        "malformed_email": 0,
        "numeric_business": 0,
        "code": 0,
        "account": 14,
        "department": 0,
        "committee": 0,
        "organization": 0,
        "role": 0,
        "business": 0,
        "abbreviation": 0,
        "ambiguous_capitals": 0,
        "footer": 0,
        "address": 0,
        "date": 0,
        "project": 0,
        "ssn": 0
      }
    },
    "heldout": {
      "cases": 0,
      "gold_spans": 0,
      "raw_candidates": 0,
      "decisions": {},
      "rates": {
        "CONFIRM": 0,
        "REJECT": 0,
        "REVIEW": 0
      },
      "duplicate_candidates": 0,
      "tp": 0,
      "fp": 0,
      "fn": 0,
      "precision": 0.0,
      "recall": 0.0,
      "f1": 0.0,
      "potential_recall": 0.0,
      "review_true_spans": 0,
      "review_false_spans": 0,
      "per_entity": {},
      "review_categories": {},
      "review_reasons": {},
      "false_positive_categories": {},
      "false_negative_categories": {}
    }
  },
  "detector_policy_version": "1.1",
  "dataset_sha256": "64e04ecbea502af76dffb1b3bb348717c5d9ffda1b664e4854ea7844462ecd4a",
  "elapsed_seconds": 2.671735900003114,
  "default_score_threshold": 0
}
```
