from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Pin:
    ref: str
    number: str


@dataclass
class Net:
    code: str
    name: str
    pins: list = field(default_factory=list)


@dataclass
class Component:
    ref: str
    value: str
    footprint: str


@dataclass
class Netlist:
    components: list = field(default_factory=list)
    nets: list = field(default_factory=list)

    def component(self, ref):
        return next((c for c in self.components if c.ref == ref), None)

    def net(self, name):
        return next((n for n in self.nets if n.name == name), None)

    def nets_for_ref(self, ref):
        return [n for n in self.nets if any(p.ref == ref for p in n.pins)]


def _tokenise(text):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in (' ', '\t', '\r', '\n'):
            i += 1
        elif ch == '(':
            tokens.append('(')
            i += 1
        elif ch == ')':
            tokens.append(')')
            i += 1
        elif ch == '"':
            i += 1
            j = i
            while j < n and text[j] != '"':
                j += 1
            tokens.append(text[i:j])
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in (' ', '\t', '\r', '\n', '(', ')'):
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def _build_tree(tokens):
    stack = []
    current = []
    for tok in tokens:
        if tok == '(':
            stack.append(current)
            current = []
        elif tok == ')':
            finished = current
            current = stack.pop()
            current.append(finished)
        else:
            current.append(tok)
    return current


def _find(node, key):
    for child in node:
        if isinstance(child, list) and child and child[0] == key:
            return child
    return None


def _find_all(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def parse(source):
    if isinstance(source, Path) or (isinstance(source, str) and '\n' not in source):
        text = Path(source).read_text(encoding='utf-8')
    else:
        text = source

    tokens = _tokenise(text)
    tree   = _build_tree(tokens)
    root   = tree[0]  # the 'export' node

    components = []
    components_node = _find(root, 'components')
    if components_node:
        for comp in _find_all(components_node, 'comp'):
            ref_n = _find(comp, 'ref')
            val_n = _find(comp, 'value')
            fp_n  = _find(comp, 'footprint')
            components.append(Component(
                ref       = ref_n[1] if ref_n and len(ref_n) > 1 else '?',
                value     = val_n[1] if val_n and len(val_n) > 1 else '?',
                footprint = fp_n[1]  if fp_n  and len(fp_n)  > 1 else '',
            ))

    nets = []
    nets_node = _find(root, 'nets')
    if nets_node:
        for net in _find_all(nets_node, 'net'):
            code_n = _find(net, 'code')
            name_n = _find(net, 'name')
            pins = []
            for node in _find_all(net, 'node'):
                r = _find(node, 'ref')
                p = _find(node, 'pin')
                if r and p:
                    pins.append(Pin(ref=r[1], number=p[1]))
            nets.append(Net(
                code  = code_n[1] if code_n and len(code_n) > 1 else '?',
                name  = name_n[1] if name_n and len(name_n) > 1 else '?',
                pins  = pins,
            ))

    return Netlist(components=components, nets=nets)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.core.parser <path-to-netlist.net>")
        sys.exit(1)

    nl = parse(sys.argv[1])
    print(f"\n{'REF':<10} {'VALUE':<20} FOOTPRINT")
    print('-' * 60)
    for c in sorted(nl.components, key=lambda x: x.ref):
        print(f"{c.ref:<10} {c.value:<20} {c.footprint}")
    print(f"\n{len(nl.components)} components, {len(nl.nets)} nets total.")