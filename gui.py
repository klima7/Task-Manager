# -*- coding: utf-8 -*-

import time
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from threading import Thread, Lock
from data import data
from processesTab import ProcessesTab


class RefreshingTimer(Thread, QObject):
    """ Timer odpowiedzialny za odświeżanie zawartości okna co ustalony czas """

    def __init__(self, period):
        Thread.__init__(self)
        QObject.__init__(self)

        self.no_refresh = Lock()

        self.period = period
        self.setDaemon(True)

    def run(self):
        """ Odświeżanie co czas period """

        while True:

            # Jeżeli okres wynosi zero to usypiam wątek - zatrzymuje odświeżanie
            while self.period == 0:
                self.no_refresh.acquire()

            time.sleep(self.period)
            data.update()

    @Slot(float)
    def change_period(self, period):
        print(period)

        # Jeśli timer jest zatrzymany to go wznawiam
        if self.period == 0 and period != 0:
            self.no_refresh.release()

        self.period = period

    @Slot()
    def refresh_now(self):
        data.update()


class MainWindow(QMainWindow):
    """ Główne okno aplikacji """

    WINDOW_TITLE = "Task Manager"
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 600

    def __init__(self):
        QMainWindow.__init__(self)

        # Ustalenie tytułu i rozmiaru okna
        self.setWindowTitle(MainWindow.WINDOW_TITLE)
        self.setGeometry(100, 100, MainWindow.WINDOW_WIDTH, MainWindow.WINDOW_HEIGHT)

        # Dodanie głównej zawartośći okna
        self.central_widget = CentralWidget()
        self.setCentralWidget(self.central_widget)

        # Stworzenie timera odświeżającego okno co dany okres
        self.timer = RefreshingTimer(1)
        self.timer.start()

        # Dodanie menu
        self._create_menu()

    def _create_menu(self):
        """ Tworzenie menu na górze okna """

        # Stworzenie najwyższego poziomu menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu("File")
        self.view_menu = self.menu.addMenu("View")
        self.refresh_menu = self.menu.addMenu("Refresh")
        self.help_menu = self.menu.addMenu("Help")

        # Wypełnianie menu plik
        exit_action = QAction("Quit", self)
        self.file_menu.addAction(exit_action)

        # Wypełnianie menu view
        self.column_name = ColumnSelectButton('Owner', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, True)
        self.view_menu.addAction(self.column_name)

        self.column_state = ColumnSelectButton('State', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, True)
        self.view_menu.addAction(self.column_state)

        self.column_memory = ColumnSelectButton('Memory', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_memory)

        self.column_priority = ColumnSelectButton('Priority', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_priority)

        self.column_nice = ColumnSelectButton('Nice', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_nice)

        self.column_numthreads = ColumnSelectButton('Num Threads', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_numthreads)

        self.column_session = ColumnSelectButton('Session ID', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_session)

        self.column_tty = ColumnSelectButton('TTY Nr', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_tty)

        self.column_vmsize = ColumnSelectButton('VM Size', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, True)
        self.view_menu.addAction(self.column_vmsize)

        self.column_oomscore = ColumnSelectButton('OOM Score', self.central_widget.tab_panel.tab1.processesPanel.set_column_visible, False)
        self.view_menu.addAction(self.column_oomscore)

        # Wypełnianie menu refresh
        self.refresh_group = QActionGroup(self.refresh_menu)

        self.refresh02 = RefreshButton('0.2 seconds', 0.2, self.refresh_group, self.timer.change_period)
        self.refresh_menu.addAction(self.refresh02)

        self.refresh05 = RefreshButton('0.5 seconds', 0.5, self.refresh_group, self.timer.change_period)
        self.refresh_menu.addAction(self.refresh05)
        self.refresh05.setChecked(True)

        self.refresh1 = RefreshButton('1 seconds', 1, self.refresh_group, self.timer.change_period)
        self.refresh_menu.addAction(self.refresh1)

        self.refresh2 = RefreshButton('2 seconds', 2, self.refresh_group, self.timer.change_period)
        self.refresh_menu.addAction(self.refresh2)

        self.norefresh = RefreshButton('No refresh', 0, self.refresh_group, self.timer.change_period)
        self.refresh_menu.addAction(self.norefresh)

        self.refresh_now = QAction('Refresh now')
        self.refresh_menu.addSeparator()
        self.refresh_menu.addAction(self.refresh_now)
        self.refresh_now.triggered.connect(self.timer.refresh_now)


