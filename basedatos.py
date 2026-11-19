"""Almacenamiento con SQLite (módulo estándar de Python, no requiere instalar nada).

Tablas:
  partidas  -> una fila por partida (jugadores, fechas, ganador, nº de disparos)
  barcos    -> coordenadas de cada casilla de cada barco elegidas al inicio
  disparos  -> cada función escrita, quién la escribió y qué casillas impactó
"""
import sqlite3
from datetime import datetime
from pathlib import Path


class BaseDatos:
    def __init__(self, ruta):
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(ruta)
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS partidas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                jugador1  TEXT NOT NULL,
                jugador2  TEXT NOT NULL,
                inicio    TEXT NOT NULL,
                fin       TEXT,
                ganador   TEXT,
                disparos  INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS barcos (
                partida_id INTEGER NOT NULL REFERENCES partidas(id),
                jugador    INTEGER NOT NULL,      -- 0 = jugador1, 1 = jugador2
                barco      INTEGER NOT NULL,      -- índice del barco dentro de su flota
                x          INTEGER NOT NULL,
                y          INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS disparos (
                partida_id INTEGER NOT NULL REFERENCES partidas(id),
                nro        INTEGER NOT NULL,
                jugador    INTEGER NOT NULL,
                expresion  TEXT NOT NULL,
                funcion    TEXT NOT NULL,         -- forma normalizada, p. ej. y = x^2 - 3
                impactos   TEXT NOT NULL          -- "x,y;x,y" (vacío si falló)
            );
        """)
        self.con.commit()

    # ------------------------------------------------------------ escritura
    def crear_partida(self, nombres, barcos_por_jugador):
        """Guarda la partida y las posiciones iniciales. Devuelve el id."""
        cur = self.con.execute(
            "INSERT INTO partidas (jugador1, jugador2, inicio) VALUES (?, ?, ?)",
            (nombres[0], nombres[1], datetime.now().isoformat(timespec="seconds")))
        pid = cur.lastrowid
        filas = [(pid, j, bi, x, y)
                 for j, barcos in enumerate(barcos_por_jugador)
                 for bi, barco in enumerate(barcos)
                 for (x, y) in barco]
        self.con.executemany("INSERT INTO barcos VALUES (?, ?, ?, ?, ?)", filas)
        self.con.commit()
        return pid

    def guardar_disparo(self, partida_id, nro, jugador, expresion, funcion, impactos):
        self.con.execute(
            "INSERT INTO disparos VALUES (?, ?, ?, ?, ?, ?)",
            (partida_id, nro, jugador, expresion, funcion,
             ";".join(f"{x},{y}" for x, y in impactos)))
        self.con.execute("UPDATE partidas SET disparos = ? WHERE id = ?", (nro, partida_id))
        self.con.commit()

    def finalizar_partida(self, partida_id, ganador, total_disparos):
        self.con.execute(
            "UPDATE partidas SET fin = ?, ganador = ?, disparos = ? WHERE id = ?",
            (datetime.now().isoformat(timespec="seconds"), ganador, total_disparos, partida_id))
        self.con.commit()

    # -------------------------------------------------------------- lectura
    def historial(self, limite=100):
        return self.con.execute(
            "SELECT * FROM partidas ORDER BY id DESC LIMIT ?", (limite,)).fetchall()

    def posiciones(self, partida_id):
        """{jugador: {barco: [(x, y), ...]}}"""
        res = {0: {}, 1: {}}
        for f in self.con.execute(
                "SELECT jugador, barco, x, y FROM barcos WHERE partida_id = ? "
                "ORDER BY jugador, barco, rowid", (partida_id,)):
            res[f["jugador"]].setdefault(f["barco"], []).append((f["x"], f["y"]))
        return res

    def disparos(self, partida_id):
        return self.con.execute(
            "SELECT * FROM disparos WHERE partida_id = ? ORDER BY nro", (partida_id,)).fetchall()

    def cerrar(self):
        self.con.close()
