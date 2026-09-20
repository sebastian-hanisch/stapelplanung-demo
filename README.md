# Stapelplanung im Containerblock – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-stapelplanung-demo.streamlit.app/)**

Interaktive Fall-Demo zur **Einlagerung im Stapelblock eines Containerterminals**: Ein Container kommt an
und muss in einen Stapel – aber **wann er abgeholt wird, weiß man nur ungefähr**. Liegt später ein früher
abfahrender Container darunter, muss er beim Abholen erst **umgestapelt** werden, ein unproduktiver
Kranhub. Die Demo vergleicht vier Einlagerungsregeln, von „irgendwohin" bis zu einer Regel, die der
**Abfahrtsschätzung** traut, und beantwortet die Frage: **Was ist Vorwissen über die Abfahrt wert, und ab
welcher Ungenauigkeit sollte man ihm besser nicht mehr trauen?**

Teil des Portfolios für die Website „Sebastian Hanisch – Operations Research und Machine Learning",
Welle 1 der Hafen-Linie (neben `berth-allocation-demo`, `quaycrane-demo`, `truck-appointment-demo` und
`yard-demo`): dort Kai, Kran, Gate und Hof, hier eine Ebene tiefer im Stapelblock des Yards.

## Warum dieses Problem

Umstapeln ist im Yard eine der Kernentscheidungen (Blocks Relocation Problem). Die übliche Frage lautet
„wie stapele ich optimal um?". Hier steht die Entscheidung *davor* im Mittelpunkt: **wohin beim
Einlagern**, wenn die Abfahrtszeit nur geschätzt ist. Das trennt zwei Aussagen sauber, die in der Praxis
gern vermischt werden: wie viel eine gute Schätzung bringt, und dass eine schlechte Schätzung schlechter sein
kann als gar keine.

## Modell

Ein **Block** besteht aus `S` Stapeln der Höhe `H`; erreichbar ist nur der oberste Container. Container
kommen an und werden abgeholt, in einer zufälligen Folge (jede Abholung trifft einen zufälligen anwesenden
Container). Die gleichzeitige Belegung ist auf `Füllgrad × (S − 1) × H` begrenzt: Ein Stapel bleibt als Platz
zum Umstapeln frei, denn bei Belegung bis `(S − 1)·H + 1` finden die Container über einem Ziel immer
Ausweichplätze (Beweisskizze in der App). Beim Abholen werden nur die Container **über dem Ziel** umgestapelt,
jeder Hub zählt als eine Umstapelung. Die Regel sieht beim Einlagern nur eine **Schätzung** der Abfahrt: die
wahre Abfahrt plus Gauß-Rauschen, dessen Größe der Regler „Schätzfehler" in Bruchteilen der mittleren
Standzeit vorgibt. Formal im Expander „📐 Mathematische Formulierung".

## Methodik – vier Regeln und ein Referenzlöser

- **Zufällig**: irgendein Stapel mit Platz – die Untergrenze ohne Information.
- **Niedrigster Stapel**: der Stapel mit den wenigsten Containern – die realistische Alltagsregel und die
  **Referenz für die Ersparnis**. Sie ignoriert die Schätzung.
- **Bestfit**: sucht einen Stapel, auf dem nichts Früheres blockiert wird, möglichst eng; sonst den mit der
  spätesten obersten Abfahrt. Sie vertraut der Schätzung.
- **Unsicherheits-bewusst**: wie Bestfit, nutzt aber die Größe des Schätzfehlers und wählt den Stapel mit der
  kleinsten Blockierwahrscheinlichkeit `P = Φ((ê − ê_oben) / (σ·D̄·√2))`.
