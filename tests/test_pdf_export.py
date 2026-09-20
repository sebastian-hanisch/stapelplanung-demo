import re

import pytest

import stk_constants as C
from stk_evaluation import compare_rules
from stk_pdf_export import generate_stacking_pdf, pdf_text
from stk_scenario import generate_instance


def _pdf(preset=None, compress=False, **override):
    p = dict(C.PRESETS[preset or "Realistisch"])
    p.update(override)
    inst = generate_instance(p["n_stacks"], p["max_height"], p["fill_pct"] / 100, p["n_containers"], p["seed"])
    return generate_stacking_pdf(inst, compare_rules(inst, p["sigma_pct"] / 100), p["sigma_pct"], compress=compress), inst


def _texts(data):
    """Alle Textstuecke des (unkomprimierten) PDFs als Liste, Latin-1 gelesen, PDF-Escapes aufgeloest."""
    raw = re.findall(rb"\((.*?)\)\s*Tj", data)
    return [t.decode("latin-1").replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\") for t in raw]


# ---------- Sonderzeichen: mit den GENAUEN Zeichen testen (fpdf2 stürzt bei "–" und "€" ab) ----------
EXPECTED = {"–": "-", "—": "-", "€": "EUR", "σ": "Sigma", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "„": '"', "“": '"', "’": "'", "·": "-"}


@pytest.mark.parametrize("char,replacement", list(EXPECTED.items()))
def test_pdf_text_replaces_every_known_troublemaker_with_a_readable_equivalent(char, replacement):
    out = pdf_text(f"a{char}b")
    out.encode("latin-1")                                          # darf nicht werfen
    assert out == f"a{replacement}b"                               # nicht bloss "irgendwie ersetzt", sondern lesbar (kein "?")


def test_pdf_text_keeps_umlauts_and_times_sign():
    assert pdf_text("Füllgrad äöüß ÄÖÜ × 3") == "Füllgrad äöüß ÄÖÜ × 3"


def test_pdf_text_replaces_unknown_characters_instead_of_crashing():
    assert pdf_text("日本語").encode("latin-1") == b"???"


# ---------- Inhalt ----------
def test_pdf_is_a_valid_document_with_the_scenario_and_results():
    data, inst = _pdf()
    assert data.startswith(b"%PDF") and data.rstrip().endswith(b"%%EOF") and len(data) > 2000
    for needle in [b"Stapelplanung im Containerblock", b"Szenario", b"Zusammenfassung", b"Regelvergleich", b"Hinweise zum Modell",
                   b"Bestfit", b"Niedrigster Stapel", b"Zuf\xe4llig", b"Unsicherheits-bewusst",      # Umlaut steht als Latin-1-Byte im Text
                   b"25 % der mittleren Standzeit", b"Zufalls-Seed"]:
        assert needle in data, needle


def test_pdf_shows_the_numbers_of_the_default_scenario():
    texts = _texts(_pdf()[0])
    # Seed 7, Realistisch: Bestfit 65, Alltagsregel 94, Ersparnis 29 (31 %)
    assert "29 Umstapelungen (31 %)" in texts and "Alltagsregel (Niedrigster Stapel)" in texts
    assert texts[texts.index("Beste Regel") + 1] == "Bestfit"
    assert texts[texts.index("Umstapelungen der besten Regel") + 1] == "65"
    assert texts[texts.index("Alltagsregel (Niedrigster Stapel)") + 1] == "94"
    assert "80 %  (höchstens 20 Container gleichzeitig)" in texts


def test_pdf_scenario_rows_show_every_setting():
    texts = _texts(_pdf()[0])
    value = lambda label: texts[texts.index(label) + 1]
    assert value("Anzahl Stapel") == "6" and value("Maximale Stapelhöhe") == "5" and value("Anzahl Container") == "120"
    assert value("Zufalls-Seed") == "7" and value("Schätzfehler der Abfahrt") == "25 % der mittleren Standzeit"
    small = _texts(_pdf("Kleiner Block")[0])
    v2 = lambda label: small[small.index(label) + 1]
    assert v2("Anzahl Stapel") == "4" and v2("Anzahl Container") == "30" and v2("Zufalls-Seed") == "30"
    assert v2("Schätzfehler der Abfahrt") == "0 % der mittleren Standzeit"


def test_pdf_states_plainly_when_the_everyday_rule_is_best():
    texts = _texts(_pdf("Kaum brauchbar")[0])
    assert texts[texts.index("Ersparnis") + 1] == "keine (die Alltagsregel ist hier die beste)"
    assert not any("Umstapelungen (" in t and "%" in t for t in texts)          # keine Scheinersparnis


def test_pdf_table_has_a_row_per_rule_with_the_measured_numbers_and_signed_deltas():
    texts = _texts(_pdf()[0])
    header = texts.index("Differenz")
    rows = [texts[header + 1 + 6 * i: header + 7 + 6 * i] for i in range(4)]
    assert [r[0] for r in rows] == [C.RULE_LABELS[k] for k in C.RULE_KEYS]
    assert [r[1] for r in rows] == ["121", "94", "65", "81"]                   # feste Werte (Seed 7)
    assert [r[5] for r in rows] == ["+27", "0", "-29", "-13"]                  # meine Regel minus Alltagsregel (94)
    assert [r[2] for r in rows] == ["1.01", "0.78", "0.54", "0.68"]


def test_pdf_contains_no_dash_or_euro_that_would_have_crashed_the_font():
    data, _ = _pdf()
    assert "–".encode("utf-8") not in data and "€".encode("utf-8") not in data and "σ".encode("utf-8") not in data


# ---------- Robustheit ----------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_produces_a_pdf(name):
    data, _ = _pdf(name, compress=True)
    assert data.startswith(b"%PDF") and len(data) > 1500


@pytest.mark.parametrize("override", [dict(n_stacks=3, max_height=3, fill_pct=40, n_containers=20),
                                      dict(n_stacks=8, max_height=6, fill_pct=100, n_containers=300, sigma_pct=200),
                                      dict(sigma_pct=0), dict(seed=0), dict(seed=9999)])
def test_extreme_scenarios_produce_a_pdf(override):
    data, _ = _pdf(**override)
    assert data.startswith(b"%PDF")


def test_compression_only_changes_the_size():
    plain, _ = _pdf(compress=False)
    packed, _ = _pdf(compress=True)
    assert len(packed) < len(plain)
