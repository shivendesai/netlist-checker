from app.models.result import CheckResult, Severity


def check_parse_integrity(netlist):
    refs = {c.ref for c in netlist.components}
    bad = []

    for net in netlist.nets:
        for pin in net.pins:
            if pin.ref not in refs:
                bad.append((net.name, pin.ref))

    if bad:
        for net_name, ref in bad:
            return CheckResult(
                check_id   = "parse_integrity",
                severity   = Severity.ERROR,
                passed     = False,
                message    = f"Net '{net_name}' references '{ref}' which doesn't exist in components.",
                net        = net_name,
                component  = ref,
                suggestion = "Check for typos in reference designators in your schematic.",
            )

    return CheckResult(
        check_id = "parse_integrity",
        severity = Severity.ERROR,
        passed   = True,
        message  = "All net references point to valid components.",
    )


def check_net_stubs(netlist):
    results = []

    for net in netlist.nets:
        if len(net.pins) < 2:
            results.append(CheckResult(
                check_id   = "net_stub",
                severity   = Severity.WARNING,
                passed     = False,
                message    = f"Net '{net.name}' has only {len(net.pins)} connection — nothing is receiving this signal.",
                net        = net.name,
                component  = net.pins[0].ref if net.pins else None,
                suggestion = f"Connect '{net.name}' to its destination or remove it if unused.",
            ))

    if not results:
        results.append(CheckResult(
            check_id = "net_stub",
            severity = Severity.WARNING,
            passed   = True,
            message  = "All nets have at least 2 connections.",
        ))

    return results