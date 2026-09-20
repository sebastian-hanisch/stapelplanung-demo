"""End-to-end-Tests über Streamlits offizielles AppTest-Framework: laden app.py wirklich und klicken durch.

Fängt, was Unit-Tests nicht sehen können: doppelte Widget-IDs (StreamlitDuplicateElementId bei st.plotly_chart ohne key),
Slider mit Wert außerhalb der Grenzen (z. B. ein Preset, das die Reglergrenzen verletzt), Slider mit min == max."""

import os

import pytest
from streamlit.testing.v1 import AppTest

import stk_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
FOOTER = ("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
          "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
          "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)")
SCENARIO_KEYS = ["n_stacks_slider", "max_height_slider", "fill_slider", "n_containers_slider", "sigma_slider", "seed_input"]


def _run(setup=None):
    at = AppTest.from_file(APP_PATH)
    if setup:
        setup(at)
    at.run(timeout=180)
    return at


def _ok(at):
    assert not at.exception, [str(e.value) for e in at.exception]


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def _settings(at):
    return {k: at.session_state[k] for k in SCENARIO_KEYS}


def _scenario(**values):
    """setup-Funktion: Permalink-Laden abschalten und Regler direkt setzen."""
    def setup(at):
        at.session_state["permalink_loaded"] = True
        for k, v in values.items():
            at.session_state[k] = v
    return setup


# ---------- Skelett ----------
def test_default_load_has_no_exception_and_follows_the_portfolio_skeleton():
    at = _run()
    _ok(at)
    assert at.title[0].value == "📦 Stapelplanung im Containerblock"
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]                 # genau EIN Header in der Seitenleiste
    assert [b.label for b in at.button[:5]] == list(C.PRESETS)                           # Presets im Hauptbereich, vor allem anderen
    assert at.button[-1].label == "🎲 Neuen Block generieren"                             # letztes Element der Seitenleiste
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – vollständiger Methodenvergleich",
                                              "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert [s.value for s in at.subheader] == ["📐 Was ist die Abfahrtsinformation wert?"]
    assert any(m.value.startswith("## 🎯") for m in at.markdown)
    assert at.caption[-1].value == FOOTER                                                 # Footer wörtlich


def test_no_dead_file_links_in_markdown():
    at = _run()
    for m in at.markdown:
        assert ".py](" not in m.value, "toter Dateilink in st.markdown (die App kann Repo-Dateien nicht ausliefern)"


def test_default_main_view_numbers_match_the_measurement():
    at = _run()
    labels = {m.label: m for m in at.metric}
    assert labels["Bestfit"].value == "65" and labels["Bestfit"].delta == "-29 (-31 %)"
    assert labels["Alltagsregel"].value == "94"
    assert any("spart hier **29 Umstapelungen**" in s.value for s in at.success)


def test_preset_names_are_short_enough_for_narrow_windows():
    """Bei 800 px Breite passen in eine Drittelspalte etwa 16 Zeichen; längere Namen wurden als 'Perfek...' abgeschnitten."""
    assert all(len(name) <= 16 for name in C.PRESETS)


# ---------- Presets ----------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_loads_sets_the_widgets_and_syncs_the_address_bar(name):
    at = _run()
    _button(at, name).click()
    at.run(timeout=180)
    _ok(at)
    p = C.PRESETS[name]
    assert _settings(at) == dict(n_stacks_slider=p["n_stacks"], max_height_slider=p["max_height"], fill_slider=p["fill_pct"],
                                 n_containers_slider=p["n_containers"], sigma_slider=p["sigma_pct"], seed_input=p["seed"])
    assert dict(at.query_params) == {"ns": [str(p["n_stacks"])], "mh": [str(p["max_height"])], "fp": [str(p["fill_pct"])],
                                     "nc": [str(p["n_containers"])], "sg": [str(p["sigma_pct"])], "seed": [str(p["seed"])]}


def test_randomize_button_changes_only_the_seed():
    at = _run()
    before = _settings(at)
    _button(at, "🎲 Neuen Block generieren").click()
    at.run(timeout=180)
    _ok(at)
    after = _settings(at)
    assert {k: v for k, v in after.items() if k != "seed_input"} == {k: v for k, v in before.items() if k != "seed_input"}
    assert 0 <= after["seed_input"] <= 9999


