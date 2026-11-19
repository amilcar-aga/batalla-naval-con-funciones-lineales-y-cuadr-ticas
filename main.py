"""Batalla Funcional - interfaz Pygame (dos jugadores en el mismo equipo, por turnos).

Ejecutar:  python main.py
"""

import sys
from functools import lru_cache
from pathlib import Path

import pygame

from funciones import parsear_funcion, formatear, valor, FuncionError
from logica import (GRID_MIN, GRID_MAX, FLOTA, celdas_barco, colocacion_valida,
                    en_tablero, Jugador, Partida)
from basedatos import BaseDatos

# ----------------------------------------------------------------- constantes
W, H = 1100, 720
CELL = 32
N = GRID_MAX - GRID_MIN + 1            # 21 casillas por lado
GRID_PX = N * CELL                     # 672
GX, GY = 30, 24                        # esquina superior izquierda del tablero
OX, OY = GX + GRID_PX // 2, GY + GRID_PX // 2   # píxel del origen (0, 0)
GRID_RECT = pygame.Rect(GX, GY, GRID_PX, GRID_PX)
PX = GX + GRID_PX + 30                 # inicio del panel derecho
PW = W - PX - 24

BG, PANEL, GRID = (12, 19, 33), (20, 30, 50), (34, 50, 76)
AXIS, TXT, DIM = (110, 140, 185), (225, 232, 245), (130, 145, 170)
ACC, GOOD, BAD = (255, 206, 84), (80, 200, 140), (235, 80, 80)
OLD, BTN, BTN_H = (70, 95, 140), (38, 58, 92), (56, 84, 130)

PERMITIDOS = set("0123456789xyf+-*/^().,= ")
MAX_EXPR = 40


# ------------------------------------------------------------------- helpers
def celda_centro(cx, cy):
    return OX + cx * CELL, OY - cy * CELL


