"""
Stapelplanung im Containerblock – interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Welle 1 der Hafen-Linie (Kaiplatz-Zuteilung, Containerbrücken-Einsatz, Lkw-Terminvergabe, Hof-Disposition):
hier eine Ebene tiefer im Terminal, im Stapelblock des Yards. Frage: Wo lagert man einen ankommenden
Container ein, wenn man seine Abfahrt nur ungefähr kennt? Jede Umstapelung ist ein unproduktiver Kranhub.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import stk_constants as C
from stk_evaluation import (best_rule, compare_rules, comparison_partner, comparison_rows, describe_step, information_value,
                            outcome_of, savings, sigma_sweep, suggested_event, tipping_point, verdict, vs_optimum)
from stk_exact import solve_exact
from stk_pdf_export import generate_stacking_pdf
from stk_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed,
                         sync_query_params)
from stk_scenario import estimate_departures, generate_instance
from stk_ui_panel import render_rule_panel
from stk_visualization import block_figure, block_title, rule_bar_figure, sigma_curve_figure, state_at

st.set_page_config(page_title="Stapelplanung – Sebastian Hanisch", layout="wide")

SCENARIO_KEYS = ["n_stacks_slider", "max_height_slider", "fill_slider", "n_containers_slider", "sigma_slider", "seed_input"]


@st.cache_data(show_spinner=False)
def _compute_scenario(scenario_key):
    n_stacks, max_height, fill_pct, n_containers, sigma_pct, seed = scenario_key
    instance = generate_instance(n_stacks, max_height, fill_pct / 100, n_containers, seed)
    return instance, compare_rules(instance, sigma_pct / 100)


@st.cache_data(show_spinner=False)
def _compute_sweep(n_stacks, max_height, fill_pct, n_containers, sigma_pct):
    return sigma_sweep(n_stacks, max_height, fill_pct / 100, n_containers, sigma_pct / 100)


@st.cache_data(show_spinner=False)
def _compute_exact(scenario_key):
    """Getrennt von der Regelrechnung: läuft nur auf Klick, denn bei großen Blöcken kann die Suche das Zeitlimit brauchen."""
    n_stacks, max_height, fill_pct, n_containers, _sigma_pct, seed = scenario_key
    return solve_exact(generate_instance(n_stacks, max_height, fill_pct / 100, n_containers, seed),
                       time_limit=C.EXACT_TIME_LIMIT_SECONDS)


st.title("📦 Stapelplanung im Containerblock")
st.markdown(
    """
Ein Container kommt an und muss in einen Stapel des Blocks - aber **wann er abgeholt wird, weiß man nur
ungefähr**. Liegt später ein früher abfahrender Container darunter, muss er beim Abholen erst
**umgestapelt** werden: ein unproduktiver Kranhub. Diese Demo vergleicht vier Einlagerungsregeln, von
"irgendwohin" bis zu einer Regel, die der **Abfahrtsschätzung** traut, und zeigt, was Vorwissen wert ist - und
ab welcher Ungenauigkeit man ihm besser nicht mehr traut. Wie das Modell funktioniert, steht im Expander
"Wie funktioniert diese Demo?" weiter unten, die formale Herleitung im Expander "📐 Mathematische Formulierung".
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
PRESET_HELP = {
    "Perfekte Info": "Die Abfahrt jedes Containers ist exakt bekannt - wer sie nutzt, stapelt fast ohne Umstapeln.",
    "Realistisch": "Die Abfahrt ist nur auf etwa ein Viertel der Standzeit genau bekannt - der Vorsprung schrumpft, bleibt aber.",
    "Kaum brauchbar": "Die Schätzung liegt typisch mehr als eine Standzeit daneben - hier schlägt die simple Regel die schätzungsgläubige.",
    "Voller Block": "Der Block ist bis an die Grenze gefüllt - selbst mit exaktem Vorwissen bleibt viel Umstapeln.",
    "Kleiner Block": "Ein kleiner Block, für den der Exakt-Tab das Optimum berechnen kann.",
}
# Je Zeile drei Schaltflächen: bei fünf in einer Zeile werden die Namen in schmalen Fenstern abgeschnitten.
preset_names = list(C.PRESETS.keys())
for row_start in range(0, len(preset_names), 3):
    row = st.columns(3)
    for col, name in zip(row, preset_names[row_start:row_start + 3]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_stacks = st.slider("Anzahl Stapel", *bounds("n_stacks_slider"), key="n_stacks_slider")
    max_height = st.slider("Maximale Stapelhöhe", *bounds("max_height_slider"), key="max_height_slider")
    fill_pct = st.slider(
        "Füllgrad des Blocks (%)", *bounds("fill_slider"), step=C.FILL_PCT_STEP, format="%d%%", key="fill_slider",
        help="Wie voll der Block höchstens wird, gemessen an (Stapel - 1) x Höhe. Ein Stapel bleibt als Platz zum "
        "Umstapeln frei - ohne diese Grenze könnte man nicht immer ausweichen.",
    )
    n_containers = st.slider(
        "Anzahl Container (Durchsatz)", *bounds("n_containers_slider"), step=C.N_CONTAINERS_STEP, key="n_containers_slider",
        help="Wie viele Container über den ganzen Ablauf ankommen und wieder abgeholt werden.",
    )
    seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)

    st.markdown("**Abfahrtsschätzung**")
    sigma_pct = st.slider(
        "Schätzfehler der Abfahrt (% der mittleren Standzeit)", *bounds("sigma_slider"), step=C.SIGMA_PCT_STEP, format="%d%%",
        key="sigma_slider",
        help="0 % = die Abfahrt ist exakt bekannt. 50 % = die Schätzung liegt typisch eine halbe mittlere Standzeit "
        "daneben. Größenordnung zum Einordnen, nicht an Echtdaten gemessen.",
    )

    st.button(
        "🎲 Neuen Block generieren", width="stretch", on_click=randomize_seed,
        help="Würfelt einen neuen Zufalls-Seed für die Ereignisfolge (Ankünfte und Abholungen).",
    )

