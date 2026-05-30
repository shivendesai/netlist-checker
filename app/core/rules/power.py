from app.models.result import CheckResult, Severity

POWER_NET_NAMES = {"VCC", "3V3", "5V", "VBAT", "VDD"}
GND_NET_NAMES   = {"GND", "AGND", "DGND", "PGND"}


def check_power_net_presence(netlist):
    net_names = {n.name.upper() for n in netlist.nets}

    has_power = bool(net_names & {n.upper() for n in POWER_NET_NAMES})
    has_gnd   = bool(net_names & {n.upper() for n in GND_NET_NAMES})

    if has_power and has_gnd:
        return CheckResult(
            check_id  = "power_net_presence",
            severity  = Severity.ERROR,
            passed    = True,
            message   = "Power and GND nets found.",
        )

    missing = []
    if not has_power:
        missing.append("a VCC/3V3/5V power net")
    if not has_gnd:
        missing.append("a GND net")

    return CheckResult(
        check_id   = "power_net_presence",
        severity   = Severity.ERROR,
        passed     = False,
        message    = f"Design is missing {' and '.join(missing)}.",
        suggestion = "Add power and ground symbols to your schematic and re-export the netlist.",
    )