# ---------- Permalink ----------
def test_permalink_is_loaded_clamped_and_snapped():
    def setup(at):
        at.query_params.update({"ns": "4", "fp": "83", "sg": "999", "nc": "abc", "mh": "3", "seed": "7"})
    at = _run(setup)
    _ok(at)
    s = _settings(at)
    assert s["n_stacks_slider"] == 4 and s["max_height_slider"] == 3 and s["seed_input"] == 7
    assert s["fill_slider"] == 85                       # 83 -> nächste Schrittweite
    assert s["sigma_slider"] == 200                     # 999 -> Obergrenze
    assert s["n_containers_slider"] == C.N_CONTAINERS_DEFAULT      # unlesbar -> Standard


# ---------- Reglergrenzen ----------
@pytest.mark.parametrize("extreme", ["min", "max"])
def test_every_slider_at_its_extreme_renders_without_exception(extreme):
    ranges = {"n_stacks_slider": C.N_STACKS_RANGE, "max_height_slider": C.MAX_HEIGHT_RANGE, "fill_slider": C.FILL_PCT_RANGE,
              "n_containers_slider": C.N_CONTAINERS_RANGE, "sigma_slider": C.SIGMA_PCT_RANGE, "seed_input": C.SEED_RANGE}
    at = _run(_scenario(**{k: (lo if extreme == "min" else hi) for k, (lo, hi) in ranges.items()}))
    _ok(at)
    n = C.N_CONTAINERS_RANGE[0] if extreme == "min" else C.N_CONTAINERS_RANGE[1]
    assert at.slider(key="event_slider").max == 2 * n


@pytest.mark.parametrize("combo", [dict(n_stacks_slider=3, max_height_slider=3, fill_slider=40, n_containers_slider=20),
                                   dict(n_stacks_slider=8, max_height_slider=6, fill_slider=100, n_containers_slider=300),
                                   dict(n_stacks_slider=3, max_height_slider=6, fill_slider=100, n_containers_slider=20),
                                   dict(n_stacks_slider=8, max_height_slider=3, fill_slider=40, n_containers_slider=300)])
def test_extreme_block_combinations_render(combo):
    _ok(_run(_scenario(**combo)))


# ---------- Blick in den Block ----------
def test_event_slider_starts_at_a_relocation_and_resets_when_the_scenario_changes():
    at = _run()
    assert at.slider(key="event_slider").value == 95
    at.slider(key="event_slider").set_value(0)
    at.run(timeout=180)
    _ok(at)
    assert any("Der Block ist noch leer" in c.value for c in at.caption)
    at.slider(key="event_slider").set_value(240)
    at.run(timeout=180)
    _ok(at)
    at.slider(key="sigma_slider").set_value(50)                      # anderes Szenario -> Startpunkt neu gesetzt
    at.run(timeout=180)
    _ok(at)
    assert at.slider(key="event_slider").value != 240


# ---------- Kernabschnitt ----------
def _core(at):
    return {m.label: m.value for m in at.metric if m.label == "Kipppunkt" or m.label.startswith("Vorsprung")}


def test_core_section_metrics_and_verdict_for_good_and_bad_estimates():
    at = _run()
    core = _core(at)
    assert core["Kipppunkt"] == "134 %" and core["Vorsprung (σ = 0 %)"] == "3.2×" and core["Vorsprung (σ = 25 %)"] == "1.7×"
    assert any("lohnt sich hier noch" in s.value for s in at.success)

    at = _run(_scenario(n_stacks_slider=6, max_height_slider=5, fill_slider=60, n_containers_slider=120, sigma_slider=200, seed_input=3))
    _ok(at)
    assert any("zu ungenau" in w.value for w in at.warning)


def test_core_section_reports_an_unclear_difference_when_it_lies_within_the_noise():
    # Gemessen (30 Instanzen, 6x5, Füllgrad 80 %, 120 Container): bei sigma 75-150 % liegt die Differenz Bestfit - Ausgleich im Rauschen
    at = _run(_scenario(n_stacks_slider=6, max_height_slider=5, fill_slider=80, n_containers_slider=120, sigma_slider=100, seed_input=3))
    _ok(at)
    assert any("Kein klarer Unterschied" in i.value for i in at.info)
    assert not any("lohnt sich" in s.value for s in at.success) and not any("zu ungenau" in w.value for w in at.warning)


# ---------- Methodenvergleich und Exakt-Tab ----------
def test_comparison_tab_lists_all_four_rules():
    at = _run()
    frames = [d.value for d in at.dataframe]
    table = next(f for f in frames if "Umstapelungen" in f.columns and len(f) == 4)
    assert list(table["Regel"]) == [C.RULE_LABELS[k] for k in C.RULE_KEYS]