def celda_rect(cx, cy):
    x, y = celda_centro(cx, cy)
    return pygame.Rect(x - CELL // 2, y - CELL // 2, CELL, CELL)


def pantalla_a_celda(pos):
    if not GRID_RECT.collidepoint(pos):
        return None
    c = (round((pos[0] - OX) / CELL), round((OY - pos[1]) / CELL))
    return c if en_tablero(c) else None


@lru_cache(maxsize=256)
def puntos_curva(coefs):
    """Puntos en pantalla de la curva, x en [-10.5, 10.5]."""
    pts = []
    for i in range(421):
        x = -10.5 + i * 0.05
        py = OY - valor(coefs, x) * CELL
        pts.append((OX + x * CELL, max(-5000.0, min(5000.0, py))))
    return pts


def texto(surf, s, font, color, pos, anchor="topleft"):
    img = font.render(s, True, color)
    r = img.get_rect(**{anchor: pos})
    surf.blit(img, r)
    return r


def parrafo(surf, s, font, color, x, y, ancho, interlineado=4):
    """Texto con salto de línea automático. Devuelve la y siguiente."""
    linea = ""
    for palabra in s.split(" "):
        prueba = (linea + " " + palabra).strip()
        if font.size(prueba)[0] > ancho and linea:
            texto(surf, linea, font, color, (x, y))
            y += font.get_height() + interlineado
            linea = palabra
        else:
            linea = prueba
    if linea:
        texto(surf, linea, font, color, (x, y))
        y += font.get_height() + interlineado
    return y


def boton(surf, rect, s, font, activo=True):
    hover = activo and rect.collidepoint(pygame.mouse.get_pos())
    col = (BTN_H if hover else BTN) if activo else (28, 36, 52)
    pygame.draw.rect(surf, col, rect, border_radius=10)
    pygame.draw.rect(surf, AXIS if activo else GRID, rect, 2, border_radius=10)
    texto(surf, s, font, TXT if activo else DIM, rect.center, "center")


def clic(e, rect):
    return e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and rect.collidepoint(e.pos)


# rectángulos de botones / campos
BTN_MENU = [pygame.Rect(W // 2 - 160, 300 + i * 78, 320, 56) for i in range(3)]
CAMPOS = [pygame.Rect(W // 2 - 220, 270 + i * 100, 440, 50) for i in range(2)]
BTN_COMENZAR = pygame.Rect(W // 2 - 140, 490, 280, 56)
BTN_DESHACER = pygame.Rect(PX, 600, 160, 48)
BTN_CONFIRMAR = pygame.Rect(PX + 176, 600, PW - 176, 48)
BTN_FIN = [pygame.Rect(W // 2 - 160, 430 + i * 72, 320, 54) for i in range(2)]


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Batalla Funcional")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        fuente = "arial,dejavusans,liberationsans"
        self.f_titulo = pygame.font.SysFont(fuente, 52, bold=True)
        self.f_grande = pygame.font.SysFont(fuente, 30, bold=True)
        self.f = pygame.font.SysFont(fuente, 20)
        self.f_peq = pygame.font.SysFont(fuente, 16)
        self.f_mini = pygame.font.SysFont(fuente, 12)
        self.f_mono = pygame.font.SysFont("consolas,dejavusansmono,couriernew,monospace", 26)
        self.db = BaseDatos(Path(__file__).parent / "datos" / "batalla.db")

        self.state = "MENU"
        self.nombres = ["", ""]
        self.campo = 0
        # colocación
        self.colocando = 0
        self.flotas = [None, None]
        self.barcos = []
        self.horizontal = True
        # partida
        self.partida = None
        self.game_id = None
        self.texto = ""
        self.error = ""
        self.shooter = 0
        self.coefs_actual = None
        self.impactos = []
        self.mensajes = []
        self.anim = 0.0
        # historial
        self.hist = []
        self.hist_sel = None
        self.hist_scroll = 0

        self.ev = {"MENU": self.ev_menu, "NAMES": self.ev_names, "COVER_PLACE": self.ev_cover,
                   "PLACE": self.ev_place, "COVER_TURN": self.ev_cover, "INPUT": self.ev_input,
                   "ANIM": self.ev_anim, "RESULT": self.ev_result, "GAMEOVER": self.ev_gameover,
                   "HISTORY": self.ev_history}
        self.dib = {"MENU": self.dib_menu, "NAMES": self.dib_names, "COVER_PLACE": self.dib_cover,
                    "PLACE": self.dib_place, "COVER_TURN": self.dib_cover, "INPUT": self.dib_juego,
                    "ANIM": self.dib_juego, "RESULT": self.dib_juego,
                    "GAMEOVER": self.dib_gameover, "HISTORY": self.dib_history}

    # ------------------------------------------------------------ bucle
    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.salir()
                self.ev[self.state](e)
            if self.state == "ANIM":
                self.anim += dt / 1.2
                if self.anim >= 1.0:
                    self.state = "RESULT"
            self.dib[self.state]()
            pygame.display.flip()

    def salir(self):
        self.db.cerrar()
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------ dibujo común
    def dibujar_cuadricula(self):
        s = self.screen
        pygame.draw.rect(s, PANEL, GRID_RECT)
        for k in range(N + 1):
            pygame.draw.line(s, GRID, (GX + k * CELL, GY), (GX + k * CELL, GY + GRID_PX))
            pygame.draw.line(s, GRID, (GX, GY + k * CELL), (GX + GRID_PX, GY + k * CELL))
        pygame.draw.line(s, AXIS, (OX, GY), (OX, GY + GRID_PX), 2)
        pygame.draw.line(s, AXIS, (GX, OY), (GX + GRID_PX, OY), 2)
        for v in range(GRID_MIN, GRID_MAX + 1):
            if v == 0:
                texto(s, "0", self.f_mini, DIM, (OX - 4, OY + 3), "topright")
                continue
            cx, _ = celda_centro(v, 0)
            texto(s, str(v), self.f_mini, DIM, (cx, OY + 3), "midtop")
            _, cy = celda_centro(0, v)
            texto(s, str(v), self.f_mini, DIM, (OX - 4, cy), "midright")
        pygame.draw.rect(s, AXIS, GRID_RECT, 2)

    def dibujar_curva(self, coefs, color, ancho, frac=1.0):
        pts = puntos_curva(coefs)
        n = max(2, int(len(pts) * frac))
        self.screen.set_clip(GRID_RECT)
        pygame.draw.lines(self.screen, color, False, pts[:n], ancho)
        self.screen.set_clip(None)

    def dibujar_barco_celda(self, c, color=GOOD):
        pygame.draw.rect(self.screen, color, celda_rect(*c).inflate(-6, -6), border_radius=6)

    def dibujar_impacto(self, c, resaltar=False):
        r = celda_rect(*c).inflate(-6, -6)
        pygame.draw.rect(self.screen, BAD, r, border_radius=6)
        pygame.draw.line(self.screen, TXT, r.topleft, r.bottomright, 3)
        pygame.draw.line(self.screen, TXT, r.topright, r.bottomleft, 3)
        if resaltar:
            pygame.draw.rect(self.screen, ACC, r.inflate(6, 6), 3, border_radius=8)

    def mini_tablero(self, x0, y0, jugador, cs=7):
        s = self.screen
        lado = N * cs
        pygame.draw.rect(s, PANEL, (x0, y0, lado, lado))
        pygame.draw.line(s, GRID, (x0 + lado // 2, y0), (x0 + lado // 2, y0 + lado))
        pygame.draw.line(s, GRID, (x0, y0 + lado // 2), (x0 + lado, y0 + lado // 2))
        for (cx, cy) in jugador.celdas:
            px, py = x0 + (cx - GRID_MIN) * cs, y0 + (GRID_MAX - cy) * cs
            col = BAD if (cx, cy) in jugador.recibidos else GOOD
            pygame.draw.rect(s, col, (px, py, cs - 1, cs - 1))
        pygame.draw.rect(s, AXIS, (x0, y0, lado, lado), 1)

    # ------------------------------------------------------------- MENÚ
    def ev_menu(self, e):
        if clic(e, BTN_MENU[0]):
            self.nombres = ["", ""]
            self.campo = 0
            self.state = "NAMES"
        elif clic(e, BTN_MENU[1]):
            self.abrir_historial()
        elif clic(e, BTN_MENU[2]):
            self.salir()

    def dib_menu(self):
        self.screen.fill(BG)
        texto(self.screen, "BATALLA FUNCIONAL", self.f_titulo, ACC, (W // 2, 150), "center")
        texto(self.screen, "Hunde la flota rival con funciones lineales y cuadráticas",
              self.f, DIM, (W // 2, 215), "center")
        for r, s in zip(BTN_MENU, ["Nueva partida", "Historial", "Salir"]):
            boton(self.screen, r, s, self.f_grande)

    # ---------------------------------------------------------- NOMBRES
    def ev_names(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(CAMPOS):
                if r.collidepoint(e.pos):
                    self.campo = i
            if BTN_COMENZAR.collidepoint(e.pos):
                self.comenzar()
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.state = "MENU"
            elif e.key == pygame.K_TAB:
                self.campo = 1 - self.campo
            elif e.key == pygame.K_RETURN:
                if self.campo == 0:
                    self.campo = 1
                else:
                    self.comenzar()
            elif e.key == pygame.K_BACKSPACE:
                self.nombres[self.campo] = self.nombres[self.campo][:-1]
            elif e.unicode and e.unicode.isprintable() and len(self.nombres[self.campo]) < 14:
                self.nombres[self.campo] += e.unicode

    def comenzar(self):
        for i in range(2):
            self.nombres[i] = self.nombres[i].strip() or f"Jugador {i + 1}"
        if self.nombres[0].lower() == self.nombres[1].lower():
            self.nombres[1] += " (2)"
        self.colocando = 0
        self.flotas = [None, None]
        self.state = "COVER_PLACE"

    def dib_names(self):
        self.screen.fill(BG)
        texto(self.screen, "Nombres de los jugadores", self.f_grande, TXT, (W // 2, 170), "center")
        for i, r in enumerate(CAMPOS):
            texto(self.screen, f"Jugador {i + 1}", self.f_peq, DIM, (r.x, r.y - 24))
            pygame.draw.rect(self.screen, PANEL, r, border_radius=8)
            pygame.draw.rect(self.screen, ACC if i == self.campo else GRID, r, 2, border_radius=8)
            cursor = "|" if (i == self.campo and pygame.time.get_ticks() // 500 % 2 == 0) else ""
            if self.nombres[i] or cursor:
                texto(self.screen, self.nombres[i] + cursor, self.f_grande, TXT,
                      (r.x + 14, r.centery), "midleft")
            else:
                texto(self.screen, f"Jugador {i + 1}", self.f_grande, GRID, (r.x + 14, r.centery), "midleft")
        boton(self.screen, BTN_COMENZAR, "Comenzar", self.f_grande)
        texto(self.screen, "TAB cambia de campo  ·  ESC vuelve al menú", self.f_peq, DIM,
              (W // 2, 590), "center")

    # ------------------------------------------------------------ PANTALLAS DE CAMBIO
    def ev_cover(self, e):
        if (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN) or \
                (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            if self.state == "COVER_PLACE":
                self.barcos = []
                self.horizontal = True
                self.state = "PLACE"
            else:
                self.texto, self.error = "", ""
                self.state = "INPUT"

    def dib_cover(self):
        self.screen.fill(BG)
        if self.state == "COVER_PLACE":
            nombre = self.nombres[self.colocando]
            otro = self.nombres[1 - self.colocando]
            texto(self.screen, nombre, self.f_titulo, ACC, (W // 2, 240), "center")
            texto(self.screen, "coloca tu flota en secreto", self.f_grande, TXT, (W // 2, 310), "center")
            texto(self.screen, f"{otro}, mira hacia otro lado.", self.f, DIM, (W // 2, 370), "center")
        else:
            texto(self.screen, f"Turno de {self.partida.atacante.nombre}", self.f_titulo, ACC,
                  (W // 2, 260), "center")
            texto(self.screen, f"{self.partida.rival.nombre} no puede ver tu tablero.", self.f, DIM,
                  (W // 2, 330), "center")
        texto(self.screen, "Pulsa ENTER o haz clic para continuar", self.f, TXT, (W // 2, 480), "center")

    # -------------------------------------------------------- COLOCACIÓN
    def tam_actual(self):
        return FLOTA[len(self.barcos)] if len(self.barcos) < len(FLOTA) else 0

    def ev_place(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if BTN_DESHACER.collidepoint(e.pos):
                self.deshacer()
            elif BTN_CONFIRMAR.collidepoint(e.pos):
                self.confirmar_flota()
            else:
                c, tam = pantalla_a_celda(e.pos), self.tam_actual()
                if c and tam:
                    cells = celdas_barco(c[0], c[1], tam, self.horizontal)
                    if colocacion_valida(cells, {k for b in self.barcos for k in b}):
                        self.barcos.append(cells)
        elif (e.type == pygame.MOUSEBUTTONDOWN and e.button == 3) or e.type == pygame.MOUSEWHEEL:
            self.horizontal = not self.horizontal
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                self.horizontal = not self.horizontal
            elif e.key == pygame.K_BACKSPACE:
                self.deshacer()
            elif e.key == pygame.K_RETURN:
                self.confirmar_flota()

    def deshacer(self):
        if self.barcos:
            self.barcos.pop()

    def confirmar_flota(self):
        if len(self.barcos) < len(FLOTA):
            return
        self.flotas[self.colocando] = [list(b) for b in self.barcos]
        if self.colocando == 0:
            self.colocando = 1
            self.state = "COVER_PLACE"
        else:
            self.iniciar_partida()

    def iniciar_partida(self):
        j1 = Jugador(self.nombres[0], self.flotas[0])
        j2 = Jugador(self.nombres[1], self.flotas[1])
        self.partida = Partida(j1, j2)
        self.game_id = self.db.crear_partida(self.nombres, self.flotas)   # guarda las posiciones
        self.state = "COVER_TURN"

    def dib_place(self):
        s = self.screen
        s.fill(BG)
        self.dibujar_cuadricula()
        ocupadas = {c for b in self.barcos for c in b}
        for c in ocupadas:
            self.dibujar_barco_celda(c)
        cell, tam = pantalla_a_celda(pygame.mouse.get_pos()), self.tam_actual()
        if cell and tam:
            cells = celdas_barco(cell[0], cell[1], tam, self.horizontal)
            color = GOOD if colocacion_valida(cells, ocupadas) else BAD
            for c in cells:
                if en_tablero(c):
                    pygame.draw.rect(s, color, celda_rect(*c).inflate(-6, -6), 3, border_radius=6)
        # panel
        texto(s, self.nombres[self.colocando], self.f_grande, ACC, (PX, 28))
        texto(s, "coloca tu flota (el rival no debe mirar)", self.f_peq, DIM, (PX, 68))
        y = 110
        for i, t in enumerate(FLOTA):
            puesto = i < len(self.barcos)
            actual = i == len(self.barcos)
            col = GOOD if puesto else (ACC if actual else DIM)
            marca = "[x]" if puesto else ("[>]" if actual else "[ ]")
            texto(s, f"{marca} Barco {i + 1}: {t} casilla(s)", self.f, col, (PX, y))
            y += 30
        y += 14
        texto(s, "Orientación: " + ("horizontal" if self.horizontal else "vertical"), self.f, TXT, (PX, y))
        y += 34
        y = parrafo(s, "El barco crece desde la casilla marcada hacia la derecha (horizontal) "
                       "o hacia arriba (vertical).", self.f_peq, DIM, PX, y, PW)
        y += 8
        for linea in ["Clic izquierdo: colocar", "R / clic derecho / rueda: girar",
                      "Retroceso: deshacer · ENTER: confirmar"]:
            texto(s, linea, self.f_peq, DIM, (PX, y))
            y += 22
        if cell:
            texto(s, f"Casilla: ({cell[0]}, {cell[1]})", self.f, TXT, (PX, y + 14))
        boton(s, BTN_DESHACER, "Deshacer", self.f, activo=bool(self.barcos))
        boton(s, BTN_CONFIRMAR, "Confirmar flota", self.f, activo=len(self.barcos) == len(FLOTA))

    # ------------------------------------------------------------ JUEGO
    def ev_input(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_RETURN:
            self.enviar()
        elif e.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
        elif e.unicode and e.unicode.lower() in PERMITIDOS and len(self.texto) < MAX_EXPR:
            self.texto += e.unicode

    def enviar(self):
        try:
            coefs = parsear_funcion(self.texto)
        except FuncionError as ex:
            self.error = str(ex)
            return
        self.error = ""
        self.shooter = self.partida.turno
        rival = self.partida.rival
        impactos, hundidos = self.partida.disparar(coefs)
        self.coefs_actual, self.impactos = coefs, impactos
        self.db.guardar_disparo(self.game_id, self.partida.num_disparos, self.shooter,
                                self.texto, formatear(coefs), impactos)
        msgs = []
        if impactos:
            msgs.append((f"¡IMPACTO! {len(impactos)} casilla(s) destruida(s):", GOOD))
            msgs.append((" ".join(f"({x},{y})" for x, y in impactos), TXT))
            msgs += [(f"¡Barco de {t} casilla(s) hundido!", ACC) for t in hundidos]
            msgs.append(("¡FLOTA ENEMIGA DESTRUIDA!", ACC) if self.partida.ganador is not None
                        else ("Tienes otro disparo.", TXT))
        else:
            msgs.append(("Agua. No has alcanzado ningún barco.", BAD))
            msgs.append((f"Turno de {rival.nombre}.", TXT))
        self.mensajes = msgs
        self.texto = ""
        self.anim = 0.0
        self.state = "ANIM"

    def ev_anim(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
            self.state = "RESULT"

    def ev_result(self, e):
        if (e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN) or \
                (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            if self.partida.ganador is not None:
                self.db.finalizar_partida(self.game_id,
                                          self.partida.jugadores[self.partida.ganador].nombre,
                                          self.partida.num_disparos)
                self.state = "GAMEOVER"
            elif self.impactos:
                self.texto, self.error = "", ""
                self.state = "INPUT"
            else:
                self.state = "COVER_TURN"

    def dib_juego(self):
        s = self.screen
        s.fill(BG)
        tirador = self.shooter if self.state in ("ANIM", "RESULT") else self.partida.turno
        atacante = self.partida.jugadores[tirador]
        rival = self.partida.jugadores[1 - tirador]
        disparando = self.state in ("ANIM", "RESULT")

        self.dibujar_cuadricula()
        for c in (atacante.curvas[:-1] if disparando else atacante.curvas):
            self.dibujar_curva(c, OLD, 2)
        nuevos = set(self.impactos) if disparando else set()
        for c in rival.recibidos - nuevos:
            self.dibujar_impacto(c)
        if self.state == "ANIM":
            self.dibujar_curva(self.coefs_actual, ACC, 3, self.anim)
        elif self.state == "RESULT":
            self.dibujar_curva(self.coefs_actual, ACC, 3)
            for c in nuevos:
                self.dibujar_impacto(c, resaltar=True)

        # panel
        texto(s, f"Turno de {atacante.nombre}", self.f_grande, ACC, (PX, 24))
        y = 80
        if self.state == "INPUT":
            texto(s, "Escribe tu función y pulsa ENTER:", self.f, TXT, (PX, y))
            caja = pygame.Rect(PX, y + 32, PW, 48)
            pygame.draw.rect(s, PANEL, caja, border_radius=8)
            pygame.draw.rect(s, ACC, caja, 2, border_radius=8)
            cursor = "|" if pygame.time.get_ticks() // 500 % 2 == 0 else ""
            texto(s, "y = " + self.texto + cursor, self.f_mono, TXT, (caja.x + 12, caja.centery), "midleft")
            y = caja.bottom + 12
            if self.error:
                y = parrafo(s, self.error, self.f_peq, BAD, PX, y, PW)
            y += 6
            for linea in ["Lineales o cuadráticas. Ejemplos:", "  2x + 1", "  x^2 - 4x + 3",
                          "  -0.5x^2 + 2", "  (x+1)(x-2)"]:
                texto(s, linea, self.f_peq, DIM, (PX, y))
                y += 21
        else:
            texto(s, "Función disparada:", self.f, DIM, (PX, y))
            y = parrafo(s, formatear(self.coefs_actual), self.f_mono, ACC, PX, y + 28, PW)
            y += 10
            if self.state == "RESULT":
                for m, col in self.mensajes:
                    y = parrafo(s, m, self.f, col, PX, y, PW)
                texto(s, "Pulsa ENTER para continuar", self.f_peq, TXT, (PX, y + 12))
            else:
                texto(s, "Trazando gráfica...", self.f, DIM, (PX, y))

        total = len(rival.celdas)
        texto(s, f"Casillas enemigas destruidas: {len(rival.recibidos)}/{total}", self.f_peq, TXT, (PX, 440))
        texto(s, f"Barcos enemigos hundidos: {rival.hundidos}/{len(rival.barcos)}", self.f_peq, TXT, (PX, 464))
        texto(s, f"Disparos totales: {self.partida.num_disparos}", self.f_peq, DIM, (PX, 488))
        texto(s, "Tu flota (verde: a flote, rojo: destruido):", self.f_mini, DIM, (PX, 520))
        self.mini_tablero(PX, 540, atacante)

    # --------------------------------------------------------- FIN DE PARTIDA
    def ev_gameover(self, e):
        if clic(e, BTN_FIN[0]):
            self.state = "MENU"
        elif clic(e, BTN_FIN[1]):
            self.abrir_historial()

    def dib_gameover(self):
        s = self.screen
        s.fill(BG)
        g = self.partida.jugadores[self.partida.ganador]
        texto(s, "¡VICTORIA!", self.f_titulo, ACC, (W // 2, 190), "center")
        texto(s, f"{g.nombre} ha hundido toda la flota enemiga", self.f_grande, TXT, (W // 2, 270), "center")
        texto(s, f"Disparos totales: {self.partida.num_disparos}   ·   Partida guardada (#{self.game_id})",
              self.f, DIM, (W // 2, 330), "center")
        boton(s, BTN_FIN[0], "Menú principal", self.f_grande)
        boton(s, BTN_FIN[1], "Ver historial", self.f_grande)

    # ---------------------------------------------------------------- HISTORIAL
    def abrir_historial(self):
        self.hist = self.db.historial()
        self.hist_sel = self.hist[0]["id"] if self.hist else None
        self.hist_scroll = 0
        self.state = "HISTORY"

    def filas_historial(self):
        return [(pygame.Rect(30, 110 + i * 40, 640, 36), f)
                for i, f in enumerate(self.hist[self.hist_scroll:self.hist_scroll + 14])]

    def ev_history(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.state = "MENU"
        elif e.type == pygame.MOUSEWHEEL:
            self.hist_scroll = max(0, min(max(0, len(self.hist) - 14), self.hist_scroll - e.y))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, f in self.filas_historial():
                if r.collidepoint(e.pos):
                    self.hist_sel = f["id"]

    def dib_history(self):
        s = self.screen
        s.fill(BG)
        texto(s, "Historial de partidas", self.f_grande, ACC, (30, 30))
        texto(s, "Clic en una partida para ver sus posiciones · rueda: desplazar · ESC: volver",
              self.f_peq, DIM, (30, 74))
        if not self.hist:
            texto(s, "Todavía no hay partidas guardadas.", self.f, DIM, (30, 120))
            return
        for r, f in self.filas_historial():
            sel = f["id"] == self.hist_sel
            pygame.draw.rect(s, BTN_H if sel else PANEL, r, border_radius=6)
            ganador = f["ganador"] or "sin terminar"
            texto(s, f"#{f['id']}  {f['inicio'][:16].replace('T', ' ')}", self.f_peq, DIM, (r.x + 10, r.centery), "midleft")
            texto(s, f"{f['jugador1']} vs {f['jugador2']}", self.f_peq, TXT, (r.x + 190, r.centery), "midleft")
            texto(s, f"Gana: {ganador}", self.f_peq, GOOD if f["ganador"] else DIM, (r.x + 420, r.centery), "midleft")
            texto(s, f"{f['disparos']} disp.", self.f_peq, DIM, (r.right - 10, r.centery), "midright")
        if self.hist_sel is not None:
            self.dib_detalle(self.hist_sel)

    def dib_detalle(self, pid):
        s = self.screen
        fila = next(f for f in self.hist if f["id"] == pid)
        x, y = 700, 110
        pygame.draw.rect(s, PANEL, (x - 12, y - 10, W - x - 18, H - y - 20), border_radius=10)
        pos = self.db.posiciones(pid)
        for j, nombre in enumerate([fila["jugador1"], fila["jugador2"]]):
            texto(s, f"Flota de {nombre}", self.f, ACC, (x, y))
            y += 26
            for bi, celdas in pos[j].items():
                txt = f"Barco {bi + 1}: " + " ".join(f"({a},{b})" for a, b in celdas)
                y = parrafo(s, txt, self.f_peq, TXT, x, y, W - x - 40, 2)
            y += 8
        texto(s, "Últimos disparos", self.f, ACC, (x, y))
        y += 26
        for d in self.db.disparos(pid)[-8:]:
            quien = fila["jugador1"] if d["jugador"] == 0 else fila["jugador2"]
            n = len(d["impactos"].split(";")) if d["impactos"] else 0
            texto(s, f"{d['nro']}. {quien}: {d['funcion']}  ->  {n} impacto(s)", self.f_peq, DIM, (x, y))
            y += 20


if __name__ == "__main__":
    App().run()
