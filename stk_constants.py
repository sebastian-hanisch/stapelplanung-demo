"""Konstanten der Stapelplanung-Demo.

Die Erzeugungsparameter sind die der Messreihe (hafen-planung/messreihe_stapel), damit die dort
gemessenen Zahlen mit diesem Code reproduzierbar sind.
"""

# --- Ereignisfolge ---------------------------------------------------------------------------------
# Wahrscheinlichkeit, dass der nächste Schritt eine Ankunft ist (sonst holt ein zufälliger
# anwesender Container ab), solange Platz unter der Belegungsgrenze ist.
P_ARRIVAL = 0.55

# --- Abfahrtsschätzung -----------------------------------------------------------------------------
# Das Rauschen kommt aus einem eigenen Zufallsstrom. Standard-Seed: aus dem Ereignis-Seed abgeleitet,
# aber ein eigener Strom (die Ereignisfolge ändert sich nicht, wenn nur das Rauschen variiert wird).
NOISE_SEED_MULTIPLIER = 13
NOISE_SEED_OFFSET = 5

# --- Regeln ----------------------------------------------------------------------------------------
RULE_RANDOM = "zufaellig"
RULE_LOWEST = "niedrigster_stapel"
RULE_BESTFIT = "bestfit"
RULE_AWARE = "unsicherheitsbewusst"

RULE_KEYS = (RULE_RANDOM, RULE_LOWEST, RULE_BESTFIT, RULE_AWARE)
RULE_LABELS = {
    RULE_RANDOM: "Zufällig",
    RULE_LOWEST: "Niedrigster Stapel",
    RULE_BESTFIT: "Bestfit",
    RULE_AWARE: "Unsicherheits-bewusst",
}

# Referenz für die Ersparnis: die realistische Alltagsregel (Ausgleich der Stapelhöhen).
BASELINE_RULE = RULE_LOWEST

# Unsicherheits-bewusste Regel: Wahrscheinlichkeiten werden auf diese Stellen gerundet, damit
# praktisch gleich riskante Stapel nach dem zweiten Kriterium entschieden werden. Ist das Risiko
# darunter, gilt "möglichst enge Passung", sonst "niedrigster Stapel".
AWARE_P_DECIMALS = 2
AWARE_TIGHTFIT_BELOW_P = 0.3

# --- Auswertung (Kernabschnitt "Was ist die Abfahrtsinformation wert?") ----------------------------
# Rasterpunkte des Schätzfehlers sigma (Bruchteil der mittleren Standzeit); das eingestellte sigma kommt hinzu.
SWEEP_SIGMAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
# Instanzen je Rasterpunkt (Seeds 0 .. n-1, bewusst NICHT der eingestellte Seed)
SWEEP_INSTANCES = 30
# Ein Unterschied gilt als klar, wenn er mehr als VERDICT_Z Standardfehler der gepaarten Differenz beträgt.
VERDICT_Z = 2.0
# Bei Gleichstand der Umstapelungen gewinnt die in dieser Reihenfolge erste Regel (Alltagsregel zuerst,
# damit keine Scheinersparnis entsteht).
TIE_PREFERENCE = (RULE_LOWEST, RULE_BESTFIT, RULE_AWARE, RULE_RANDOM)

# --- Darstellung -----------------------------------------------------------------------------------
RULE_COLORS = {
    RULE_RANDOM: "#8a94a3",
    RULE_LOWEST: "#2a6fb0",
    RULE_BESTFIT: "#c77700",
    RULE_AWARE: "#2e7d4f",
}

