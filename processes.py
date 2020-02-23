# -*- coding: utf-8 -*-

import os
import os.path
import subprocess
import pwd

# Nazwy pól odpowiadające kolejnym tokenom z pliku proc/id/statm, szczegóły w man proc
STATM_KEYS = ('size', 'resident', 'shared', 'text', 'lib', 'data', 'dt')

# Nazwy kolejnych pól z pliku proc/id/stat, szczegóły w man proc
STAT_KEYS = ('pid', 'comm', 'state', 'ppid', 'pgrp', 'session', 'tty_nr', 'tpgid', 'flags', 'minflt', 'cminflt',
    'majflt', 'cmajflt', 'utime', 'stime', 'cutime', 'cstime', 'priority', 'nice', 'num_threads',
    'itrealvalue', 'starttime', 'vsize', 'rss', 'rsslim', 'startcode', 'endcode', 'startstack',
    'kstkesp', 'kstkeip', 'signal', 'blocked', 'sigignore', 'sigcatch', 'wchan', 'nswap', 'cnswap',
    'exit_signal', 'processor', 'rt_priority', 'policy', 'delayacct_blkio_ticks', 'guest_time', 'cguest_time',
    'start_data', 'end_data', 'start_brk', 'arg_start', 'arg_end', 'env_start', 'env_end', 'exit_code')

# Numery pid kilku ważnych procesów
SCHEDULER_PROCESS_PID = 0
INIT_PROCESS_PID = 1

# Zakres poprawnych wartości parametru oom_adj
OOM_ADJ_MIN = -17           # Proces nigdy nie zabijany
OOM_ADJ_MAX = 15            # Proces zawsze zabijany

# Maksymalna wartość arametru oom_score(najmniejsza to 0)
OOM_SCORE_MAX = 1000

# Zakres poprawnych wartości parametru oom_score_adj
OOM_SCORE_ADJ_MIN = -1000   # Proces nigdy nie zabijany
OOM_SCORE_ADJ_MIN = 1000    # Proces zawsze zabijany


class Limit:
    """ Klasa reprezentująca ograniczenia i przechowująca informacje o nich """

    def __init__(self, name, soft, hard, unit=''):
        """ Funkcja inicjuje pola wartościami z konstruktora """
        self.name = name
        self.soft_limit = soft
        self.hard_limit = hard
        self.unit = unit

    def __repr__(self):
        return "Limit[name: %s, soft_limit: %s, hard_limit: %s, unit: %s]" % (self.name, self.soft_limit, self.hard_limit, self.unit)


class MMFile:
    """ Klasa reprezentująca plik mapowany na pamieć """

    def __init__(self, address, permission, offset, device, inode, path=''):
        """ Funkcja inicjuje pola wartościami z konstruktora """
        self.address = address
        self.permission = permission
        self.offset = offset
        self.device = device
        self.inode = inode
        self.path = path

    def __repr__(self):
        return "MMFile[%s, %s, %s, %s, %s, %s]" % (self.address, self.permission, self.offset, self.device, self.inode, self.path)


class MountPoint:
    """ Klasa reprezentująca punkt montowania """

    def __init__(self, mount_id, parent_id, st_dev, root, mount_point, mount_options, optional_fields, fs_type, mount_source, super_options):
        """ Funkcja inicjuje pola wartościami z konstruktora """
        self.mount_id = mount_id
        self.parent_id = parent_id
        self.st_dev = st_dev
        self.root = root
        self.mount_point = mount_point
        self.mount_options = mount_options
        self.optional_fields = optional_fields
        self.fs_type = fs_type
        self.mount_source = mount_source
        self.super_options = super_options

    def __repr__(self):
        return "MountPoint[%s %s %s %s %s %s %s %s %s %s]" % (self.mount_id, self.parent_id, self.st_dev, self.root, self.mount_point, self.mount_options, self.optional_fields, self.fs_type, self.mount_source, self.super_options)


