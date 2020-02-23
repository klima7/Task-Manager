from PySide2.QtWidgets import *
from PySide2.QtCore import *
from data import data
from resources import convert_bytes_to_readable_form


class ProcessesTab(QWidget):
    """ Zakładka processes """

    def __init__(self):
        """ Dodawanie komponentów do zakładki """
        QWidget.__init__(self)

        self.layout = QHBoxLayout()
        self.layout.setMargin(0)
        self.setLayout(self.layout)

        self.processesPanel = ProcessesPanel()
        self.detailsPanel = DetailsPanel()

        self.layout.addWidget(self.processesPanel)
        self.layout.addWidget(self.detailsPanel)
        self.detailsPanel.hide()


class DetailsPanel(QWidget):
    """ Prawy panel ze szczegółami o procesach """

    def __init__(self):
        """ Dodawanie komponentów """
        QWidget.__init__(self)
        self.setFixedWidth(200)


class ProcessesPanel(QWidget):
    """ lewy panel z listą procesów """

    LABELS = ['Name', 'PID', 'Owner', 'State', 'Memory', 'Priority', 'Nice']

    def __init__(self):
        """ Dodawanie komponentów """
        QWidget.__init__(self)

        # Otwarte węzły w drzewie
        self.opened_items = {1}

        # Kolumny które mają być wyświetlane
        self.columns = {'Name': True, 'PID': True, 'Owner': True, 'State': True, 'Memory': False, 'Priority': False, 'Nice': False, 'Num Threads': False, 'Session ID': False, 'TTY Nr': False,
                        'VM Size': True, 'OOM Score': False}

        self.layout = QVBoxLayout()
        self.layout.setMargin(0)
        self.setLayout(self.layout)

        self.treeWidget = QTreeWidget(None)
        self.treeWidget.setIndentation(11)
        self.treeWidget.setStyleSheet("""QTreeWidget { border-style: none; }
                                      QScrollBar::handle:vertical { border: none }""")
        self.layout.addWidget(self.treeWidget)

        # Ustawianie nagłówków w liście
        self.treeWidget.setColumnCount(len(self.LABELS))
        self.treeWidget.setHeaderLabels(self.LABELS)
        self.treeWidget.setColumnWidth(0, 200)

        # Połączenie
        self.treeWidget.itemExpanded.connect(self.add_item)
        self.treeWidget.itemCollapsed.connect(self.remove_item)

        # Połączenie
        data.processes_changed.connect(self.refresh)

    @Slot(str, bool)
    def set_column_visible(self, column, visibility):
        """ Funkca pokazuje lub chowa daną kolumnę """
        self.columns[column] = visibility

    @Slot(object)
    def add_item(self, item):
        """ Funkcja dodaje przekazany węzeł do listy otwartych """
        pid = int(item.text(1))
        self.opened_items.add(pid)

    @Slot(object)
    def remove_item(self, item):
        """ Funkcja usuła przekazany węzeł z listy otwartych """
        pid = int(item.text(1))
        self.opened_items.difference_update({pid})

    @Slot(object)
    def refresh(self, processes):
        """ Funkcja aktualizuje listę procesów """

        self.treeWidget.clear()

        self._set_proper_labels(self.columns)

        # Tworzenie wpisu dla procesu Init
        init_proc = processes.init
        item = QTreeWidgetItem(None)
        self._fill_tree_item(item, init_proc, self.columns)
        self.treeWidget.insertTopLevelItem(0, item)
        item.setExpanded(1 in self.opened_items)

        # Tworzenie wpisów dla reszty procesów
        self._create_tree_recur(item, init_proc, self.columns)

    def _create_tree_recur(self, parentitem, proc, columns):
        """ Funkcja w rekurencyjny sposób tworzy drzewo procesów """

        for child in proc.children:
            item = QTreeWidgetItem(parentitem)
            self._fill_tree_item(item, child, columns)
            self._create_tree_recur(item, child, columns)
            item.setExpanded(child.pid in self.opened_items)

    def _set_proper_labels(self, columns):
        """ Funkcja ustawia odpowiednie nazwy kolumn """

        labels = [column for column in columns if columns[column]]
        self.treeWidget.setColumnCount(len(labels))
        self.treeWidget.setHeaderLabels(labels)

    def _fill_tree_item(self, item, proc, columns):
        """ Funkcja uzupełnia węzeł drzewa biorąc pod uwagę dane procesu i wybrane kolumny """

        nr = 0

        if columns['Name']:
            item.setText(nr, proc.stat['comm'])
            nr += 1

        if columns['PID']:
            item.setText(nr, str(proc.pid))
            nr += 1

        if columns['Owner']:
            item.setText(nr, proc.get_owner()[1])
            nr += 1

        if columns['State']:
            item.setText(nr, proc.get_readable_state())
            nr += 1

        if columns['Memory']:
            item.setText(nr, '0')
            nr += 1

        if columns['Priority']:
            item.setText(nr, proc.stat['priority'])
            nr += 1

        if columns['Nice']:
            item.setText(nr, proc.stat['nice'])
            nr += 1

        if columns['Num Threads']:
            item.setText(nr, proc.stat['num_threads'])
            nr += 1

        if columns['Session ID']:
            item.setText(nr, proc.stat['session'])
            nr += 1

        if columns['TTY Nr']:
            item.setText(nr, proc.stat['tty_nr'])
            nr += 1

        if columns['VM Size']:
            item.setText(nr, convert_bytes_to_readable_form(int(proc.stat['vsize'])))
            nr += 1

        if columns['OOM Score']:
            item.setText(nr, str(proc.read_oom_properties()[1]))
            nr += 1

