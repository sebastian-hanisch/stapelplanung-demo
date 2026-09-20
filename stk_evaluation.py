"""Auswertung: Regelvergleich auf einer Instanz, beste Regel, σ-Kurve, Kipppunkt, Urteil, Abstand zum Optimum.

Alles hier ist reine Rechnung ohne Streamlit; app.py legt die teuren Teile (sigma_sweep, solve_exact)
per st.cache_data ab.
"""

import statistics
from dataclasses import dataclass

import stk_constants as C
from stk_scenario import generate_instance
from stk_simulation import run_rule


# ---------------------------------------------------------------------------------------------------
# Vergleich auf einer Instanz
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class RuleOutcome:
    key: str
    label: str
    result: object          # stk_simulation.Result

    @property
    def moves(self):
        return self.result.moves


def compare_rules(instance, sigma, noise_seed=None):
    """Alle vier Regeln auf derselben Instanz und derselben Schätzung (mit aufgezeichnetem Verlauf)."""
    return tuple(
        RuleOutcome(key, C.RULE_LABELS[key], run_rule(instance, key, sigma, noise_seed, record=True))
        for key in C.RULE_KEYS
    )


def outcome_of(outcomes, key):
    return next(o for o in outcomes if o.key == key)


def best_rule(outcomes):
    """Regel mit den wenigsten Umstapelungen; bei Gleichstand die erste in C.TIE_PREFERENCE."""
    return min(outcomes, key=lambda o: (o.moves, C.TIE_PREFERENCE.index(o.key)))


@dataclass(frozen=True)
class Savings:
    baseline_moves: int
    best_moves: int
    saved: int              # >= 0
    saved_pct: float        # Anteil an der Alltagsregel, 0 wenn die Alltagsregel selbst 0 braucht


def savings(outcomes):
    base = outcome_of(outcomes, C.BASELINE_RULE).moves
    best = best_rule(outcomes).moves
    saved = base - best
    return Savings(base, best, saved, 100.0 * saved / base if base else 0.0)


@dataclass(frozen=True)
class RuleRow:
    key: str
    label: str
    moves: int
    moves_per_container: float
    share_with_move: float      # Anteil der Abholungen mit mindestens einer Umstapelung
    max_stack_height: int
    delta_moves: int            # meine Umstapelungen minus Alltagsregel
    delta_per_container: float


def comparison_rows(outcomes):
    """Tabellenzeilen; Delta immer 'meine Regel minus Referenz (Alltagsregel)'."""
    ref = outcome_of(outcomes, C.BASELINE_RULE).result
    return tuple(
        RuleRow(o.key, o.label, o.result.moves, o.result.moves_per_container, o.result.share_retrievals_with_move,
                o.result.max_stack_height, o.result.moves - ref.moves,
                o.result.moves_per_container - ref.moves_per_container)
        for o in outcomes
    )


# ---------------------------------------------------------------------------------------------------
# Abstand zum Optimum mit Hellsehen
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class OptimumGap:
    key: str
    label: str
    moves: int
    gap: int | None             # nur bei bewiesenem Optimum: moves - optimum
    ratio: float | None         # moves / optimum (None bei Optimum 0)
    gap_low: int                # Optimum liegt in [lower, upper] -> Abstand liegt in [moves - upper, moves - lower]
    gap_high: int


def vs_optimum(outcomes, exact):
    rows = []
    for o in outcomes:
        gap = o.moves - exact.optimum if exact.proven else None
        ratio = o.moves / exact.optimum if exact.proven and exact.optimum else None
        rows.append(OptimumGap(o.key, o.label, o.moves, gap, ratio, o.moves - exact.upper_bound,
                               o.moves - exact.lower_bound))
    return tuple(rows)


# ---------------------------------------------------------------------------------------------------
# σ-Kurve
# ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SweepResult:
    sigmas: tuple               # aufsteigend
    n_instances: int
    values: dict                # Regel -> Tupel über sigma von Tupeln über Instanzen (Umstapelungen pro Container)

    def series(self, rule, sigma_index):
        return self.values[rule][sigma_index]

    def mean(self, rule, sigma_index):
        return statistics.fmean(self.series(rule, sigma_index))

    def sem(self, rule, sigma_index):
        v = self.series(rule, sigma_index)
        return statistics.stdev(v) / len(v) ** 0.5 if len(v) > 1 else 0.0

    def paired_diff(self, rule_a, rule_b, sigma_index):
        """(Mittel, Standardfehler) von a - b über dieselben Instanzen."""
        d = [x - y for x, y in zip(self.series(rule_a, sigma_index), self.series(rule_b, sigma_index))]
        return statistics.fmean(d), (statistics.stdev(d) / len(d) ** 0.5 if len(d) > 1 else 0.0)

    def index_of(self, sigma):
        return min(range(len(self.sigmas)), key=lambda i: abs(self.sigmas[i] - sigma))


def sigma_sweep(n_stacks, max_height, fill, n_containers, sigma_current,
                n_instances=C.SWEEP_INSTANCES, sigmas=C.SWEEP_SIGMAS):
    """Umstapelungen pro Container je Regel über den Schätzfehler, für die eingestellte Blockgröße.

    Instanzen: Seeds 0 .. n_instances-1 (unabhängig vom eingestellten Seed). Das eingestellte sigma wird
    dem Raster hinzugefügt, damit die Kennzahlen dafür exakt und nicht interpoliert sind."""
    grid = tuple(sorted(set(sigmas) | {sigma_current}))
    instances = [generate_instance(n_stacks, max_height, fill, n_containers, seed) for seed in range(n_instances)]
    values = {key: [] for key in C.RULE_KEYS}
    for sigma in grid:
        for key in C.RULE_KEYS:
            values[key].append(tuple(run_rule(inst, key, sigma).moves_per_container for inst in instances))
    return SweepResult(grid, n_instances, {k: tuple(v) for k, v in values.items()})