class Process:
    """ Klasa reprezentująca proces """

    # TODO Dodać do informacji o plikach mapowanych na pamięć informację o NUMA i informacje z pliku smaps
    # TODO Dodać obśługę proc/meminfo

    def __init__(self, pid):
        """ W konstruktorze procesu pobierane są wszystkie dane na temat procesu o podanym numerze pid """
        self.proc_directory = os.path.join('/proc', str(pid))
        self.pid = pid
        self.parent = None
        self.children = []
        self.stat = {}
        self.update_stat()

    def __eq__(self, other):
        """ Porównanie zwraca prawdę gdy numer procesu się zgadza z liczbą """
        if isinstance(other, int):
            return self.pid == other
        elif isinstance(other, Process):
            return self.pid == other.pid
        else:
            return False

    def __repr__(self):
        """ Wypisuje najważniejsze parametry procesu """
        children_message = ''
        for child in self.children:
            children_message += str(child.pid) + ' '
        if not children_message:
            children_message = '---'
        return "[PID %7d, Parent %7s, Children %s]" % (self.pid, self.stat['ppid'], children_message)

    def __str__(self):
        """ To samo co repr """
        return self.__repr__()

    def update_stat(self):
        """ Funkcja przyjmująca pid procesu i zwracająca słownik z informacjami odczytanymi z pliku /proc/pid/stat """

        # Odczytanie zawartości pliku stat
        path = os.path.join(self.proc_directory, 'stat')
        with open(path, 'r') as file:
            content = file.readline()

        # Nazwa pliku wykonywalnego jest zapisana w odróżnieniu od reszty w nawiasach okrągłych i może zawierać spacje, znajdujemy ten fragment i go usówamy
        pstart, pend = content.find('('), content.find(')')
        comm = content[pstart+1:pend]
        content = content[:pstart-1] + content[pend+1:]

        # Resztę symboli można bez problemu rozdzielić za pomocą spacji
        content = content.strip()
        tokens = content.split(' ')

        # Na liście tokenów umieszczamy nazwę pliku wykonywalnego którą wcześniej wyodrębniliśmy
        tokens.insert(1, comm)

        # Stworzenie słownika i zapisanie go w polu stat
        self.stat = dict(zip(STAT_KEYS, tokens))

    def read_associated_command(self):
        """ Funkcja odczytuje komendę skojarzoną z procesem """

        # Odczytanie zawartości pliku comm
        path = os.path.join(self.proc_directory, 'comm')
        with open(path, 'r') as file:
            content = file.readline()
        return content

    def read_execusion_command(self):
        """ Funkcja zwraca krotkę zawierająca polecenie użyte do uruchomienia procesu i użyte argumenty """

        # Odczytanie zawartości pliku cmdline
        path = os.path.join(self.proc_directory, 'cmdline')
        with open(path, 'r') as file:
            content = file.readline()

        # Usunięcie ewentualnego ostatniego znaku o kodzie zero, by przy tokenizacji nie dostać tokena o długości 0
        content = content.strip(chr(0))

        # Rozdzielenie tokenów i zwrócenie wyniku - argumenty są rozdzielone za pomocą znaku o kodzie 0
        tokens = content.split(chr(0))
        return tuple(tokens)

    def read_stack(self):
        """ Funkcja zwraca ogólny opis stanu stosu z pliku stack """
        path = os.path.join(self.proc_directory, 'stack')
        with open(path, 'r') as file:
            content = file.readline()
        return content

    def read_current_working_directory(self):
        """ Funkcja zwraca aktualny katalog roboczy  """

        # Funkcja odczytuje dokąd prowadzi link symboliczny cwd
        path = os.path.join(self.proc_directory, 'cwd')
        cwd = os.readlink(path)
        return cwd

    def read_environmental_variables(self):
        """ Funkcja odczytuje listę zmiennych środowiskowych przekazane procesowi przy jego uruchomieniu """

        # Odczytanie zawartości pliku environ
        path = os.path.join(self.proc_directory, 'environ')
        with open(path, 'r') as file:
            content = file.readline()

        # Tokenizacja - poszczególne wpisy są oddzielone za pomocą znaków 0
        entries = content.split(chr(0))

        # Tworzenie słownika nazwa_zmiennej: wartość_zmiennej
        variables_dictionary = {}
        for entry in entries:
            # Nie wiem czy to jakiś błąd w systemie, ale zmienna DBUS_SESSION_BUS_ADDRESS zawiera dwa znaki =, stąd następujące dwie linie
            key, *value = entry.split('=')
            value = ''.join(value)
            # Dodanie zmiennej do słownika
            variables_dictionary[key] = value

        return variables_dictionary

    def read_file_descriptors(self):
        """ Funkcja zwraca słownik z kluczamy będącymi deskryptorami plików i wartościami ze ścieżkami do otwarty przez proces plików.
            Jeżeli deskryptor wskazuje na strumień lub gniazdo to ścieżka nie jest poprawna """

        # Dla każdego otwartego pliku w katalogu proc/id/fd znajduje się link symboliczny
        # Odczytujemy nazwy tych plików
        path = os.path.join(self.proc_directory, 'fd')
        files = os.listdir(path)

        # Sprawdzamy gdzie wskazują linki symboliczne i zachowujemy te ścieżki
        descriptors = {}
        for file in files:
            physical_path = os.readlink(os.path.join(path, file))
            descriptors[int(file)] = physical_path

        return descriptors

    def read_file_descriptor_details(self, fd):
        """ Zwraca informacje o deskryptorze o przekazanym numerze """
        path = os.path.join(self.proc_directory, 'fdinfo', str(fd))
        with open(path, 'r') as file:
            details = ''.join(file.readlines())
        return details

    def read_io_stats(self):
        """ Zwraca statystyki operacji wejścia/wyjścia """
        # Stworzenie słownika z odczytanymi statystykami
        io_stats = {}

        # Statystyki io znajdują się w pliku proc/id/io
        path = os.path.join(self.proc_directory, 'io')
        with open(path, 'r') as file:
            lines = file.readlines()

            for line in lines:
                # Statystyki są zapisanie w pliku w postaci parametr: wartość
                key, value = line.strip().split(':')
                io_stats[key] = value

        return io_stats

    def read_limits(self):
        """ Funkcja odczytuje ograniczenia danego procesu i zwraca je w postaci listy objektów Limit """

        # Lista wszystkich ograniczneń
        limits = []

        # Statystyki io znajdują się w pliku proc/id/io
        path = os.path.join(self.proc_directory, 'limits')
        with open(path, 'r') as file:
            # Pierwszy wiersz pliku zawiera nagłówek
            lines = file.readlines()[1:]

            for line in lines:
                # Rozdzielenie tokenów, mogą one zawierać pojedyńcze spacje, więc rozdzielamy za pomocą podwójnych
                tokens = line.strip().split('  ')
                filtered = list(filter(lambda token: len(token), tokens))
                limits.append(Limit(*filtered))

        return tuple(limits)

    def read_memory_maped_files(self):
        """ Funkcja odczytuje informacje o plikach zmapowanych na pamieć """

        # Lista wszystkich ograniczneń
        mmfiles = []

        # Statystyki io znajdują się w pliku proc/id/io
        path = os.path.join(self.proc_directory, 'maps')
        with open(path, 'r') as file:
            lines = file.readlines()

            for line in lines:
                # Wszystkie tokeny oprócz ostatniego rozdzielamy za pomocą spacji, bo na pewno jej nie zawierają
                tokens = line.strip().split(' ', 5)
                # Ostatniemu tokenowi usówamy spacji poprzedzające i kończące by był poprawny
                tokens[-1] = tokens[-1].strip()
                mmfiles.append(MMFile(*tokens))

        return tuple(mmfiles)

    def read_mount_points(self):
        """ Funkcja zwraca informacje o punktach montowania w postaci krotki obiektów MountPoint """

        # Lista do której będziemy dodawać punkty montowania
        mount_points = []

        # Informacje o punktach montowania znajdują się w pliku proc/id/mountinfo
        path = os.path.join(self.proc_directory, 'mountinfo')
        with open(path, 'r') as file:
            lines = file.readlines()

            for line in lines:
                # Pierwsze 6 i ostatnie 3 pola zawsze istnieją, natomiast w polu options może wystąpić wiele tokenów, szczegóły w man proc
                first_tokens = line.strip().split(' ', 6)
                last_tokens = first_tokens[-1].rsplit(' ', 3)
                first_tokens = first_tokens[:-1]
                last_tokens[-4] = last_tokens[-4].strip(' -')
                all_tokens = first_tokens+last_tokens

                # Stworzenie i dodanie punktu
                mount_points.append(MountPoint(*all_tokens))

        return tuple(mount_points)

    def read_oom_properties(self):
        """ Zwraca informacje dotyczące proawdopodobieństwa, że proces zostanie zabity w sytuacji oom(out-of-memory)
            Funkcja zwraca trzyelementową krotkę (oom_adj, oom_score, oom_score_adj)"""

        try:
            path = os.path.join(self.proc_directory, 'oom_adj')
            with open(path, 'r') as file:
                oom_adj = int(file.readline().strip())

            path = os.path.join(self.proc_directory, 'oom_score')
            with open(path, 'r') as file:
                oom_score = int(file.readline().strip())

            path = os.path.join(self.proc_directory, 'oom_score_adj')
            with open(path, 'r') as file:
                oom_score_adj = int(file.readline().strip())

            return oom_adj, oom_score, oom_score_adj
        except FileNotFoundError:
            return 0, 0, 0

    def change_oom_score_adj(self, factor):
        """ Funkcja zmienia parametr mówiący o prawdopodobieństwie zabicia procesu w sytuacji oom """

        path = os.path.join(self.proc_directory, 'oom_score_adj')
        with open(path, 'w') as file:
            file.write(str(factor))

    def read_memory_usage_data(self):
        """ Zwraca słownik z informacjami o zużytej ilości stron odczytanych z pliku /proc/pid/statm """

        path = os.path.join(self.proc_directory, 'statm')
        with open(path, 'r') as file:
            content = file.readline().strip()

        # Tokenizacja i konwersja na liczby
        tokens = content.split(' ')
        tokens = [int(token) for token in tokens]

        return dict(zip(STATM_KEYS, tokens))

    def read_schedule_stat(self):
        """ Funkcja zwraca trójelementową krotkę: czas wykonywania procesu, czas oczekiwania, '# of timeslices run on this cpu' """

        path = os.path.join(self.proc_directory, 'schedstat')
        with open(path, 'r') as file:
            content = file.readline().strip()

        tokens = content.split(' ')
        tokens = [int(token) for token in tokens]
        return tuple(tokens)

    def get_owner(self):
        """ Funkcja zwraca uid właściciela procesu i nazwe właściciela """
        try:
            owner_uid = os.stat(self.proc_directory).st_uid
            owner_name = pwd.getpwuid(owner_uid).pw_name
            return owner_uid, owner_name
        except FileNotFoundError:
            return 0, 'Unknown'

    def get_parent_pid(self):
        """ Funkcja zwraca numer pid rodzica """
        return int(self.stat['ppid'])

    def get_readable_state(self):
        """ Funkcja zwraca stan procesu w czytelnej postaci """
        state = self.stat['state']
        if state == 'R':
            return 'Running'
        elif state == 'S':
            return 'Sleeping'
        elif state == 'D':
            return 'Waiting on disc'
        elif state == 'Z':
            return 'Zombie'
        elif state == 'T':
            return 'Stopped'
        elif state == 't':
            return 'Tracing Stop'
        elif state == 'W':
            return 'Paging'
        elif state == 'W':
            return 'Paging'
        elif state == 'W':
            return 'Paging'
        elif state == 'X':
            return 'Dead'
        elif state == 'W':
            return 'Paging'
        elif state == 'W':
            return 'Paging'
        else:
            return 'Unknown'

    def kill(self):
        """ Funkcja zabija proces """
        subprocess.run('kill %d' % self.pid, shell=True, check=True)

    def change_priority(self, priority):
        """ Funkcja zmienia priorytet procesu """
        subprocess.run('sudo renice %d %d' % (priority, self.pid), shell=True, check=True)


