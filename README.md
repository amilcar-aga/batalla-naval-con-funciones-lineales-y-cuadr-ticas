# Batalla Funcional

Batalla naval donde en lugar de elegir coordenadas escribes **funciones lineales o cuadráticas**.
Si la gráfica de tu función atraviesa una casilla con un barco, esa casilla queda destruida y juegas otra vez.

## Cómo ejecutar
```
pip install -r requirements.txt
python main.py
```
Pruebas del núcleo (sin ventana): `python test_nucleo.py`

## Reglas
- Tablero: plano cartesiano con enteros de **-10 a 10** en x e y.
- Flota de cada jugador: barcos de **3, 2, 2, 1 y 1** casillas (9 casillas en total).
- Colocación en secreto, uno tras otro (pantalla de cambio entre jugadores).
- Disparo: escribes `y = ...` (ej. `2x+1`, `x^2-4x+3`, `-0.5x^2+2`, `(x+1)(x-2)`). Grado máximo 2.
- Una casilla es un cuadrado de 1x1 centrado en (x, y). **Impacta si la curva atraviesa su interior**
  (rozar solo una esquina o borde no cuenta). Una sola función puede destruir varias casillas.
- Impacto -> sigues disparando. Agua -> turno del rival. Gana quien destruya toda la flota enemiga.

## Archivos
| Archivo | Contenido |
|---|---|
| `main.py` | Interfaz Pygame y flujo de pantallas |
| `logica.py` | Reglas: flota, colocación, detección de impactos, turnos |
| `funciones.py` | Parser seguro (sin `eval`) de las funciones escritas |
| `basedatos.py` | SQLite: posiciones iniciales, disparos e historial |
| `test_nucleo.py` | Pruebas automáticas del núcleo |

## Datos guardados (`datos/batalla.db`, SQLite)
- `partidas`: jugadores, fecha de inicio/fin, ganador, número de disparos.
- `barcos`: coordenadas (x, y) de cada casilla de cada barco, guardadas al empezar la partida.
- `disparos`: cada función escrita, quién la escribió y las casillas impactadas.
