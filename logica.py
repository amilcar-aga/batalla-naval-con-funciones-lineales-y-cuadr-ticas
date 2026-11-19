"""Reglas del juego (sin nada de interfaz).

El tablero es un plano cartesiano con coordenadas enteras de -10 a 10 en ambos ejes.
Cada barco ocupa casillas (x, y). Una casilla es un cuadrado de 1x1 centrado en (x, y).
Un disparo (la gráfica de la función) impacta una casilla si la curva atraviesa
el INTERIOR de ese cuadrado (rozar solo un borde o esquina no cuenta).
"""
from funciones import valor

GRID_MIN, GRID_MAX = -10, 10
FLOTA = [3, 2, 2, 1, 1]          # tamaños de los barcos de cada jugador
EPS = 1e-9


# -------------------------------------------------------------- colocación
def celdas_barco(x, y, tam, horizontal):
    """Casillas de un barco cuyo extremo inicial está en (x, y)."""
    return [(x + i, y) if horizontal else (x, y + i) for i in range(tam)]


def en_tablero(c):
    return GRID_MIN <= c[0] <= GRID_MAX and GRID_MIN <= c[1] <= GRID_MAX


def colocacion_valida(celdas, ocupadas):
    return all(en_tablero(c) and c not in ocupadas for c in celdas)


# ---------------------------------------------------------------- impactos
def _rango_en_intervalo(coefs, x0, x1):
    """Mínimo y máximo exactos de a*x^2+b*x+c en [x0, x1]."""
    a, b, _ = coefs
    xs = [x0, x1]
    if abs(a) > 1e-12:
        vertice = -b / (2 * a)
        if x0 < vertice < x1:
            xs.append(vertice)
    ys = [valor(coefs, x) for x in xs]
    return min(ys), max(ys)


def curva_toca_celda(coefs, cx, cy):
    ymin, ymax = _rango_en_intervalo(coefs, cx - 0.5, cx + 0.5)
    return ymax > cy - 0.5 + EPS and ymin < cy + 0.5 - EPS


# ------------------------------------------------------------------ estado
class Jugador:
    def __init__(self, nombre, barcos):
        self.nombre = nombre
        self.barcos = [list(b) for b in barcos]   # lista de barcos, cada uno lista de casillas
        self.recibidos = set()                    # casillas propias ya destruidas
        self.curvas = []                          # funciones que ha disparado

    @property
    def celdas(self):
        return {c for b in self.barcos for c in b}

    def barco_hundido(self, barco):
        return all(c in self.recibidos for c in barco)

    @property
    def hundidos(self):
        return sum(self.barco_hundido(b) for b in self.barcos)

    @property
    def derrotado(self):
        return self.celdas <= self.recibidos


class Partida:
    def __init__(self, j1, j2):
        self.jugadores = [j1, j2]
        self.turno = 0
        self.num_disparos = 0
        self.ganador = None      # índice del ganador cuando termina

    @property
    def atacante(self):
        return self.jugadores[self.turno]

    @property
    def rival(self):
        return self.jugadores[1 - self.turno]

    def disparar(self, coefs):
        """Aplica un disparo. Devuelve (casillas_impactadas, tamaños_de_barcos_hundidos).

        Si impacta, el mismo jugador conserva el turno; si falla, pasa al rival.
        """
        rival = self.rival
        hundidos_antes = {i for i, b in enumerate(rival.barcos) if rival.barco_hundido(b)}
        impactos = [c for c in sorted(rival.celdas - rival.recibidos)
                    if curva_toca_celda(coefs, *c)]
        rival.recibidos.update(impactos)
        self.atacante.curvas.append(coefs)
        self.num_disparos += 1
        nuevos = [len(b) for i, b in enumerate(rival.barcos)
                  if i not in hundidos_antes and rival.barco_hundido(b)]
        if rival.derrotado:
            self.ganador = self.turno
        elif not impactos:
            self.turno = 1 - self.turno
        return impactos, nuevos