- **Optimum mit Hellsehen** (Tab „Exakt"): exakte IDA\*-artige Suche über alle Einlagerungs- und
  Umstapelentscheidungen, mit wahren Abfahrten **und bekannter Ankunftsfolge**. Es ist eine **untere
  Schranke** für jede Online-Regel und nicht erreichbar.

Die Hauptansicht zeigt **dynamisch** die für die aktuelle Ereignisfolge beste Regel neben der Alltagsregel.
Die Ersparnis-Meldung erscheint nur, wenn es wirklich eine Ersparnis gibt.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stammen aus Simulationen mit diesem Code; die Abstimmung steht reproduzierbar in
`tools/PRESET_SWEEP.md`.

| Frage | Befund |
|---|---|
| **Wert exakter Kenntnis** | Block 6×5, Füllgrad 80 %, 120 Container, σ = 0: Bestfit braucht rund 3-mal weniger Umstapelungen als zufälliges Einlagern (Mittel über 200 Seeds: 23 gegen 77). In der früheren Messreihe mit 200 Containern waren es bei Füllgrad 60 % sogar etwa 6×. |
| **Kipppunkt** | Ab einem Schätzfehler zwischen etwa 55 % und 140 % der mittleren Standzeit braucht Bestfit **mehr** Umstapelungen als der einfache Ausgleich. Wo genau, **hängt von Blockgröße und Durchsatz ab**: bei 120 Containern und Füllgrad 60 % bei 56 %, bei Füllgrad 80 % bei 134 %; in einer früheren Messreihe mit 200 Containern bei 75 % bzw. 139 %. Um den Kipppunkt herum ist der Unterschied nicht vom Rauschen zu trennen. |
| **Unsicherheits-bewusste Regel** | Gewinnt bei großem σ, verliert bei kleinem σ gegen Bestfit. Keine Regel gewinnt überall. |
| **Abstand zum Optimum** | Bei exakter Abfahrtskenntnis braucht Bestfit etwa das Doppelte (kleine Blöcke) bis Dreifache (4×4 mit 30 Containern) des Optimums. Aber: Das Optimum kennt auch die künftigen Ankünfte. Die Lücke ist großenteils der **Preis des Nicht-Wissens**, kein Verbesserungsspielraum für eine Online-Regel. |
| **Reichweite des Exakt-Lösers** (10 s, 8 Instanzen) | 4×4/18, 4×4/30, 5×4/30: 8 von 8 in unter 1,1 s; 6×5/40: 7 von 8; 6×5/60: 6 von 8; 6×5/120: 6 von 8 (Füllgrad 60 %) bzw. **2 von 8** (Füllgrad 80 %). |

## Ehrliche Grenzen

- **Abholreihenfolge zufällig.** In echten Blöcken werden Container meist nach Schiff oder Zielgruppe
  gebündelt und getrennt gelagert; das senkt die Umstapelungen stark und ist hier **nicht** abgebildet.
- **Gauß-Rauschen ohne Schiefe**; reale Standzeiten sind schief verteilt. Ein Schätzfehler von 25–50 % ist
  ein Wert zum Einordnen, nicht ein gemessener.
- **Ein Block**, keine Fahrzeiten und Kranwege, keine Gefahrgut-, Reefer- oder Gewichtsklassen.
- **Exakt nicht überall.** Auf dem Standardblock (6×5, 120 Container) liefert der Exakt-Tab meist ein
  breites Intervall statt eines Werts. Er zeigt dann die bewiesene untere und die obere Schranke und **nie**
  einen unbewiesenen Wert als „Optimum", plus einen Knopf, der einen exakt lösbaren Block lädt.
- Alle Zahlen sind **Größenordnungen aus einer Simulation, keine Messung an Echtdaten.**

## Design-Entscheidungen und Funde

**Für alle Regeln dieselbe Umstapel-Regel.** Beim Abholen entscheidet Bestfit, wohin ein Blocker kommt, egal
welche Regel eingelagert hat. So misst der Vergleich nur die Einlagerungsentscheidung. Nachgemessen: Mit
einheitlichem Umstapeln bleibt das Muster gleich, die unsicherheits-bewusste Regel ist sogar gleich gut oder
besser als mit eigener Umstapel-Logik.

**Das Urteil im Kernabschnitt kennt drei Zustände.** „Lohnt sich", „kippt" und „kein klarer Unterschied": Ein
Unterschied gilt nur als klar, wenn die **gepaarte Differenz** über dieselben Ereignisfolgen mehr als zwei
Standardfehler beträgt. Lieber kein Urteil als eines, das im Rauschen liegt.

**Der Exakt-Löser: Machbarkeitssuche mit Kindersortierung statt exaktem Minimalwert.** Die erste Fassung
(memoisierte Suche ohne Schranke) war bei 4×4 mit 18 Containern für 30 Instanzen nach über 5 Minuten nicht fertig. Die
Endfassung ist IDA\* mit der zulässigen unteren Schranke „Container über einem früher abfahrenden" (jeder muss
mindestens einmal umgestapelt werden), iterativer Vertiefung über das Budget, Kindern in Bestfit-Reihenfolge
(Abbruch beim ersten Fund) und je Stapel gemerkter Schranke: **2,5- bis 11-mal schneller** bei identischem
Ergebnis auf 200 Instanzen. Ein absteigender Machbarkeitslauf zur Verkleinerung der oberen Schranke brachte am
Standardblock nur 2–3 Umstapelungen bei rund 1,5 s je Schritt und wurde nicht übernommen.

