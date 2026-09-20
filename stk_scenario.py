"""Szenario: Ereignisfolge im Containerblock und verrauschte Abfahrtsschätzung.

Ein Block besteht aus n_stacks Stapeln der Höhe max_height. Container kommen und gehen in einer
Ereignisfolge ("A" = Ankunft, "D" = Abholung). Die wahre Abfahrt eines Containers ist der Index
seines "D"-Ereignisses. Die Regeln sehen nur eine Schätzung davon (siehe estimate_departures).
"""

import random
from dataclasses import dataclass

import stk_constants as C

INF = float("inf")


@dataclass(frozen=True)
class Instance:
    n_stacks: int
    max_height: int
    fill: float            # Anteil von (n_stacks - 1) * max_height, 0 < fill <= 1
    n_containers: int
    seed: int
    capacity: int          # höchste gleichzeitige Belegung
    events: tuple          # ((kind, container), ...), kind in {"A", "D"}
    arrival: dict          # container -> Index des Ankunfts-Ereignisses
    departure: dict        # container -> Index des Abholungs-Ereignisses (wahre Abfahrt)
    mean_dwell: float      # mittlere Standzeit in Ereignisschritten

    @property
    def n_events(self):
        return len(self.events)


def capacity_for(n_stacks, max_height, fill):
    """Höchste gleichzeitige Belegung. Bis (n_stacks - 1) * max_height + 1 Container finden beim Abholen
    immer Platz zum Umstapeln: liegen k Container über dem Ziel in Stapel x, sind außerhalb von x
    (n_stacks * max_height - Belegung) - (max_height - len(x)) Plätze frei, und k <= len(x) - 1."""
    return max(1, round(fill * (n_stacks - 1) * max_height))


def generate_instance(n_stacks, max_height, fill, n_containers, seed):
    if n_stacks < 2:
        raise ValueError("Mindestens 2 Stapel nötig (sonst gibt es kein Umstapeln).")
    if max_height < 1:
        raise ValueError("Stapelhöhe muss mindestens 1 sein.")
    if not 0 < fill <= 1:
        raise ValueError("Füllgrad muss in (0, 1] liegen.")
    if n_containers < 1:
        raise ValueError("Mindestens 1 Container nötig.")

    rng = random.Random(seed)
    cap = capacity_for(n_stacks, max_height, fill)
    events, present, arrived = [], [], 0
    while arrived < n_containers or present:
        may_arrive = arrived < n_containers and (not present or (len(present) < cap and rng.random() < C.P_ARRIVAL))
        if may_arrive:
            events.append(("A", arrived))
            present.append(arrived)
            arrived += 1
        else:
            container = present.pop(rng.randrange(len(present)))
            events.append(("D", container))

    arrival = {c: t for t, (kind, c) in enumerate(events) if kind == "A"}
    departure = {c: t for t, (kind, c) in enumerate(events) if kind == "D"}
    mean_dwell = sum(departure[c] - arrival[c] for c in departure) / len(departure)
    return Instance(
        n_stacks=n_stacks, max_height=max_height, fill=fill, n_containers=n_containers, seed=seed,
        capacity=cap, events=tuple(events), arrival=arrival, departure=departure, mean_dwell=mean_dwell,
    )


def default_noise_seed(seed):
    return seed * C.NOISE_SEED_MULTIPLIER + C.NOISE_SEED_OFFSET


def estimate_departures(instance, sigma, noise_seed=None):
    """Geschätzte Abfahrt je Container: wahre Abfahrt + Gauß-Rauschen.

    sigma ist der Schätzfehler als Bruchteil der mittleren Standzeit (0.5 = die Schätzung liegt typisch
    eine halbe Standzeit daneben). Die Standardnormalen werden in Abfahrtsreihenfolge gezogen und mit
    sigma * mittlere Standzeit skaliert: dieselben Zufallszahlen, größeres sigma streckt nur die Fehler.
    """
    if sigma < 0:
        raise ValueError("sigma darf nicht negativ sein.")
    rng = random.Random(default_noise_seed(instance.seed) if noise_seed is None else noise_seed)
    scale = sigma * instance.mean_dwell
    return {c: d + rng.gauss(0.0, 1.0) * scale for c, d in instance.departure.items()}