sync_query_params({key: st.session_state[key] for key in SCENARIO_KEYS})

scenario_key = (int(n_stacks), int(max_height), int(fill_pct), int(n_containers), int(sigma_pct), int(seed))

with st.spinner("Simuliere den Block..."):
    instance, outcomes = _compute_scenario(scenario_key)

baseline = outcome_of(outcomes, C.BASELINE_RULE)
best = best_rule(outcomes)
saved = savings(outcomes)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht
# ---------------------------------------------------------------------------------------------------
st.markdown("## 🎯 Weniger Umstapelungen mit der besten Regel")
st.caption(f"Beste Regel: **{best.label}** - wird bei jedem Lauf neu anhand der Umstapelungen bestimmt.")

m1, m2, m3 = st.columns(3)
m1.metric(
    best.label, f"{best.moves}",
    delta=None if best.key == baseline.key else f"{best.moves - baseline.moves:+d} ({-saved.saved_pct:+.0f} %)", delta_color="inverse",
    help="Umstapelungen der besten Regel für diese Ereignisfolge.",
)
m2.metric("Alltagsregel", f"{baseline.moves}", help=f"{baseline.label}: die realistische Alltagsregel und Referenz für die Ersparnis.")
m3.metric(
    "pro Container", f"{best.result.moves_per_container:.2f}",
    delta=None if best.key == baseline.key else f"{best.result.moves_per_container - baseline.result.moves_per_container:+.2f}",
    delta_color="inverse", help=f"Umstapelungen pro Container bei {best.label}.",
)

if saved.saved > 0:
    st.success(
        f"🏗️ **{best.label}** spart hier **{saved.saved} Umstapelungen** ({saved.saved_pct:.0f} %) gegenüber der "
        f"Alltagsregel '{baseline.label}' - jede davon ist ein Kranhub, der nichts bewegt."
    )
elif baseline.moves == 0:
    st.info("ℹ️ In diesem Szenario braucht auch die Alltagsregel keine Umstapelung - bei so wenig Belegung liegt "
            "nie ein früher abfahrender Container unten. Stellen Sie mehr Container oder einen volleren Block ein.")
else:
    st.info("ℹ️ Hier schlägt keine Regel die Alltagsregel: Die Schätzung ist zu ungenau, um sie zu nutzen. Der Kernabschnitt "
            "unten zeigt, ab welchem Schätzfehler das passiert.")

st.markdown("#### 🔍 Blick in den Block")
partner = comparison_partner(outcomes)
if st.session_state.get("event_owner") != scenario_key:
    st.session_state["event_slider"] = suggested_event(baseline.result)
    st.session_state["event_owner"] = scenario_key