**Presets: typisch statt schön, und rauschstabil.** Seeds sind nicht nach dem schönsten Einzelfall gewählt,
sondern nahe am Median mehrerer Merkmale über 200 Seeds, und die Aussage muss bei mindestens 90 % anderer
Rausch-Ziehungen halten. Der zuerst gewählte Seed 3 war typisch, aber **nicht rauschstabil**: Bei „Realistisch"
gewann Bestfit nur in 75 % der Rausch-Ziehungen, ein Glückstreffer. Außerdem hielten zwei Plankriterien aus
einer Messung mit 200 Containern bei 120 Containern nicht („Unsicherheits-bewusst ≤ beide" gilt nur in 62 % der
Seeds; „Bestfit ≥ 0,4 pro Container" nur in 46 %) und wurden an der Grundgesamtheit korrigiert.

**Fund: ein Preset außerhalb der Reglergrenzen.** Das Preset „Kleiner Block" setzte zuerst 30 Container bei
einer Reglerunterkante von 40. Streamlit warf eine Ausnahme; der End-to-End-Test fing sie sofort. Seitdem
prüft ein Test alle Presets gegen die Grenzen und die Schrittweite.

## Tests

`pytest tests/ -v` – 324 Tests, rund 33 s. Zusammensetzung:

- **Kern:** Ereignisfolge und Schätzung (feste Werte, Invarianten je Ereignis, unabhängiges Kontrollmodell), Regeln
  (Randfälle, Tie-Breaks), Simulation (Handfälle, 20 feste Referenzwerte aus der Messreihe).
- **Exakt-Löser:** Handfälle, **unabhängige Vollaufzählung** als Gegenprobe auf 160 kleinen Instanzen, feste
  Optima aus dem Messreihen-Code, „Optimum ≤ jede Regel", das Intervall wird mit mehr Rechenzeit nie schlechter,
  kein Rekursionsfehler bei 600 Ereignissen, Aufrufzahl als Regressionsschutz.
- **Auswertung, Figuren, Panel:** σ-Kurve reproduziert die Messwerte, Geometrieprüfung der Blockansicht (keine
  Überlappungen, Beschriftung im Container), Kennzahlen-Farben am Streamlit-Proto.
- **Presets:** je Preset ein Test am gewählten Seed, an 20 Rausch-Ziehungen und im Mittel über 60 Seeds.
- **PDF:** Inhalt zeilenweise, genaue Sonderzeichen (fpdf2 stürzt bei „–" und „€" ab).
- **End-to-End (AppTest):** Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, Exakt-Tab
  (bewiesen, Intervall, veraltetes Ergebnis).

Zusätzlich wurde jedes Modul mit **eingebauten Fehlern** geprüft (über 60 Stück: Vorzeichen, Schwellen,
Formeln, Seeds): Was die Tests nicht fanden, bekam einen eigenen Test.

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Hauptablauf: Presets, Sidebar, Hauptansicht, Blick in den Block, Kernabschnitt, Methodenvergleich, Texte |
| `stk_constants.py` | Regler-Grenzen, `PRESETS`, Farben, Regelbeschreibungen |
| `stk_presets.py` | `SETTING_SPECS`, Permalink (Begrenzen und Einrasten), Presets, Zufalls-Seed-Button |
| `stk_scenario.py` | Ereignisfolge, verrauschte Abfahrtsschätzung (eigener Zufallsstrom) |
| `stk_rules.py` | die vier Einlagerungsregeln und die gemeinsame Umstapel-Regel |
| `stk_simulation.py` | Ablauf im Block, optional mit Momentaufnahme je Ereignis |
| `stk_exact.py` | Optimum mit Hellsehen (IDA\*-artige Suche, Zeitlimit, Intervall) |
| `stk_evaluation.py` | Regelvergleich, beste Regel, σ-Kurve, Kipppunkt, Urteil, Abstand zum Optimum |
| `stk_visualization.py` | Blockansicht, σ-Kurve, kumulierte Kurve, Regelbalken (alle Achsen fest) |
| `stk_ui_panel.py` | Panel je Regel im Methodenvergleich |
| `stk_pdf_export.py` | PDF-Ergebnis (`fpdf2`, Kernschrift, Sonderzeichen-Bereinigung) |
| `tools/tune_presets.py`, `tools/PRESET_SWEEP.md` | Preset-Abstimmung und ihr Bericht |
| `tests/` | siehe oben |

## Bewusst nicht umgesetzt (mögliche Erweiterungen)

- **Bündelung nach Schiff oder Zielgruppe** (Segregation): die realistischere Abholstruktur. Zuerst müsste
  gemessen werden, wie stark sie das Bild verändert.
- **Schief verteilte Standzeiten**, echte Daten statt Gauß-Rauschen.
- **Reefer-Stellplätze, Gefahrgut und Gewichtsklassen** als Nebenbedingungen (gehören eher zu Stau- und
  Reefer-Demos).
- **Vorsortieren** (Pre-Marshalling) in ruhigen Zeiten und **mehrere Blöcke** mit Kranfahrzeiten.
- **Stärkere untere Schranke** im Exakt-Löser, um auch den Standardblock zu beweisen.

## Lokal ausführen

```bash
pip install -r requirements-dev.txt
streamlit run app.py
```

Tests: `pytest tests/ -v`. Preset-Abstimmung: `python tools/tune_presets.py population|candidates|robust|small`.

---

Teil des [Operations-Research-Demo-Portfolios](https://sebastianhanisch.net/demos.html) von
[Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning.
Interesse an einer maßgeschneiderten Lösung? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html).
