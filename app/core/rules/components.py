from app.models.result import CheckResult, Severity

POWER_NET_NAMES = {"VCC", "3V3", "5V", "VBAT", "VDD"}
IC_REF_PREFIXES = {"U", "IC"}
CAP_REF_PREFIX  = "C"


def check_decoupling_capacitors(netlist):
    results = []
    net_by_name = {n.name.upper(): n for n in netlist.nets}

    for comp in netlist.components:
        is_ic = any(comp.ref.startswith(p) for p in IC_REF_PREFIXES)
        if not is_ic:
            continue

        # find which power nets this IC is on
        ic_power_nets = []
        for net in netlist.nets:
            if net.name.upper() in POWER_NET_NAMES:
                if any(p.ref == comp.ref for p in net.pins):
                    ic_power_nets.append(net.name.upper())

        if not ic_power_nets:
            continue  # IC has no power pin we recognise, skip

        for power_net in ic_power_nets:
            net = net_by_name.get(power_net)
            if not net:
                continue

            has_cap = any(
                p.ref.startswith(CAP_REF_PREFIX)
                for p in net.pins
            )

            if has_cap:
                results.append(CheckResult(
                    check_id  = "decoupling_capacitor",
                    severity  = Severity.WARNING,
                    passed    = True,
                    message   = f"{comp.ref} has a decoupling capacitor on {power_net}.",
                    component = comp.ref,
                    net       = power_net,
                ))
            else:
                results.append(CheckResult(
                    check_id   = "decoupling_capacitor",
                    severity   = Severity.WARNING,
                    passed     = False,
                    message    = f"{comp.ref} has no decoupling capacitor on net {power_net}.",
                    component  = comp.ref,
                    net        = power_net,
                    suggestion = f"Add a 100nF capacitor between {power_net} and GND near {comp.ref}.",
                ))

    if not results:
        results.append(CheckResult(
            check_id = "decoupling_capacitor",
            severity = Severity.WARNING,
            passed   = True,
            message  = "No ICs found to check for decoupling capacitors.",
        ))

    return results


def check_footprint_consistency(netlist):
    results = []
    rules = {
        "R": "Resistor_SMD",
        "C": "Capacitor_SMD",
        "L": "Inductor_SMD",
    }

    for comp in netlist.components:
        for prefix, expected in rules.items():
            if comp.ref.startswith(prefix) and comp.footprint:
                if expected not in comp.footprint:
                    results.append(CheckResult(
                        check_id   = "footprint_consistency",
                        severity   = Severity.INFO,
                        passed     = False,
                        message    = f"{comp.ref} has footprint '{comp.footprint}' which doesn't match expected family '{expected}'.",
                        component  = comp.ref,
                        suggestion = f"Verify {comp.ref}'s footprint is correct for its value ({comp.value}).",
                    ))
                else:
                    results.append(CheckResult(
                        check_id  = "footprint_consistency",
                        severity  = Severity.INFO,
                        passed    = True,
                        message   = f"{comp.ref} footprint looks correct.",
                        component = comp.ref,
                    ))

    if not results:
        results.append(CheckResult(
            check_id = "footprint_consistency",
            severity = Severity.INFO,
            passed   = True,
            message  = "No passive components found to check.",
        ))

    return results