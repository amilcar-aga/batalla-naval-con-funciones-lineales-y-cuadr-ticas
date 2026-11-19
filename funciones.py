"""Parser seguro de funciones lineales y cuadráticas.

No usa eval(). Convierte el texto escrito por el jugador en coeficientes
(a, b, c) de la función  y = a*x^2 + b*x + c  y rechaza todo lo demás.

Ejemplos válidos:  2x+1   y = x^2 - 4x + 3   -0.5x^2 + 2   (x+1)(x-2)   3(x-1)^2
"""
import re

GRADO_MAX = 2


class FuncionError(ValueError):
    """Error de sintaxis o de tipo de función (con mensaje para el jugador)."""


# ---------------------------------------------------------------- polinomios
# Un polinomio es una lista [c0, c1, c2, ...] (término independiente primero).

def _trim(p):
    while len(p) > 1 and abs(p[-1]) < 1e-12:
        p.pop()
    return p


def _check(p):
    if len(p) - 1 > GRADO_MAX:
        raise FuncionError("Solo se permiten funciones lineales o cuadráticas (grado máximo 2).")
    return p


def _add(p, q):
    n = max(len(p), len(q))
    r = [(p[i] if i < len(p) else 0.0) + (q[i] if i < len(q) else 0.0) for i in range(n)]
    return _trim(r)


def _neg(p):
    return [-c for c in p]


def _mul(p, q):
    r = [0.0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            r[i + j] += a * b
    return _check(_trim(r))


def _pow(base, exp):
    if len(exp) > 1:
        raise FuncionError("El exponente debe ser un número, no puede contener x.")
    n = exp[0]
    if abs(n - round(n)) > 1e-9 or n < 0:
        raise FuncionError("El exponente debe ser un entero mayor o igual a 0.")
    n = int(round(n))
    try:
        if len(base) == 1:
            if n > 200:
                raise FuncionError("El exponente es demasiado grande.")
            return [float(base[0]) ** n]
    except OverflowError:
        raise FuncionError("El número es demasiado grande.")
    if n * (len(base) - 1) > GRADO_MAX:
        raise FuncionError("Solo se permiten funciones lineales o cuadráticas (grado máximo 2).")
    r = [1.0]
    for _ in range(n):
        r = _mul(r, base)
    return r


# ------------------------------------------------------------------- lexer
def _tokenizar(s):
    tokens, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch.isdigit() or ch == ".":
            j = i
            while j < len(s) and (s[j].isdigit() or s[j] == "."):
                j += 1
            try:
                tokens.append(("num", float(s[i:j])))
            except ValueError:
                raise FuncionError(f"Número inválido: '{s[i:j]}'")
            i = j
        elif ch == "x":
            tokens.append(("x", None))
            i += 1
        elif ch in "+-*/^()":
            tokens.append(("op", ch))
            i += 1
        else:
            raise FuncionError(f"Carácter no permitido: '{ch}'")
    return tokens


# ------------------------------------------------------------------ parser
class _Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def es_op(self, ch):
        tok = self.peek()
        return tok is not None and tok[0] == "op" and tok[1] == ch

    def expr(self):
        p = self.term()
        while self.es_op("+") or self.es_op("-"):
            op = self.next()[1]
            q = self.term()
            p = _add(p, q) if op == "+" else _add(p, _neg(q))
        return p

    def term(self):
        p = self.unary()
        while True:
            tok = self.peek()
            if self.es_op("*"):
                self.next()
                p = _mul(p, self.unary())
            elif self.es_op("/"):
                self.next()
                q = self.unary()
                if len(q) > 1:
                    raise FuncionError("No se puede dividir entre una expresión con x.")
                if abs(q[0]) < 1e-12:
                    raise FuncionError("División entre cero.")
                p = [c / q[0] for c in p]
            elif tok is not None and (tok[0] == "x" or tok == ("op", "(")):
                p = _mul(p, self.unary())  # multiplicación implícita: 2x, 3(x+1)
            else:
                break
        return _trim(p)

    def unary(self):
        if self.es_op("-"):
            self.next()
            return _neg(self.unary())
        if self.es_op("+"):
            self.next()
            return self.unary()
        return self.potencia()

    def potencia(self):
        base = self.atomo()
        if self.es_op("^"):
            self.next()
            base = _pow(base, self.unary())
        return base

    def atomo(self):
        tok = self.next()
        if tok is None:
            raise FuncionError("La expresión está incompleta.")
        if tok[0] == "num":
            return [tok[1]]
        if tok[0] == "x":
            return [0.0, 1.0]
        if tok == ("op", "("):
            p = self.expr()
            if not self.es_op(")"):
                raise FuncionError("Falta cerrar un paréntesis.")
            self.next()
            return p
        raise FuncionError(f"Símbolo inesperado: '{tok[1]}'")


# --------------------------------------------------------------- API pública
def parsear_funcion(texto):
    """Devuelve (a, b, c) tal que y = a*x^2 + b*x + c. Lanza FuncionError si no es válida."""
    s = re.sub(r"\s+", "", texto.lower()).replace("**", "^").replace(",", ".")
    if "=" in s:
        izq, der = s.split("=", 1)
        if izq not in ("y", "f(x)"):
            raise FuncionError("Escribe solo la función, por ejemplo: y = 2x + 1")
        s = der
    if not s:
        raise FuncionError("Escribe una función.")
    parser = _Parser(_tokenizar(s))
    poly = parser.expr()
    if parser.peek() is not None:
        raise FuncionError("Expresión no válida. Revisa los operadores y paréntesis.")
    poly = poly + [0.0] * (3 - len(poly))
    coefs = tuple(round(c, 9) + 0.0 for c in (poly[2], poly[1], poly[0]))
    if any(abs(c) > 1e9 for c in coefs):
        raise FuncionError("Los coeficientes son demasiado grandes.")
    return coefs


def valor(coefs, x):
    a, b, c = coefs
    return a * x * x + b * x + c


def formatear(coefs):
    """Texto legible de la función, p. ej. 'y = x^2 - 3x + 1'."""
    out = ""
    for coef, var in zip(coefs, ("x^2", "x", "")):
        if abs(coef) < 1e-12:
            continue
        mag = abs(coef)
        cuerpo = var if (var and abs(mag - 1) < 1e-12) else f"{mag:g}{var}"
        if not out:
            out = ("-" if coef < 0 else "") + cuerpo
        else:
            out += f" {'-' if coef < 0 else '+'} {cuerpo}"
    return "y = " + (out or "0")
