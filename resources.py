# -*- coding: utf-8 -*-

# Nazwy pól odpowiadające kolejnym tokenom z pliku proc/loadavg, szczegóły w man proc
AVGLOAD_KEYS = ('cpu_use_1', 'cpu_use_5', 'cpu_use_15', 'exec_threads', 'max_exec_threads', 'last_created_pid')

# Nazwy pól z pliku proc/stat odpowiadające czynnościam na które procesor przeznaczył czas
STAT_CPU_KEYS = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest', 'guest_nice')


def get_avgload():
    """ Funkcja zwraca listę ze średnim zużyciem procesora w ciągu ostatnich 1, 5, 15 minut  """

    # Odczytanie zawartości pliku avgload
    with open('/proc/loadavg', 'r') as file:
        content = file.readline()

    # Tokenizujemy. Tokeny są rozdzielone za pomocą ukośnika lub spacji, więc zamieniamy wszystkie ukośniki na spacji by to ujednolicić
    content = content.strip()
    content = content.replace('/', ' ')
    tokens = content.split(' ')

    # Zamiana łańcuchów znaków na odpowiedni typ
    return dict(zip(AVGLOAD_KEYS, tokens))


def get_memory_info():
    """ Funkcja zwraca słownik z informacjami na temat pamięci ram """

    # Słownik który jest dalej uzupełniany
    memory_data = {}

    # Odczytanie zawartości pliku meminfo
    with open('/proc/meminfo', 'r') as file:
        lines = file.readlines()

        for line in lines:
            tokens = line.split(' ')

            # Pozostawienie tokenów które nie mają długości 0
            tokens = [token for token in tokens if token]

            key, value = tokens[0:2]
            key = key.rstrip(':')
            memory_data[key] = int(value)

    return memory_data


def convert_bytes_to_readable_form(bytes):
    """ Przedstawia podaną liczbę w czytelnej postaci, np. Mb, Gb, zwraca napis """

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0

    while bytes >= 1024:
        bytes /= 1024
        unit_index += 1

    return '%.1f %s' % (bytes, units[unit_index])


def get_cpus_times():
    """ Funkcja zwraca krotkę słowników, po jednym słowniku na każdy procesor, zawierające na co procesor stracił czas """

    cpus = []

    with open('/proc/stat', 'r') as file:
        while True:
            line = file.readline().strip()

            # Jeśli odczytano już informacje o wszystkich procesorach
            if not line.startswith('cpu'):
                break

            tokens = line.split(' ')
            tokens = [int(token) for token in tokens[1:] if token]
            cpu = dict(zip(STAT_CPU_KEYS, tokens))
            cpus.append(cpu)

    return cpus


class CpuTracker:
    """ Klasa odpowiedzialna za śledzenie obciążenia procesora """

    def __init__(self):
        """ Konstruktor obiektu śledzącego obiążenie procesora """
        self.previous_times = None

    def update(self):
        """ Funkcja pobiera czasy procesorów, obliczna obiążenia jeśli już może i je zwraca w postaci słownika """

        current_times = get_cpus_times()

        # Sprawdzenie czy można obliczyć obciążenia
        if self.previous_times is None:
            self.previous_times = current_times
            return None

        cpus_count = len(current_times)
        cpus = []

        for cpu in range(cpus_count):
            previous_total = sum(self.previous_times[cpu].values())
            current_total = sum(current_times[cpu].values())

            loads = {}

            for key in current_times[cpu]:
                if current_total - previous_total == 0:
                    return None
                loads[key] = (current_times[cpu][key] - self.previous_times[cpu][key]) / (current_total - previous_total)
            loads['load'] = 1-loads['idle']
            cpus.append(loads)

        self.previous_times = current_times
        return cpus









