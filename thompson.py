"""
Laboratorio 4 - Teoria de la Computacion
Construccion de AFN por el algoritmo de Thompson a partir de una expresion
regular, dibujo del automata y simulacion sobre una cadena de entrada.

Autor: Diego (apoyo generado con Claude)
"""

from graphviz import Digraph

EPSILON = "\u03b5"  # ε

# ---------------------------------------------------------------------------
# 1. Preprocesamiento: tokenizacion + insercion de concatenacion explicita
# ---------------------------------------------------------------------------

def tokenize(regex: str):
    """Convierte el string de la regex en una lista de tokens, respetando
    escapes con '\\' para tratar operadores como literales."""
    tokens = []
    i = 0
    while i < len(regex):
        c = regex[i]
        if c == " ":
            i += 1
            continue
        if c == "\\":
            if i + 1 >= len(regex):
                raise ValueError("Escape invalido al final de la expresion")
            tokens.append(("LITERAL", regex[i + 1]))
            i += 2
            continue
        if c == EPSILON:
            tokens.append(("LITERAL", EPSILON))
            i += 1
            continue
        if regex[i:i + 3] == "eps":
            tokens.append(("LITERAL", EPSILON))
            i += 3
            continue
        if c in "()|*+?":
            tokens.append(("OP", c))
        else:
            tokens.append(("LITERAL", c))
        i += 1
    return tokens


def is_operand_end(tok):
    """True si un token puede aparecer justo antes de una concatenacion."""
    return tok[0] == "LITERAL" or tok == ("OP", ")") or tok[1] in "*+?"


def is_operand_start(tok):
    """True si un token puede aparecer justo despues de una concatenacion."""
    return tok[0] == "LITERAL" or tok == ("OP", "(")


def insert_concat(tokens):
    """Inserta el operador explicito '.' de concatenacion entre tokens
    donde la concatenacion esta implicita en la regex original."""
    out = []
    for idx, tok in enumerate(tokens):
        out.append(tok)
        if idx + 1 < len(tokens):
            nxt = tokens[idx + 1]
            if is_operand_end(tok) and is_operand_start(nxt):
                out.append(("OP", "."))
    return out


# ---------------------------------------------------------------------------
# 2. Shunting Yard: infix -> postfix
# ---------------------------------------------------------------------------

PRECEDENCE = {"|": 1, ".": 2, "*": 3, "+": 3, "?": 3}
UNARY_POSTFIX = {"*", "+", "?"}
RIGHT_ASSOC = set()  # todos los operadores usados aqui son left-assoc


def to_postfix(tokens):
    output = []
    stack = []
    for tok in tokens:
        kind, val = tok
        if kind == "LITERAL":
            output.append(tok)
        elif val == "(":
            stack.append(tok)
        elif val == ")":
            while stack and stack[-1][1] != "(":
                output.append(stack.pop())
            if not stack:
                raise ValueError("Parentesis desbalanceados")
            stack.pop()  # descarta '('
        else:  # operador
            while (stack and stack[-1][1] != "(" and
                   (PRECEDENCE[stack[-1][1]] > PRECEDENCE[val] or
                    (PRECEDENCE[stack[-1][1]] == PRECEDENCE[val] and val not in RIGHT_ASSOC))):
                output.append(stack.pop())
            stack.append(tok)
    while stack:
        if stack[-1][1] == "(":
            raise ValueError("Parentesis desbalanceados")
        output.append(stack.pop())
    return output


# ---------------------------------------------------------------------------
# 3. Arbol sintactico a partir del postfix
# ---------------------------------------------------------------------------

class Node:
    def __init__(self, kind, value=None, left=None, right=None):
        self.kind = kind      # 'LITERAL' | '.' | '|' | '*' | '+' | '?'
        self.value = value    # simbolo si es LITERAL
        self.left = left
        self.right = right

    def __repr__(self):
        if self.kind == "LITERAL":
            return f"'{self.value}'"
        if self.kind in UNARY_POSTFIX:
            return f"({self.left!r}{self.kind})"
        return f"({self.left!r} {self.kind} {self.right!r})"


def build_tree(postfix):
    stack = []
    for kind, val in postfix:
        if kind == "LITERAL":
            stack.append(Node("LITERAL", value=val))
        elif val in UNARY_POSTFIX:
            child = stack.pop()
            stack.append(Node(val, left=child))
        else:  # binario: '.' o '|'
            right = stack.pop()
            left = stack.pop()
            stack.append(Node(val, left=left, right=right))
    if len(stack) != 1:
        raise ValueError("Expresion regular malformada")
    return stack[0]


# ---------------------------------------------------------------------------
# 4. Construccion de Thompson: arbol -> fragmento de AFN
# ---------------------------------------------------------------------------

