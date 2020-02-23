# -*- coding: utf-8 -*-

import math
from PyQt5.QtCore import pyqtSignal
from PySide2.QtCore import *
from processes import *
from resources import *


class DataPack(QObject):
    """ Klasa przechowująca informacje na temat procesów i zasobów z których korzysta gui """

    cpu_load_changed = Signal(int)
    ram_space_changed = Signal(int)
    processes_changed = Signal(object)

    def __init__(self):
        """ Konstruktor xd """
        QObject.__init__(self)

        self.cpu_tracker = CpuTracker()
        self.cpu_loads = None
        self.memory_info = None
        self.processes = Processes()

    def get_ram_percent_use(self):
        """ Zwraca procentową zajętość pamięci ram """
        total = self.memory_info['MemTotal']
        use = self.memory_info['MemTotal'] - self.memory_info['MemAvailable']
        return use / total * 100

    def update(self):
        """ Funkcja aktualizująca wszystkie dane w obiekcie """

        # Pobranie obciążenia procesora
        new_cpu_loads = self.cpu_tracker.update()
        if new_cpu_loads:
            self.cpu_loads = new_cpu_loads

            # Zmiana wartości na głównym pasku progresu zużycia cpu
            value = math.ceil(self.cpu_loads[0]['load']*100)
            self.cpu_load_changed.emit(value)

        # Pobranie stanu pamięci
        self.memory_info = get_memory_info()
        self.ram_space_changed.emit(self.get_ram_percent_use())

        # aktualizacja procesów
        self.processes.update()
        self.processes_changed.emit(self.processes)


# Dane na temat procesów i zasobów
data = DataPack()