class RefreshButton(QAction):
    """ Przycisk umieszczony w menu refresh zmieniający odświeżanie """

    refresh_selected = Signal(float)

    def __init__(self, text, period, group, slot):
        QAction.__init__(self, text)
        self.period = period
        group.addAction(self)
        self.setCheckable(True)
        self.refresh_selected.connect(slot)
        self.triggered.connect(lambda: self.refresh_selected.emit(self.period))


class ColumnSelectButton(QAction):
    """ Przycisk umożliwiający dodanie lub usunięcie kolumny z widoku """

    column_changed = Signal(str, bool)

    def __init__(self, text, slot, checked):
        QAction.__init__(self, text)
        self.text = text
        self.setCheckable(True)
        self.column_changed.connect(slot)
        self.triggered.connect(lambda: self.column_changed.emit(self.text, self.isChecked()))
        self.setChecked(checked)


class CentralWidget(QWidget):
    """ Widget znajdujący się w głównej części okna """

    def __init__(self):
        """ Dodawanie elementów do widgeta """

        QWidget.__init__(self)

        self.vertical_layout = QVBoxLayout()
        self.setLayout(self.vertical_layout)

        self.bars_layout = QHBoxLayout()
        self.vertical_layout.addLayout(self.bars_layout)

        # Tworzenie paska CPU
        self.cpu_bar = ColorProgressBar('CPU', 0, 100, 0)
        self.bars_layout.addWidget(self.cpu_bar)
        data.cpu_load_changed.connect(self.cpu_bar.setValue)

        # Tworzenia paska RAM
        self.ram_bar = ColorProgressBar('RAM')
        self.bars_layout.addWidget(self.ram_bar)
        data.ram_space_changed.connect(self.ram_bar.setValue)

        self.tab_panel = TabPanel()
        self.vertical_layout.addWidget(self.tab_panel)


class TabPanel(QWidget):
    """ Klasa przedstawiająca panel z zakładkami znajdujący się w głównym oknie """

    def __init__(self):
        """ W konstruktorze tworzone są wszystkie zakładki """
        QWidget.__init__(self)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.tab_widget = QTabWidget()

        self.layout.addWidget(self.tab_widget)
        self.tab_widget.resize(300, 200)

        self.tab1 = ProcessesTab()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()

        self.tab_widget.addTab(self.tab1, "Processes")
        self.tab_widget.addTab(self.tab2, "Processor")
        self.tab_widget.addTab(self.tab3, "Memory")
        self.tab_widget.addTab(self.tab4, "Discs")


class TitledProgressBar(QProgressBar):
    """ Pasek postępu z napisem """

    def __init__(self, title, mini=0, maxi=100, val=0):
        QProgressBar.__init__(self)

        # Zapamiętanie i uwidocznienie tytułu
        self.title = title
        self.setTextVisible(True)

        # Ustalenie aktulnej wartości suwaka
        self.setMaximum(maxi)
        self.setMinimum(mini)
        self.setValue(val)

    def text(self):
        """ Funkcja robi to samo co wcześniej lecz przed wynikiem procentowym dodaje tytuł """
        return self.title + ' ' + super().text()


class ColorProgressBar(TitledProgressBar):
    """ Pasek postępu z tytułem zmieniający kolor w zależności od wartości """

    MIN_COLOR = 110     # Zielony
    MAX_COLOR = 0       # Czerwony

    def __init__(self, title, mini=0, maxi=100, val=0):
        TitledProgressBar.__init__(self, title, mini, maxi, val)
        self.setValue(val)

    def setValue(self, value):
        """ Robi to samo co wcześniej, lecz jeszcze zmienia kolor """

        color = self._calculate_color(value)
        self.setStyleSheet(ColorProgressBar.style % color)
        super().setValue(value)

    def _calculate_color(self, value):
        """ Funkcja pomocnicza obliczająca jaki kolor powinien mieć pasek przy danej wartości """

        minimum = self.minimum()
        maximum = self.maximum()
        percent = (value-minimum)/(maximum-minimum)

        hue = int(self.MIN_COLOR - (self.MIN_COLOR - self.MAX_COLOR) * percent)
        return str(hue) + r", 100%, 50%"

    # Odczytanie reguł css dla wyglądu paska przy pierwszym użyciu klasy
    with open('ProgressBar.css') as f:
        style = ''.join(f.readlines())











