from app.models.result import CheckReport, Severity
from app.core.rules.power import check_power_net_presence
from app.core.rules.nets import check_parse_integrity, check_net_stubs
from app.core.rules.spi import check_spi_bus_completeness, check_spi_pin_assignment
from app.core.rules.components import check_decoupling_capacitors, check_footprint_consistency

SEVERITY_SYMBOL = {
    Severity.ERROR:   "✖",
    Severity.WARNING: "⚠",
    Severity.INFO:    "ℹ",
}


def run_checks(netlist, source_file="unknown"):
    results = []

    # single-result checks
    for fn in [
        check_parse_integrity,
        check_power_net_presence,
        check_net_stubs,
    ]:
        out = fn(netlist)
        if isinstance(out, list):
            results.extend(out)
        else:
            results.append(out)

    # multi-result checks
    for fn in [
        check_spi_bus_completeness,
        check_spi_pin_assignment,
        check_decoupling_capacitors,
        check_footprint_consistency,
    ]:
        results.extend(fn(netlist))

    return CheckReport(source_file=source_file, results=results)


def print_report(report):
    total    = len(report.results)
    failures = [r for r in report.results if not r.passed]
    passing  = total - len(failures)

    print(f"\n{'═' * 60}")
    print(f"  Netlist checker — {report.source_file}")
    print(f"{'═' * 60}")
    print(f"  {total} checks  |  {passing} passed  |  {report.error_count} errors  |  {report.warning_count} warnings")
    print(f"{'─' * 60}")

    for r in report.results:
        sym    = SEVERITY_SYMBOL[r.severity]
        status = "PASS" if r.passed else "FAIL"
        print(f"\n  {sym} [{status}] {r.check_id}")
        print(f"     {r.message}")
        if r.component:
            print(f"     component : {r.component}")
        if r.net:
            print(f"     net       : {r.net}")
        if r.suggestion:
            print(f"     fix       : {r.suggestion}")

    print(f"\n{'═' * 60}")
    overall = "✔  READY" if report.passed else "✖  NOT READY — fix errors before manufacturing"
    print(f"  {overall}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    import sys
    from app.core.parser import parse

    if len(sys.argv) < 2:
        print("Usage: python -m app.core.checker <path-to-netlist.net>")
        sys.exit(1)

    netlist = parse(sys.argv[1])
    report  = run_checks(netlist, source_file=sys.argv[1])
    print_report(report)