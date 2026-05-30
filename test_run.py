from app.core.parser import parse
from app.core.rules.power import check_power_net_presence

nl = parse("tests/fixtures/sample.net")
result = check_power_net_presence(nl)

status = "PASS" if result.passed else "FAIL"
print(f"\n[{status}] {result.check_id}")
print(f"  severity : {result.severity.value}")
print(f"  message  : {result.message}")
if result.suggestion:
    print(f"  fix      : {result.suggestion}")