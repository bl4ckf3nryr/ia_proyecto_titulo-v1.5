"""
state.py
Estado central de la simulacion de bodega.
Mantiene configuracion, pallets y calculo de capacidad/ocupacion.
"""

import math
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Tuple

# Tipos de producto validos
PRODUCT_TYPES = {
    "leche":   {"label": "Pallet de leche",   "color": "#f2f2f2"},
    "cajas":   {"label": "Pallet de cajas",   "color": "#c98a3a"},
    "bebidas": {"label": "Pallet de bebidas", "color": "#2e7d32"},
}

# Limites de configuracion
MIN_WIDTH, MAX_WIDTH = 2, 8
MIN_DEPTH, MAX_DEPTH = 2, 8
MIN_LEVELS, MAX_LEVELS = 1, 3
MIN_THRESHOLD = 0.0
MAX_THRESHOLD = 100.0


@dataclass
class Pallet:
    """Un pallet ubicado en una posicion discreta (x, y, level)."""
    x: int
    y: int
    level: int
    product: str

    def key(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.level)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WarehouseState:
    width: int = 4
    depth: int = 3
    levels: int = 2
    min_threshold_pct: float = 20.0
    pallets: Dict[Tuple[int, int, int], Pallet] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ---------- Calculos ----------
    def capacity(self) -> int:
        return self.width * self.depth * self.levels

    def occupied(self) -> int:
        return len(self.pallets)

    def free(self) -> int:
        return self.capacity() - self.occupied()

    def occupancy_pct(self) -> float:
        cap = self.capacity()
        if cap == 0:
            return 0.0
        return round((self.occupied() / cap) * 100.0, 2)

    def min_pallets(self) -> int:
        return math.ceil((self.min_threshold_pct / 100.0) * self.capacity())

    def status(self) -> str:
        occ = self.occupied()
        cap = self.capacity()
        if occ == 0:
            return "vacia"
        if occ >= cap:
            return "llena"
        if occ < self.min_pallets():
            return "bajo_minimo"
        return "en_rango"

    def in_bounds(self, x: int, y: int, level: int) -> bool:
        return (
            0 <= x < self.width
            and 0 <= y < self.depth
            and 0 <= level < self.levels
        )

    # ---------- Operaciones ----------
    def add_pallet(self, x: int, y: int, level: int, product: str) -> Tuple[bool, str]:
        with self._lock:
            if product not in PRODUCT_TYPES:
                return False, f"Tipo de producto invalido: {product}"
            if not self.in_bounds(x, y, level):
                return False, "Posicion fuera de los limites de la bodega."
            key = (x, y, level)
            if key in self.pallets:
                return False, "La posicion ya esta ocupada."
            self.pallets[key] = Pallet(x, y, level, product)
            return True, "Pallet agregado."

    def remove_pallet(self, x: int, y: int, level: int) -> Tuple[bool, str]:
        with self._lock:
            key = (x, y, level)
            if not self.in_bounds(x, y, level):
                return False, "Posicion fuera de los limites de la bodega."
            if key not in self.pallets:
                return False, "La posicion esta vacia."
            del self.pallets[key]
            return True, "Pallet retirado."

    def move_pallet(
        self,
        src: Tuple[int, int, int],
        dst: Tuple[int, int, int],
    ) -> Tuple[bool, str]:
        with self._lock:
            if src not in self.pallets:
                return False, "La posicion de origen no contiene un pallet."
            if not self.in_bounds(*dst):
                return False, "Posicion de destino fuera de los limites."
            if dst in self.pallets:
                return False, "La posicion de destino ya esta ocupada."
            pallet = self.pallets.pop(src)
            pallet.x, pallet.y, pallet.level = dst
            self.pallets[dst] = pallet
            return True, "Pallet trasladado."

    def clear(self) -> Tuple[bool, str]:
        with self._lock:
            self.pallets.clear()
            return True, "Bodega vaciada."

    def configure(
        self,
        width: int,
        depth: int,
        levels: int,
        min_threshold_pct: Optional[float] = None,
    ) -> Tuple[bool, str]:
        with self._lock:
            if not (MIN_WIDTH <= width <= MAX_WIDTH):
                return False, f"Ancho debe estar entre {MIN_WIDTH} y {MAX_WIDTH}."
            if not (MIN_DEPTH <= depth <= MAX_DEPTH):
                return False, f"Fondo debe estar entre {MIN_DEPTH} y {MAX_DEPTH}."
            if not (MIN_LEVELS <= levels <= MAX_LEVELS):
                return False, f"Niveles debe estar entre {MIN_LEVELS} y {MAX_LEVELS}."
            if min_threshold_pct is not None:
                if not (MIN_THRESHOLD <= min_threshold_pct <= MAX_THRESHOLD):
                    return False, "El umbral minimo debe estar entre 0 y 100."
                self.min_threshold_pct = float(min_threshold_pct)

            changed = (self.width, self.depth, self.levels) != (width, depth, levels)
            self.width, self.depth, self.levels = width, depth, levels

            if changed:
                kept = {}
                for key, p in self.pallets.items():
                    if self.in_bounds(p.x, p.y, p.level):
                        kept[key] = p
                self.pallets = kept
                return True, "Dimensiones actualizadas (distribucion reiniciada)."
            return True, "Configuracion actualizada."

    # ---------- Serializacion ----------
    def snapshot(self) -> dict:
        with self._lock:
            return {
                "width": self.width,
                "depth": self.depth,
                "levels": self.levels,
                "min_threshold_pct": self.min_threshold_pct,
                "min_pallets": self.min_pallets(),
                "capacity": self.capacity(),
                "occupied": self.occupied(),
                "free": self.free(),
                "occupancy_pct": self.occupancy_pct(),
                "status": self.status(),
                "product_types": PRODUCT_TYPES,
                "pallets": [p.to_dict() for p in self.pallets.values()],
            }


# Instancia global unica (compartida por API y camara)
STATE = WarehouseState()