event = st.slider(
    "Ereignis", 0, instance.n_events, key="event_slider",
    help="Ein Ereignis ist eine Ankunft oder eine Abholung. Startpunkt: eine Abholung mit Umstapelung bei hoher Belegung.",
)
estimates = estimate_departures(instance, sigma_pct / 100)
left, right = st.columns(2)
for col, outcome, side in ((left, baseline, "left"), (right, partner, "right")):
    with col:
        stacks, moved, arrived, step = state_at(instance, outcome.result, event)
        so_far = step.moves_so_far if step is not None else 0
        st.plotly_chart(
            block_figure(stacks, instance.max_height, instance.departure, block_title(outcome.label, so_far), moved, arrived, estimates),
            width="stretch", key=f"block_chart_{side}",
        )
        st.caption(describe_step(step, event, instance.n_events))
st.caption(
    f"Links die Alltagsregel, rechts {'die beste Regel' if partner.key == best.key else 'die beste Alternative'} "
    f"({partner.label}). {C.BLOCK_LEGEND_TEXT}"
)

st.download_button(
    "📄 Ergebnis als PDF herunterladen", data=generate_stacking_pdf(instance, outcomes, scenario_key[4]),
    file_name="stapelplanung_ergebnis.pdf", mime="application/pdf", key="primary_pdf_download",
)

st.caption(
    f"Ermittelt mit der besten von {len(outcomes)} eigenen Regeln für diese Ereignisfolge. Welche Regel im Mittel vorn liegt, "
    "zeigt der Kernabschnitt darunter; Details zu allen Regeln und der Vergleich mit dem Optimum stehen im Methodenvergleich unten."
)

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt
# ---------------------------------------------------------------------------------------------------
st.subheader("📐 Was ist die Abfahrtsinformation wert?")
st.markdown(
    """
Kernfrage dieser Demo: **Bestfit** vertraut der Abfahrtsschätzung, **Niedrigster Stapel** ignoriert sie und gleicht
nur die Höhen aus. Bei exakter Kenntnis gewinnt Bestfit klar. Aber jede Schätzung hat einen Fehler - und irgendwann
lohnt es sich nicht mehr, ihr zu trauen. Hier live für Ihre Blockgröße gerechnet (nicht nur behauptet):
"""
)
with st.spinner("Rechne die Kurve über den Schätzfehler..."):
    sweep = _compute_sweep(scenario_key[0], scenario_key[1], scenario_key[2], scenario_key[3], scenario_key[4])
sigma = sigma_pct / 100
tip = tipping_point(sweep)
info = information_value(sweep, sigma)
v = verdict(sweep, sigma)

k1, k2, k3 = st.columns(3)
k1.metric(
    "Vorsprung (σ = 0 %)", f"{info.at_zero_factor:.1f}×" if info.at_zero_factor else "—",
    help="Zufälliges Einlagern braucht so viel mal mehr Umstapelungen als Bestfit bei exakt bekannter Abfahrt.",
)
k2.metric(
    f"Vorsprung (σ = {int(sigma_pct)} %)", f"{info.at_sigma_factor:.1f}×" if info.at_sigma_factor else "—",
    help="Dasselbe Verhältnis (Zufällig zu Bestfit) beim eingestellten Schätzfehler.",
)
if tip is None:
    k3.metric("Kipppunkt", "keiner bis 200 %", help="Im ganzen betrachteten Bereich bleibt Bestfit besser als der einfache Ausgleich.")
else:
    k3.metric(
        "Kipppunkt", f"{tip * 100:.0f} %",
        help="Ab diesem Schätzfehler braucht Bestfit im Mittel mehr Umstapelungen als der einfache Ausgleich "
        "(lineare Interpolation zwischen den Rasterpunkten).",
    )

st.plotly_chart(sigma_curve_figure(sweep, sigma, tip), width="stretch", key="sigma_curve_chart")
st.caption(
    f"Basis: {sweep.n_instances} Ereignisfolgen (Seeds 0-{sweep.n_instances - 1}) mit Ihrer Blockgröße - nicht Ihr aktueller Seed. "
    "Band = ± 1 Standardfehler. σ = 25-50 % entspricht einer Prognose, die typisch um ein Viertel bis eine halbe Standzeit "
    "danebenliegt; das ist eine Größenordnung, nicht an Echtdaten gemessen."
)