class Processes:
    """ Klasa reprezentująca całą herarchię procesów """

    def __init__(self):
        """ Funkcja inicjująca pusty obiekt i wywołująca aktualizację by zawierał dane o procesach """
        self.all = []
        self.init = None
        self.max_pid = self.get_max_pid()

    def __repr__(self):
        """ Funkcja wypisuje informacje o wszystkich procesach """
        message = ""
        for process in self.all:
            message = message + str(process) + '\n'
        return message

    def __str__(self):
        """ Funkcja robi to samo co repr """
        return self.__repr__()

    def update(self):
        """ Funkcja pobierająca aktualne procesy i porządkująca je """
        self.update_processes()
        self.update_processes_tree()

    def update_processes(self):
        """ Funkcja aktualizująca pole all zawierające zbiór wszystkich procesów """

        # Znalezienie numerów pid wszystkich istniejących procesów
        pids = []
        for i in range(1, self.max_pid):
            if os.path.exists("/proc/"+str(i)):
                pids.append(i)

        # Stworzenie obiektu procesu dla każdego znalezionego pid
        self.all = []
        for pid in pids:
            try:
                self.all.append(Process(pid))
            except FileNotFoundError:
                continue
        return pids

    def update_processes_tree(self):
        """ Funkcja tworząca/aktualizująca drzewo procesów i umieszczająca w self.init proces nadrzędny - korzeń drzewa """
        for proc in self.all:
            proc_parent_pid = proc.get_parent_pid()

            # Zdarzy się to zapewne dla procesu init - jednak procesu o numerze pid 0 nie ma w folderze proc
            if proc_parent_pid == SCHEDULER_PROCESS_PID:
                continue
            parent_process = self.all[self.all.index(proc_parent_pid)]
            parent_process.children.append(proc)

        # Znalezienie procesu init i zachowanie go
        self.init = self.all[self.all.index(INIT_PROCESS_PID)]

    def get_process_by_pid(self, pid):
        """ Funkcja zwraca obiekt procesu o podanym numerze pid lub None jeżeli taki nie istnieje """
        try:
            return self.all[self.all.index(pid)]
        except ValueError:
            return None

    @staticmethod
    def get_max_pid():
        """ Funkcja zwraca maksymalny numer pid jaki może mieć proces """
        with open('/proc/sys/kernel/pid_max', 'r') as file:
            content = file.readline()
        return int(content)









