from dataclasses import dataclass
from typing import Literal

AccessLevelType = Literal[
    "ADMIN_ONLY",
    "EMPLOYEE_SHARED",
    "DEPARTMENT_ONLY",
    "GROUP_ONLY",
    "USER_SPECIFIC",
]

VALID_ACCESS_LEVELS: set[str] = {
    "ADMIN_ONLY",
    "EMPLOYEE_SHARED",
    "DEPARTMENT_ONLY",
    "GROUP_ONLY",
    "USER_SPECIFIC",
}

VALID_USER_STATUSES: set[str] = {
    "ACTIVE",
    "SUSPENDED",
    "DISABLED",
}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    matched_rule: str = "default_deny"

    def to_dict(self, include_detailed_reason: bool = False) -> dict:
        if include_detailed_reason:
            return {
                "allowed": self.allowed,
                "reason": self.reason,
                "matched_rule": self.matched_rule,
            }
        return {
            "allowed": self.allowed,
            "reason": "authorized" if self.allowed else "access_denied",
        }