def tipping_point(sweep, trusting=C.RULE_BESTFIT, ignoring=C.RULE_LOWEST):
    """Schätzfehler sigma, ab dem die schätzungsgläubige Regel gegen die ignorierende verliert.

    Lineare Interpolation des ersten Vorzeichenwechsels von (trusting - ignoring) auf dem Raster.
    0.0, wenn sie schon bei sigma = 0 nicht besser ist; None, wenn sie im ganzen Raster besser bleibt."""
    diffs = [sweep.mean(trusting, i) - sweep.mean(ignoring, i) for i in range(len(sweep.sigmas))]
    if diffs[0] >= 0:
        return 0.0
    for i in range(len(diffs) - 1):
        if diffs[i] < 0 <= diffs[i + 1]:
            s0, s1 = sweep.sigmas[i], sweep.sigmas[i + 1]
            return s0 + (s1 - s0) * (-diffs[i]) / (diffs[i + 1] - diffs[i])
    return None


@dataclass(frozen=True)
class InformationValue:
    at_zero: float              # Zufällig - Bestfit bei sigma = 0 (Umstapelungen pro Container): Wert exakter Kenntnis
    at_sigma: float             # dasselbe beim eingestellten sigma
    at_zero_factor: float | None    # Zufällig / Bestfit bei sigma = 0
    at_sigma_factor: float | None


def information_value(sweep, sigma):
    i0, i1 = 0, sweep.index_of(sigma)
    zero_rand, zero_best = sweep.mean(C.RULE_RANDOM, i0), sweep.mean(C.RULE_BESTFIT, i0)
    sig_rand, sig_best = sweep.mean(C.RULE_RANDOM, i1), sweep.mean(C.RULE_BESTFIT, i1)
    return InformationValue(zero_rand - zero_best, sig_rand - sig_best,
                            zero_rand / zero_best if zero_best else None,
                            sig_rand / sig_best if sig_best else None)


@dataclass(frozen=True)
class Verdict:
    kind: str                   # "trust" | "tipped" | "unclear"
    diff: float                 # Bestfit - Niedrigster Stapel, Umstapelungen pro Container (negativ = Bestfit besser)
    se: float                   # Standardfehler der gepaarten Differenz
    saving_pct: float           # Bestfit spart so viele % gegenüber dem Ausgleich (negativ, wenn er mehr braucht)
    best_mean_rule: str         # Regel mit dem kleinsten Mittel unter den vieren
    aware_is_best: bool


def verdict(sweep, sigma):
    """Bewertung beim eingestellten sigma. 'Klar' heißt: Unterschied > VERDICT_Z Standardfehler der gepaarten
    Differenz. Sonst 'unclear' - lieber kein Urteil als eines, das im Rauschen liegt."""
    i = sweep.index_of(sigma)
    diff, se = sweep.paired_diff(C.RULE_BESTFIT, C.RULE_LOWEST, i)
    base = sweep.mean(C.RULE_LOWEST, i)
    if abs(diff) <= C.VERDICT_Z * se:
        kind = "unclear"
    else:
        kind = "trust" if diff < 0 else "tipped"
    means = {k: sweep.mean(k, i) for k in C.RULE_KEYS}
    best = min(means, key=lambda k: (means[k], C.TIE_PREFERENCE.index(k)))
    return Verdict(kind, diff, se, -100.0 * diff / base if base else 0.0, best, best == C.RULE_AWARE)


# ---------------------------------------------------------------------------------------------------
# Hilfen für die Blickansicht
# ---------------------------------------------------------------------------------------------------
def comparison_partner(outcomes):
    """Die Regel, die in der Blickansicht neben der Alltagsregel steht: die beste NICHT-Alltagsregel
    (ist die Alltagsregel selbst die beste, sieht man trotzdem, was die beste Alternative anders macht)."""
    others = [o for o in outcomes if o.key != C.BASELINE_RULE]
    return min(others, key=lambda o: (o.moves, C.TIE_PREFERENCE.index(o.key)))


def suggested_event(result):
    """Ereignisnummer (1-basiert), an der die Blickansicht startet: die Abholung mit Umstapelung bei der
    höchsten Belegung; gibt es keine, der Zeitpunkt mit der höchsten Belegung. Braucht record=True."""
    best_k, best_occ = None, -1
    for k, step in enumerate(result.steps, start=1):
        if step.kind == "D" and step.moved:
            occ = sum(len(s) for s in step.stacks)
            if occ > best_occ:
                best_k, best_occ = k, occ
    if best_k is not None:
        return best_k
    return max(range(1, len(result.steps) + 1), key=lambda k: (sum(len(s) for s in result.steps[k - 1].stacks), -k))


def describe_step(step, event_index, n_events):
    """Beschreibung des Ereignisses für die Blickansicht (Deutsch)."""
    head = f"Ereignis {event_index} von {n_events}: "
    if step is None:
        return head + "Der Block ist noch leer."
    if step.kind == "A":
        return head + f"Container {step.container} kommt an und wird auf Stapel {step.stack + 1} gelegt."
    if not step.moved:
        return head + f"Container {step.container} wird aus Stapel {step.stack + 1} abgeholt, ohne Umstapelung."
    n = len(step.moved)
    return head + (f"Container {step.container} wird aus Stapel {step.stack + 1} abgeholt, dafür "
                   f"{'muss 1 Container' if n == 1 else f'müssen {n} Container'} umgestapelt werden.")
