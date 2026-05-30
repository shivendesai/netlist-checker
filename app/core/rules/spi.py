from app.models.result import CheckResult, Severity

SPI_BUSES = ["SPI1", "SPI2", "SPI3"]
REQUIRED_SIGNALS = ["SCK", "MOSI", "MISO"]

# STM32F103 SPI1 pin mapping (from datasheet / CubeMX)
SPI1_PIN_MAP = {
    "SPI1_SCK":  "PA5",
    "SPI1_MOSI": "PA7",
    "SPI1_MISO": "PA6",
}


def check_spi_bus_completeness(netlist):
    net_names = {n.name.upper() for n in netlist.nets}
    results = []

    for bus in SPI_BUSES:
        bus_nets = [n for n in net_names if n.startswith(bus)]
        if not bus_nets:
            continue  # this bus isn't used, skip

        missing = []
        for signal in REQUIRED_SIGNALS:
            if f"{bus}_{signal}" not in net_names:
                missing.append(signal)

        if missing:
            results.append(CheckResult(
                check_id   = "spi_bus_completeness",
                severity   = Severity.WARNING,
                passed     = False,
                message    = f"{bus} bus is missing signals: {', '.join(missing)}.",
                suggestion = f"Add nets named {bus}_{'/ '.join(missing)} to your schematic.",
            ))
        else:
            results.append(CheckResult(
                check_id = "spi_bus_completeness",
                severity = Severity.WARNING,
                passed   = True,
                message  = f"{bus} bus has all required signals (SCK, MOSI, MISO).",
            ))

    if not results:
        results.append(CheckResult(
            check_id = "spi_bus_completeness",
            severity = Severity.INFO,
            passed   = True,
            message  = "No SPI buses found in design.",
        ))

    return results


def check_spi_pin_assignment(netlist):
    results = []
    net_by_name = {n.name: n for n in netlist.nets}

    for net_name, expected_pin in SPI1_PIN_MAP.items():
        if net_name not in net_by_name:
            continue  # net doesn't exist, spi_bus_completeness will catch it

        net = net_by_name[net_name]
        u1_pins = [p.number for p in net.pins if p.ref == "U1"]

        if not u1_pins:
            results.append(CheckResult(
                check_id  = "spi_pin_assignment",
                severity  = Severity.ERROR,
                passed    = False,
                message   = f"{net_name} exists but is not connected to U1.",
                component = "U1",
                net       = net_name,
                suggestion = f"Connect {net_name} to U1 pin {expected_pin}.",
            ))
        elif expected_pin not in u1_pins:
            results.append(CheckResult(
                check_id   = "spi_pin_assignment",
                severity   = Severity.ERROR,
                passed     = False,
                message    = f"{net_name} is on U1 pin {u1_pins[0]} but should be on {expected_pin}.",
                component  = "U1",
                net        = net_name,
                suggestion = f"Move {net_name} to U1 pin {expected_pin} in KiCad.",
            ))
        else:
            results.append(CheckResult(
                check_id  = "spi_pin_assignment",
                severity  = Severity.ERROR,
                passed    = True,
                message   = f"{net_name} correctly assigned to U1 pin {expected_pin}.",
                component = "U1",
                net       = net_name,
            ))

    if not results:
        results.append(CheckResult(
            check_id = "spi_pin_assignment",
            severity = Severity.INFO,
            passed   = True,
            message  = "No SPI1 nets found to check pin assignment.",
        ))

    return results