RULE_DESCRIPTIONS = {
    RULE_RANDOM: "Legt jeden Container in irgendeinen Stapel mit Platz. Sie kennt nichts und ist die Untergrenze: "
                 "so viel kostet es, wenn Information keine Rolle spielt.",
    RULE_LOWEST: "Nimmt den Stapel mit den wenigsten Containern (Ausgleich der Höhen). Sie ignoriert die "
                 "Abfahrtsschätzung. Die realistische Alltagsregel und Referenz für die Ersparnis.",
    RULE_BESTFIT: "Sucht einen Stapel, auf dem sie nichts Früheres blockiert, und zwar möglichst eng: oben liegt "
                  "der Container mit der nächstspäteren geschätzten Abfahrt. Blockiert jeder Stapel, nimmt sie den "
                  "mit der spätesten obersten Abfahrt. Sie vertraut der Schätzung.",
    RULE_AWARE: "Wie Bestfit, kennt aber zusätzlich die Größe des Schätzfehlers σ und wählt den Stapel mit der "
                "kleinsten Wahrscheinlichkeit zu blockieren. Bei großem σ fällt sie auf den Ausgleich zurück.",
}

# Blockdarstellung: Farbe = wahre Abfahrtsreihenfolge unter den anwesenden Containern (dunkel = fährt als nächster)
BLOCK_COLOR_SOON = (31, 58, 95)
BLOCK_COLOR_LATE = (208, 224, 240)
BLOCK_STACK_BG = "#f0f2f5"
BLOCK_STACK_LINE = "#c9d1db"
MOVED_COLOR = "#e8850c"        # gerade umgestapelt
ARRIVED_COLOR = "#2e7d4f"      # gerade angekommen
BLOCK_LEGEND_TEXT = ("Farbe = wahre Abfahrtsreihenfolge (dunkel = fährt als nächster ab), Zahl = Rang der Abfahrt unter den "
                     "anwesenden Containern, oranger Rand = gerade umgestapelt, grüner Rand = gerade angekommen.")
OPTIMUM_COLOR = "#7a3fb0"
# Marker-Linien (eingestelltes sigma, Cursor): mittleres Grau, damit sie auf hellem UND dunklem Hintergrund sichtbar bleiben
MARKER_LINE_COLOR = "#808895"

BLOCK_FIGURE_TIER_PX = 38      # Pixelhöhe je Stapelebene
BLOCK_FIGURE_BASE_PX = 70
CHART_HEIGHT = 380

# --- Regler (Bereich als (min, max), Standardwert, Schrittweite) -----------------------------------
N_STACKS_RANGE, N_STACKS_DEFAULT = (3, 8), 6
MAX_HEIGHT_RANGE, MAX_HEIGHT_DEFAULT = (3, 6), 5
FILL_PCT_RANGE, FILL_PCT_DEFAULT, FILL_PCT_STEP = (40, 100), 80, 5          # ganze Prozent; erst beim Verbrauchen /100
N_CONTAINERS_RANGE, N_CONTAINERS_DEFAULT, N_CONTAINERS_STEP = (20, 300), 120, 10
SIGMA_PCT_RANGE, SIGMA_PCT_DEFAULT, SIGMA_PCT_STEP = (0, 200), 25, 5        # ganze Prozent der mittleren Standzeit
SEED_RANGE, SEED_DEFAULT = (0, 9999), 7

# Beispielszenarien (Schnellstart). Seeds per Sweep abgestimmt (tools/tune_presets.py): typisch, nicht der schoenste Einzelfall,
# und rauschstabil (Aussage haelt bei >= 90 % anderer Rausch-Ziehungen).
PRESETS = {
    "Perfekte Info": dict(n_stacks=6, max_height=5, fill_pct=80, n_containers=120, sigma_pct=0, seed=7),
    "Realistisch": dict(n_stacks=6, max_height=5, fill_pct=80, n_containers=120, sigma_pct=25, seed=7),
    "Kaum brauchbar": dict(n_stacks=6, max_height=5, fill_pct=60, n_containers=120, sigma_pct=150, seed=7),
    "Voller Block": dict(n_stacks=6, max_height=5, fill_pct=100, n_containers=120, sigma_pct=0, seed=7),
    "Kleiner Block": dict(n_stacks=4, max_height=4, fill_pct=100, n_containers=30, sigma_pct=0, seed=30),
}
EXACT_PRESET = "Kleiner Block"

# Zeitlimit des Exakt-Tabs in Sekunden (die App liest es zur Laufzeit, Tests dürfen es kürzen)
EXACT_TIME_LIMIT_SECONDS = 10.0