def test_exact_tab_proves_the_optimum_on_the_small_preset():
    at = _run()
    _button(at, C.EXACT_PRESET).click()
    at.run(timeout=180)
    _button(at, "🧮 Optimum mit Hellsehen berechnen").click()
    at.run(timeout=180)
    _ok(at)
    assert any("Optimum mit Hellsehen: **3**" in i.value for i in at.info)
    assert not any("Für einen genauen Wert" in w.value for w in at.warning)
    exact_table = next(d.value for d in at.dataframe if "Abstand zum Optimum" in d.value.columns)
    assert all(str(v).startswith("+") for v in exact_table["Abstand zum Optimum"])


def test_exact_tab_shows_an_interval_and_the_shrink_button_when_the_limit_is_hit(monkeypatch):
    import stk_exact
    monkeypatch.setattr(C, "EXACT_TIME_LIMIT_SECONDS", 0.0)
    monkeypatch.setattr(stk_exact, "CHECK_EVERY", 1)                 # Zeit bei jedem Aufruf prüfen
    at = _run()
    _button(at, "🧮 Optimum mit Hellsehen berechnen").click()
    at.run(timeout=180)
    _ok(at)
    assert any("kein Beweis" in w.value and "zwischen" in w.value for w in at.warning)
    assert not any("Optimum mit Hellsehen: **" in i.value for i in at.info)         # nie ein unbewiesener Wert als Optimum
    _button(at, "Auf exakt lösbare Größe setzen").click()
    at.run(timeout=180)
    _ok(at)
    p = C.PRESETS[C.EXACT_PRESET]
    assert at.session_state["n_stacks_slider"] == p["n_stacks"] and at.session_state["n_containers_slider"] == p["n_containers"]


def test_exact_result_of_an_old_scenario_is_not_shown_after_changing_settings():
    at = _run()
    _button(at, C.EXACT_PRESET).click()
    at.run(timeout=180)
    _button(at, "🧮 Optimum mit Hellsehen berechnen").click()
    at.run(timeout=180)
    at.slider(key="sigma_slider").set_value(50)
    at.run(timeout=180)
    _ok(at)
    assert any("anderes Szenario" in i.value for i in at.info)


# ---------- Jedes Preset zeigt in der Oberfläche die Meldung, die zu seiner Geschichte passt ----------
STORY_MESSAGES = {
    # Preset: (Hauptansicht, Kernabschnitt-Urteil)
    "Perfekte Info": (("success", "spart hier"), ("success", "lohnt sich hier noch")),
    "Realistisch": (("success", "spart hier"), ("success", "lohnt sich hier noch")),
    "Kaum brauchbar": (("info", "Hier schlägt keine Regel die Alltagsregel"), ("warning", "zu ungenau")),
    "Voller Block": (("success", "spart hier"), ("success", "lohnt sich hier noch")),
    "Kleiner Block": (("success", "spart hier"), ("success", "lohnt sich hier noch")),
}


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_each_preset_shows_the_message_that_matches_its_story(name):
    at = _run()
    _button(at, name).click()
    at.run(timeout=180)
    _ok(at)
    (main_kind, main_text), (verdict_kind, verdict_text) = STORY_MESSAGES[name]
    elements = {"success": at.success, "info": at.info, "warning": at.warning}
    assert any(main_text in e.value for e in elements[main_kind]), f"{name}: Hauptansicht zeigt nicht '{main_text}'"
    assert any(verdict_text in e.value for e in elements[verdict_kind]), f"{name}: Urteil zeigt nicht '{verdict_text}'"


def test_barely_usable_preset_reports_that_the_everyday_rule_is_best():
    at = _run()
    _button(at, "Kaum brauchbar").click()
    at.run(timeout=180)
    labels = {m.label: m for m in at.metric}
    assert labels["Niedrigster Stapel"].value == "73" and "Alltagsregel" in labels and labels["Alltagsregel"].value == "73"
    core = _core(at)
    assert core["Kipppunkt"] == "56 %"


# ---------- PDF-Schaltfläche und Modellgrenzen ----------
def test_pdf_download_button_is_offered_in_the_main_view():
    at = _run()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Ergebnis als PDF herunterladen"


def test_model_limits_are_stated_openly_in_the_explanation():
    at = _run()
    text = " ".join(m.value for m in at.markdown)
    for needle in ["Grenzen dieses Modells", "Abholreihenfolge ist zufällig", "Schätzfehler ist gaußverteilt", "einen Block",
                   "hängen von Blockgröße, Füllgrad und Durchsatz ab", "keine Messung an Echtdaten", "Kein klarer Unterschied"]:
        assert needle in text, needle


def test_pdf_still_renders_when_the_everyday_rule_is_best():
    at = _run()
    _button(at, "Kaum brauchbar").click()
    at.run(timeout=180)
    _ok(at)
    assert len(at.get("download_button")) == 1