if v.kind == "trust":
    st.success(
        f"✅ Der Schätzung zu trauen lohnt sich hier noch: Bestfit braucht im Mittel **{v.saving_pct:.0f} % weniger** Umstapelungen "
        f"als der einfache Ausgleich ({-v.diff:.2f} pro Container, Standardfehler {v.se:.2f})."
    )
elif v.kind == "tipped":
    st.warning(
        f"⚠️ Die Schätzung ist hier zu ungenau: Bestfit braucht im Mittel **{-v.saving_pct:.0f} % mehr** Umstapelungen als der "
        f"einfache Ausgleich ({v.diff:.2f} pro Container, Standardfehler {v.se:.2f}). Jenseits des Kipppunkts ist die simple Regel besser."
    )
else:
    st.info(
        f"ℹ️ Kein klarer Unterschied zwischen Bestfit und dem einfachen Ausgleich: die Differenz ({v.diff:+.2f} pro Container) "
        f"liegt innerhalb des Rauschens (Standardfehler {v.se:.2f}). Genau hier, um den Kipppunkt, ist die Schätzung gerade so gut wie keine."
    )
if v.aware_is_best:
    st.info("🧠 Die **unsicherheits-bewusste Regel** hat hier das kleinste Mittel: Sie kennt die Größe des Schätzfehlers und "
            "fällt bei großem σ auf den Ausgleich zurück, statt der Schätzung blind zu trauen.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Methodenvergleich
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tab_labels = [o.label for o in outcomes] + ["🧮 Exakt (IDA*-artig)", "📊 Vergleich"]
    tabs = st.tabs(tab_labels)

    for tab, outcome in zip(tabs[: len(outcomes)], outcomes):
        with tab:
            render_rule_panel(f"rule_{outcome.key}", outcome, outcomes)

    tab_exact, tab_compare = tabs[len(outcomes)], tabs[len(outcomes) + 1]

    exact_result = None
    with tab_exact:
        st.caption(
            "Das Optimum mit Hellsehen: die kleinstmögliche Zahl an Umstapelungen, wenn man alle wahren Abfahrten UND die ganze "
            "Ankunftsfolge im Voraus kennt und jede Entscheidung frei treffen darf. Keine Online-Regel kann das erreichen - es ist "
            f"die untere Schranke. Auf {C.EXACT_TIME_LIMIT_SECONDS:g} s begrenzt; bei großen Blöcken zeigt der Tab dann ein Intervall "
            "statt eines Werts (nie einen unbewiesenen Wert als Optimum)."
        )
        if st.button("🧮 Optimum mit Hellsehen berechnen", key="stk_exact_btn"):
            st.session_state["stk_exact_scenario_key"] = scenario_key

        if st.session_state.get("stk_exact_scenario_key") == scenario_key:
            with st.spinner(f"Exakte Suche (bis zu {C.EXACT_TIME_LIMIT_SECONDS:g} s)..."):
                exact_result = _compute_exact(scenario_key)
            if exact_result.proven:
                st.info(
                    f"✅ Optimum mit Hellsehen: **{exact_result.optimum}** Umstapelungen (in {exact_result.seconds:.1f} s bewiesen). "
                    f"Die beste Online-Regel ({best.label}) braucht {best.moves}, die Alltagsregel {baseline.moves}. "
                    "Das Optimum kennt auch die künftigen Ankünfte - die Lücke ist zu einem großen Teil der Preis des Nicht-Wissens, "
                    "kein Verbesserungsspielraum für eine Online-Regel."
                )
            else:
                st.warning(
                    f"⏱️ {exact_result.limit_reason} nach {exact_result.seconds:.0f} s, kein Beweis: Das Optimum liegt zwischen "
                    f"**{exact_result.lower_bound}** und **{exact_result.upper_bound}** Umstapelungen. Für einen genauen Wert den Block "
                    "verkleinern."
                )
                st.button("Auf exakt lösbare Größe setzen", key="stk_exact_shrink_btn", on_click=apply_preset, args=(C.EXACT_PRESET,),
                          help="Lädt das Beispielszenario 'Kleiner Block', für das der Exakt-Tab das Optimum berechnen kann.")
            st.plotly_chart(rule_bar_figure(outcomes, exact_result), width="stretch", key="exact_bar_chart")
            gap_rows = vs_optimum(outcomes, exact_result)
            st.dataframe(
                pd.DataFrame([
                    {"Regel": r.label, "Umstapelungen": r.moves,
                     "Abstand zum Optimum": (f"+{r.gap}" if r.gap is not None else f"zwischen {r.gap_low:+d} und {r.gap_high:+d}")}
                    for r in gap_rows
                ]),
                width="stretch", hide_index=True,
            )
        elif "stk_exact_scenario_key" in st.session_state:
            st.info("ℹ️ Die zuletzt berechnete exakte Lösung bezog sich auf ein anderes Szenario - Einstellungen geändert? "
                    "Erneut auf '🧮 Optimum mit Hellsehen berechnen' klicken.")
        else:
            st.info("Noch nichts berechnet – auf den Button oben klicken.")

    with tab_compare:
        rows = comparison_rows(outcomes)
        table = pd.DataFrame([
            {"Regel": r.label, "Umstapelungen": r.moves, "pro Container": round(r.moves_per_container, 3),
             "Abholungen mit Umstapelung": f"{r.share_with_move * 100:.0f} %", "Höchster Stapel": r.max_stack_height,
             f"Differenz zu '{baseline.label}'": r.delta_moves}
            for r in rows
        ])
        st.dataframe(table, width="stretch", hide_index=True)
        st.plotly_chart(rule_bar_figure(outcomes, exact_result), width="stretch", key="comparison_bar_chart")
        if exact_result is None:
            st.caption("Das Optimum mit Hellsehen erscheint hier, sobald es im Tab '🧮 Exakt' berechnet wurde.")

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        """
Ein **Block** besteht aus mehreren **Stapeln** begrenzter Höhe. Von einem Stapel ist nur der oberste Container
erreichbar. Container **kommen an** und werden **abgeholt**, in einer zufälligen Folge; wie voll der Block dabei
höchstens wird, legt der **Füllgrad** fest. Wird ein Container abgeholt, der unter anderen liegt, müssen die darüber
liegenden erst **umgestapelt** werden - jeder solche Hub zählt als eine Umstapelung.

Die Regel entscheidet beim Ankommen nur mit einer **Schätzung** der Abfahrt: der wahren Abfahrt plus ein Fehler, dessen
Größe der Regler "Schätzfehler" in Bruchteilen der mittleren Standzeit vorgibt. Abgeholt wird in der wahren Reihenfolge.

Vier Regeln stehen zur Auswahl (im Expander "Wie wir das erreichen" alle nebeneinander):

- **Zufällig**: irgendein Stapel mit Platz - die Untergrenze ohne Information.
- **Niedrigster Stapel**: der Stapel mit den wenigsten Containern - die realistische Alltagsregel, sie ignoriert die Schätzung.
- **Bestfit**: sucht einen Stapel, auf dem sie nichts Früheres blockiert, möglichst eng; sonst den mit der spätesten obersten
  Abfahrt.
- **Unsicherheits-bewusst**: wie Bestfit, nutzt aber die Größe des Schätzfehlers und wählt den Stapel mit der kleinsten
  Blockierwahrscheinlichkeit.

Beim Abholen entscheidet für **alle** Regeln dieselbe Regel (Bestfit), wohin ein Blocker kommt; so misst der Vergleich nur die
Einlagerungsentscheidung. Die Hauptansicht zeigt die für diese Ereignisfolge beste Regel neben der Alltagsregel; im Diagramm
"Blick in den Block" bedeutet die Zahl den Rang der wahren Abfahrt unter allen anwesenden Containern (1 = fährt als nächster ab).

Das **Optimum mit Hellsehen** im Tab "Exakt" kennt zusätzlich die künftigen Ankünfte. Es ist eine untere Schranke und für
Online-Regeln nicht erreichbar.

**Der Kernabschnitt** rechnet für Ihre Blockgröße die Umstapelungen pro Container über den Schätzfehler, gemittelt über 30
Ereignisfolgen (nicht Ihr aktueller Seed). Der **Kipppunkt** ist die Stelle, an der Bestfit im Mittel schlechter wird als der
einfache Ausgleich. Das Urteil darunter nennt einen Unterschied nur dann klar, wenn er mehr als zwei Standardfehler beträgt - liegt
er im Rauschen, steht dort "Kein klarer Unterschied".

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- Die **Abholreihenfolge ist zufällig**. In echten Blöcken werden Container meist nach Schiff oder Zielgruppe gebündelt und getrennt
  gelagert; das senkt die Umstapelungen stark und ist hier nicht abgebildet.
- Der **Schätzfehler ist gaußverteilt** und ohne Schiefe. Reale Standzeiten sind schief verteilt.
- Es gibt **einen Block**, keine Fahrzeiten und Kranwege, keine Gefahrgut-, Reefer- oder Gewichtsklassen.
- **Kipppunkt und Vorsprung hängen von Blockgröße, Füllgrad und Durchsatz ab.** Sie sind kein Naturgesetz; deshalb wird die Kurve
  live für Ihre Einstellung gerechnet.
- Alle Zahlen sind **Größenordnungen aus einer Simulation, keine Messung an Echtdaten.** Ein Schätzfehler von 25-50 % ist ein Wert zum
  Einordnen, nicht ein gemessener.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Stapelplanung mit Umstapelung** (Blocks Relocation Problem mit ankommenden Containern), NP-schwer im Allgemeinen.

Gegeben Container $i = 1, \dots, n$ mit Ankunft $a_i$ und Abholung $d_i$ (Indizes in der Ereignisfolge, $a_i < d_i$), ein Block
aus $S$ Stapeln der Höhe $H$. Zu jedem Zeitpunkt sind höchstens $\text{cap} = \lfloor \varphi\,(S-1)\,H \rceil$ Container
anwesend, mit Füllgrad $\varphi \le 1$. **Ausführbarkeit:** Liegen beim Abholen $k$ Container über dem Ziel in Stapel $x$ und
sind insgesamt $m \le (S-1)H + 1$ Container anwesend, so sind außerhalb von $x$ mindestens $S H - m - (H - |x|) \ge |x| - 1 \ge k$
Plätze frei, das Umstapeln gelingt also immer.

**Schätzung:** $\hat d_i = d_i + \varepsilon_i$, $\varepsilon_i \sim \mathcal N\big(0, (\sigma \bar D)^2\big)$ mit mittlerer Standzeit
$\bar D = \frac1n \sum_i (d_i - a_i)$ und Schätzfehler $\sigma$ (Regler, in $\%$).

**Zielfunktion:** Zahl der Umstapelungen
$$
\min \; \sum_{j} |B_j|, \qquad B_j = \{\text{Container über dem bei Abholung } j \text{ abgeholten Container}\}.
$$

**Regeln** für einen ankommenden Container mit Schätzung $\hat e$; $\text{top}(s)$ ist die geschätzte Abfahrt des obersten Containers
von Stapel $s$ (leerer Stapel: $\infty$):

- Bestfit: $s^\* = \arg\min\{\text{top}(s) : \text{top}(s) \ge \hat e\}$, falls die Menge nicht leer ist, sonst $\arg\max_s \text{top}(s)$.
- Unsicherheits-bewusst: $s^\* = \arg\min_s P_s$ mit der Blockierwahrscheinlichkeit
  $P_s = \Phi\!\Big(\dfrac{\hat e - \text{top}(s)}{\sigma \bar D \sqrt 2}\Big)$.

**Optimum mit Hellsehen:** Rekursion über den Zustand $(t, X)$ aus Ereignisindex und Multimenge der Stapel,
$V(t, X)$ = minimale Restkosten; bei Ankunft das Minimum über alle Stapel, bei Abholung Kosten $|B|$ plus das Minimum
über alle Verteilungen der Blocker auf die anderen Stapel. Gelöst als **IDA\***: iterative Vertiefung über das Budget
$b$, Machbarkeitsfrage "gibt es eine Fortsetzung mit höchstens $b$ Umstapelungen?", mit der zulässigen unteren Schranke

$$
h(X) = \big|\{\, c \in X : c \text{ liegt über einem früher abfahrenden Container im selben Stapel} \,\}\big|,
$$

denn jeder solche Container muss mindestens einmal umgestapelt werden. Das erste machbare Budget ist das Optimum. Bei
Zeitlimit liefert das zuletzt begonnene Budget eine bewiesene untere Schranke, ein Bestfit-Lauf mit wahren Abfahrten die obere.

**Einsicht:** Kommen alle Container vor der ersten Abholung, ist eine Belegung ohne Umstapeln genau dann möglich, wenn sich die
Ankunftsfolge (nach Abfahrt geordnet) in höchstens $S$ fallende Teilfolgen zerlegen lässt, also die längste steigende Teilfolge
höchstens $S$ lang ist. Im verschränkten Ablauf dieser Demo gilt das nicht so einfach.

Implementiert in `stk_exact.py` (Suche), `stk_rules.py` (Regeln) und `stk_simulation.py` (Ablauf).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