class NFAFragment:
    """Fragmento de AFN con un unico estado inicial y uno de aceptacion.
    transitions: dict state -> list[(symbol, dest_state)]"""

    def __init__(self):
        self.transitions = {}
        self.start = None
        self.accept = None

    def add_state(self, state):
        self.transitions.setdefault(state, [])

    def add_edge(self, src, symbol, dst):
        self.add_state(src)
        self.add_state(dst)
        self.transitions[src].append((symbol, dst))

    def states(self):
        return set(self.transitions.keys())

    def merge(self, other):
        for s, edges in other.transitions.items():
            self.transitions.setdefault(s, [])
            self.transitions[s].extend(edges)


_state_counter = [0]


def new_state():
    _state_counter[0] += 1
    return f"q{_state_counter[0]}"


def reset_state_counter():
    _state_counter[0] = 0


def thompson(node: Node) -> NFAFragment:
    frag = NFAFragment()

    if node.kind == "LITERAL":
        s0, s1 = new_state(), new_state()
        frag.add_edge(s0, node.value, s1)
        frag.start, frag.accept = s0, s1
        return frag

    if node.kind == ".":
        left = thompson(node.left)
        right = thompson(node.right)
        frag.merge(left)
        frag.merge(right)
        frag.add_edge(left.accept, EPSILON, right.start)
        frag.start, frag.accept = left.start, right.accept
        return frag

    if node.kind == "|":
        left = thompson(node.left)
        right = thompson(node.right)
        s0, s1 = new_state(), new_state()
        frag.merge(left)
        frag.merge(right)
        frag.add_edge(s0, EPSILON, left.start)
        frag.add_edge(s0, EPSILON, right.start)
        frag.add_edge(left.accept, EPSILON, s1)
        frag.add_edge(right.accept, EPSILON, s1)
        frag.start, frag.accept = s0, s1
        return frag

    if node.kind == "*":
        inner = thompson(node.left)
        s0, s1 = new_state(), new_state()
        frag.merge(inner)
        frag.add_edge(s0, EPSILON, inner.start)
        frag.add_edge(s0, EPSILON, s1)
        frag.add_edge(inner.accept, EPSILON, inner.start)
        frag.add_edge(inner.accept, EPSILON, s1)
        frag.start, frag.accept = s0, s1
        return frag

    if node.kind == "+":
        inner = thompson(node.left)
        s0, s1 = new_state(), new_state()
        frag.merge(inner)
        frag.add_edge(s0, EPSILON, inner.start)
        frag.add_edge(inner.accept, EPSILON, inner.start)
        frag.add_edge(inner.accept, EPSILON, s1)
        frag.start, frag.accept = s0, s1
        return frag

    if node.kind == "?":
        inner = thompson(node.left)
        s0, s1 = new_state(), new_state()
        frag.merge(inner)
        frag.add_edge(s0, EPSILON, inner.start)
        frag.add_edge(s0, EPSILON, s1)
        frag.add_edge(inner.accept, EPSILON, s1)
        frag.start, frag.accept = s0, s1
        return frag

    raise ValueError(f"Nodo desconocido: {node.kind}")


# ---------------------------------------------------------------------------
# 5. Simulacion del AFN (busqueda de estados via epsilon-clausura)
# ---------------------------------------------------------------------------

def epsilon_closure(frag: NFAFragment, states):
    stack = list(states)
    closure = set(states)
    while stack:
        s = stack.pop()
        for sym, dst in frag.transitions.get(s, []):
            if sym == EPSILON and dst not in closure:
                closure.add(dst)
                stack.append(dst)
    return closure


def simulate(frag: NFAFragment, w: str) -> bool:
    current = epsilon_closure(frag, {frag.start})
    for ch in w:
        nxt = set()
        for s in current:
            for sym, dst in frag.transitions.get(s, []):
                if sym == ch:
                    nxt.add(dst)
        current = epsilon_closure(frag, nxt)
        if not current:
            return False
    return frag.accept in current


# ---------------------------------------------------------------------------
# 6. Dibujo del AFN con graphviz
# ---------------------------------------------------------------------------

def draw_nfa(frag: NFAFragment, filename: str, regex_label: str = ""):
    dot = Digraph(format="png")
    dot.attr(rankdir="LR")
    if regex_label:
        dot.attr(label=f"AFN para: {regex_label}", labelloc="t", fontsize="16")

    dot.node("__start__", shape="point")  # flecha de entrada al inicial
    for state in frag.states():
        shape = "doublecircle" if state == frag.accept else "circle"
        dot.node(state, shape=shape)

    dot.edge("__start__", frag.start)

    for src, edges in frag.transitions.items():
        for sym, dst in edges:
            dot.edge(src, dst, label=sym)

    dot.render(filename, cleanup=True)
    return f"{filename}.png"


# ---------------------------------------------------------------------------
# 7. Pipeline completo: regex -> postfix -> arbol -> AFN
# ---------------------------------------------------------------------------

def regex_to_nfa(regex: str) -> NFAFragment:
    reset_state_counter()
    tokens = tokenize(regex)
    tokens = insert_concat(tokens)
    postfix = to_postfix(tokens)
    tree = build_tree(postfix)
    return thompson(tree)