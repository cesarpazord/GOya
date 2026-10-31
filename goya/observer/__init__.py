"""Patrón Observer (núcleo puro, sin dependencias de Flask)."""
from abc import ABC, abstractmethod


class Observador(ABC):
    @abstractmethod
    def actualizar(self, orden, estado): ...


class Sujeto:
    def __init__(self):
        self._observadores = []

    def suscribir(self, obs):
        if obs not in self._observadores:
            self._observadores.append(obs)

    def desuscribir(self, obs):
        if obs in self._observadores:
            self._observadores.remove(obs)

    def notificar(self, orden, estado):
        for obs in list(self._observadores):
            obs.actualizar(orden, estado)


bus_ordenes = Sujeto()
