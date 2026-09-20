"""PDF-Export des Ergebnisses (fpdf2, Helvetica-Kernschrift, nur Text und Tabellen).

Die Kernschriften kennen nur Latin-1: Umlaute und "×" sind erlaubt, aber "–" (Gedankenstrich), "€", "σ", "≥" usw.
lassen fpdf2 abstürzen. Deshalb läuft jeder Text durch pdf_text().
"""

import time

import stk_constants as C
from stk_evaluation import best_rule, comparison_rows, outcome_of, savings

_REPLACEMENTS = {
    "–": "-", "—": "-", "‑": "-", "σ": "Sigma", "≥": ">=", "≤": "<=", "→": "->", "≈": "ca.", "€": "EUR",
    "·": "-", "“": '"', "”": '"', "„": '"', "’": "'", "‘": "'",
}


def pdf_text(text):
    """Text für die Helvetica-Kernschrift: bekannte Sonderzeichen ersetzen, den Rest Latin-1-sicher machen."""
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_stacking_pdf(instance, outcomes, sigma_pct, compress=True):
    """Ergebnis der aktuellen Einstellung als PDF: Szenario, Zusammenfassung, Regelvergleich, Hinweise."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    baseline = outcome_of(outcomes, C.BASELINE_RULE)
    best = best_rule(outcomes)
    saved = savings(outcomes)

    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()

    def line(text, height=7, width=0):
        pdf.cell(width, height, pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "B", 16)
    line("Stapelplanung im Containerblock", 10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(120, 120, 120)
    line(f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')}  -  sebastianhanisch.net", 6)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    line("Szenario", 8)
    pdf.set_font("Helvetica", "", 10)
    for label, value in [
        ("Anzahl Stapel", str(instance.n_stacks)),
        ("Maximale Stapelhöhe", str(instance.max_height)),
        ("Füllgrad", f"{instance.fill * 100:.0f} %  (höchstens {instance.capacity} Container gleichzeitig)"),
        ("Anzahl Container", str(instance.n_containers)),
        ("Schätzfehler der Abfahrt", f"{sigma_pct} % der mittleren Standzeit"),
        ("Zufalls-Seed", str(instance.seed)),
    ]:
        pdf.cell(70, 6, pdf_text(label), border=0)
        line(value, 6)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    line("Zusammenfassung", 8)
    pdf.set_font("Helvetica", "", 10)
    for label, value in [
        ("Beste Regel", best.label),
        ("Umstapelungen der besten Regel", str(best.moves)),
        (f"Alltagsregel ({baseline.label})", str(baseline.moves)),
        ("Ersparnis", f"{saved.saved} Umstapelungen ({saved.saved_pct:.0f} %)" if saved.saved > 0 else "keine (die Alltagsregel ist hier die beste)"),
    ]:
        pdf.cell(70, 6, pdf_text(label), border=0)
        line(value, 6)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    line("Regelvergleich", 8)
    headers = ["Regel", "Umstapelungen", "pro Container", "Mit Umstapelung", "Höchster Stapel", "Differenz"]
    widths = [46, 30, 28, 32, 30, 24]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    for header, width in zip(headers, widths):
        pdf.cell(width, 7, pdf_text(header), border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for row in comparison_rows(outcomes):
        cells = [row.label, str(row.moves), f"{row.moves_per_container:.2f}", f"{row.share_with_move * 100:.0f} %",
                 str(row.max_stack_height), "0" if row.delta_moves == 0 else f"{row.delta_moves:+d}"]
        for value, width in zip(cells, widths):
            pdf.cell(width, 7, pdf_text(value), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(110, 110, 110)
    line("Differenz = Umstapelungen dieser Regel minus Alltagsregel (negativ = besser).", 5)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    line("Hinweise zum Modell", 8)
    pdf.set_font("Helvetica", "", 9)
    for note in [
        "Jede Umstapelung ist ein unproduktiver Kranhub. Beim Abholen werden nur die Container über dem Ziel umgestapelt.",
        "Beim Umstapeln entscheidet für alle Regeln dieselbe Regel (Bestfit); verglichen wird nur die Einlagerungsentscheidung.",
        "Die Abholreihenfolge ist zufällig, der Schätzfehler gaußverteilt: Größenordnungen aus einer Simulation, keine Messung an Echtdaten.",
        "Ein Block, keine Fahrzeiten, keine Gefahrgut-, Reefer- oder Gewichtsklassen.",
    ]:
        pdf.multi_cell(0, 5, pdf_text("- " + note), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
