from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"


@dataclass
class CheckResult:
    check_id:   str
    severity:   Severity
    passed:     bool
    message:    str
    component:  str | None = None
    net:        str | None = None
    suggestion: str | None = None


@dataclass
class CheckReport:
    source_file: str
    results:     list

    @property
    def passed(self):
        return all(r.passed for r in self.results if r.severity == Severity.ERROR)

    @property
    def error_count(self):
        return sum(1 for r in self.results if r.severity == Severity.ERROR and not r.passed)

    @property
    def warning_count(self):
        return sum(1 for r in self.results if r.severity == Severity.WARNING and not r.passed)