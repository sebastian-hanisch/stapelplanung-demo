# Preset-Abstimmung (AP 6)

Reproduzierbar mit `./venv/Scripts/python.exe tools/tune_presets.py <modus>` (Modi: population, candidates, robust, small).

**Grundsätze:** Seeds nicht nach dem schönsten Einzelfall wählen, sondern typisch (nahe am Median der Merkmale über 200 Seeds); Ereignis-Seed UND Rausch-Strom prüfen (20 Rausch-Ziehungen, Aussage muss in ≥ 90 % halten); Kriterien an der Grundgesamtheit messen, nicht an einer früheren Messung mit anderer Größe (die Planwerte stammten von N=200).

## 1. Grundgesamtheit je Preset (200 Seeds, N=120)
```

### Perfekte Info  {'n_stacks': 6, 'max_height': 5, 'fill_pct': 80, 'n_containers': 120, 'sigma_pct': 0, 'seed': 7}
Mittel Umstapelungen: {'Zufällig': 76.8, 'Niedrigster Stapel': 64.3, 'Bestfit': 23.3, 'Unsicherheits-bewusst': 29.3}
Anteil Seeds: bestfit < lowest 100% | lowest < bestfit 0% | aware <= beide 20% | zufaellig >= 2.5x bestfit 81% | bestfit pro Container >= 0.4 5%
Verhaeltnis zufaellig/bestfit: Median 3.5, 10%-Quantil 2.3, 90%-Quantil 8.8

### Realistisch  {'n_stacks': 6, 'max_height': 5, 'fill_pct': 80, 'n_containers': 120, 'sigma_pct': 25, 'seed': 7}
Mittel Umstapelungen: {'Zufällig': 89.5, 'Niedrigster Stapel': 73.3, 'Bestfit': 51.5, 'Unsicherheits-bewusst': 56.2}
Anteil Seeds: bestfit < lowest 94% | lowest < bestfit 4% | aware <= beide 42% | zufaellig >= 2.5x bestfit 6% | bestfit pro Container >= 0.4 62%
Verhaeltnis zufaellig/bestfit: Median 1.8, 10%-Quantil 1.4, 90%-Quantil 2.3

### Kaum brauchbar  {'n_stacks': 6, 'max_height': 5, 'fill_pct': 60, 'n_containers': 120, 'sigma_pct': 150, 'seed': 7}
Mittel Umstapelungen: {'Zufällig': 86.6, 'Niedrigster Stapel': 60.7, 'Bestfit': 75.0, 'Unsicherheits-bewusst': 58.1}
Anteil Seeds: bestfit < lowest 8% | lowest < bestfit 90% | aware <= beide 62% | zufaellig >= 2.5x bestfit 0% | bestfit pro Container >= 0.4 96%
Verhaeltnis zufaellig/bestfit: Median 1.2, 10%-Quantil 0.9, 90%-Quantil 1.4

### Voller Block  {'n_stacks': 6, 'max_height': 5, 'fill_pct': 100, 'n_containers': 120, 'sigma_pct': 0, 'seed': 7}
Mittel Umstapelungen: {'Zufällig': 93.1, 'Niedrigster Stapel': 81.4, 'Bestfit': 43.0, 'Unsicherheits-bewusst': 48.8}
Anteil Seeds: bestfit < lowest 100% | lowest < bestfit 0% | aware <= beide 26% | zufaellig >= 2.5x bestfit 42% | bestfit pro Container >= 0.4 46%
Verhaeltnis zufaellig/bestfit: Median 2.3, 10%-Quantil 1.5, 90%-Quantil 8.3

### Kleiner Block  {'n_stacks': 4, 'max_height': 4, 'fill_pct': 100, 'n_containers': 30, 'sigma_pct': 0, 'seed': 30}
Mittel Umstapelungen: {'Zufällig': 12.6, 'Niedrigster Stapel': 9.9, 'Bestfit': 3.5, 'Unsicherheits-bewusst': 4.4}
Anteil Seeds: bestfit < lowest 94% | lowest < bestfit 2% | aware <= beide 60% | zufaellig >= 2.5x bestfit 46% | bestfit pro Container >= 0.4 5%
Verhaeltnis zufaellig/bestfit: Median 3.2, 10%-Quantil 1.6, 90%-Quantil 10.0
```

## 2. Typische Seeds über alle σ-Presets (mit allen Nebenbedingungen, inkl. der später verworfenen aware-Bedingung)
```
Median der Merkmale: {'r1': 3.53, 's1': 66.67, 's2': 29.03, 'g3': 24.82, 'r4': 1.65, 'pc4': 0.34}
43 von 200 Seeds erfuellen alle Nebenbedingungen; die typischsten:
  seed 101 dist 0.82 | r1 3.6 s1 68% s2 33% g3 +32% r4 1.90 pc4 0.32 | Rauschen: P2 100% P3 75% P3aware<=low 95%
  seed   3 dist 0.82 | r1 4.2 s1 66% s2 27% g3 +26% r4 1.88 pc4 0.27 | Rauschen: P2 75% P3 100% P3aware<=low 40%
  seed  44 dist 1.56 | r1 3.5 s1 65% s2 26% g3 +39% r4 2.30 pc4 0.44 | Rauschen: P2 95% P3 85% P3aware<=low 75%
  seed 183 dist 1.74 | r1 3.0 s1 52% s2 31% g3 +21% r4 1.90 pc4 0.46 | Rauschen: P2 100% P3 85% P3aware<=low 40%
  seed  96 dist 1.82 | r1 4.1 s1 70% s2 39% g3 +3% r4 1.68 pc4 0.27 | Rauschen: P2 100% P3 75% P3aware<=low 90%
  seed   9 dist 1.93 | r1 2.9 s1 68% s2 14% g3 +36% r4 2.05 pc4 0.34 | Rauschen: P2 85% P3 95% P3aware<=low 75%
  seed  54 dist 1.96 | r1 3.1 s1 64% s2 35% g3 +45% r4 2.12 pc4 0.42 | Rauschen: P2 100% P3 100% P3aware<=low 65%
  seed 139 dist 2.04 | r1 2.7 s1 62% s2 25% g3 +16% r4 1.97 pc4 0.62 | Rauschen: P2 100% P3 85% P3aware<=low 70%
```

## 3. Typische UND rauschstabile Seeds (harte Bedingung ≥ 90 % in Preset 2 und 3)
```
43 Seeds mit Rauschstabilitaet >= 90 % in Preset 2 und 3; die typischsten:
  seed   7 dist 0.87 | r1 4.0 s1 70% s2 31% g3 +34% r4 1.58 pc4 0.34 | P2 100% P3 95% aware<=low 55%
  seed  86 dist 0.99 | r1 4.1 s1 67% s2 25% g3 +31% r4 1.78 pc4 0.27 | P2 100% P3 90% aware<=low 55%
  seed 195 dist 1.04 | r1 3.6 s1 64% s2 23% g3 +20% r4 2.11 pc4 0.33 | P2 95% P3 95% aware<=low 65%
  seed 189 dist 1.55 | r1 3.5 s1 71% s2 21% g3 +47% r4 1.62 pc4 0.28 | P2 100% P3 95% aware<=low 50%
  seed  52 dist 1.56 | r1 4.5 s1 67% s2 28% g3 +21% r4 2.38 pc4 0.47 | P2 100% P3 100% aware<=low 10%
  seed 171 dist 1.91 | r1 2.6 s1 55% s2 30% g3 +21% r4 1.67 pc4 0.64 | P2 95% P3 90% aware<=low 45%
  seed  54 dist 1.96 | r1 3.1 s1 64% s2 35% g3 +45% r4 2.12 pc4 0.42 | P2 100% P3 100% aware<=low 65%
  seed 150 dist 2.06 | r1 3.3 s1 59% s2 15% g3 +7% r4 1.50 pc4 0.30 | P2 100% P3 100% aware<=low 80%
  seed 188 dist 2.11 | r1 3.8 s1 69% s2 18% g3 +31% r4 2.72 pc4 0.41 | P2 100% P3 100% aware<=low 80%
  seed 106 dist 2.13 | r1 5.4 s1 75% s2 28% g3 +12% r4 2.11 pc4 0.32 | P2 100% P3 100% aware<=low 45%
```

## 4. Kleiner Block: Bestfit gegen exaktes Optimum (100 Seeds)
```
100 von 100 Seeds in 8 s exakt geloest; mittlere Zeit 0.11 s, max 3.2 s
Mittel: Optimum 1.21, Bestfit 3.56, Ausgleich 9.88; Verhaeltnis der Mittel Bestfit/Optimum 2.94
typischste Seeds (Optimum >= 2, Bestfit > Optimum, Ausgleich > Bestfit, < 3 s):
  seed  20  Optimum 2  Bestfit 6  Ausgleich 12  Verhaeltnis 3.0  0.01 s
  seed  30  Optimum 3  Bestfit 9  Ausgleich 16  Verhaeltnis 3.0  0.04 s
  seed  64  Optimum 3  Bestfit 9  Ausgleich 21  Verhaeltnis 3.0  0.15 s
  seed  55  Optimum 2  Bestfit 5  Ausgleich 15  Verhaeltnis 2.5  0.01 s
  seed  61  Optimum 2  Bestfit 5  Ausgleich 17  Verhaeltnis 2.5  0.03 s
  seed  90  Optimum 2  Bestfit 5  Ausgleich 11  Verhaeltnis 2.5  0.01 s
  seed  81  Optimum 4  Bestfit 12  Ausgleich 15  Verhaeltnis 3.0  1.53 s
  seed  40  Optimum 3  Bestfit 8  Ausgleich 15  Verhaeltnis 2.7  0.03 s
```

## Ergebnis und Entscheidungen

- **Seed 7** für die vier σ-Presets (bis dahin 3): typisch (Abstand 0,87 zum Median, der niedrigste unter den rauschstabilen Kandidaten) und stabil (Preset 2: 100 %, Preset 3: 95 % der Rausch-Ziehungen). Der frühere Seed 3 war typisch, aber nicht rauschstabil: Bei Preset „Realistisch“ gewann Bestfit nur in 75 % der Rausch-Ziehungen.
- **Standard-Seed = 7**, damit die Startseite dem Preset „Realistisch“ entspricht.
- **Seed 30** für „Kleiner Block“ (bis dahin 4): Optimum 3, Bestfit 9, Ausgleich 16, Verhältnis 3,0 (Mittel über 100 Seeds: 2,94), in 0,04 s exakt gelöst. Seed 4 hatte nur das Verhältnis 1,75.
- **Korrigierte Kriterien** (Plan, Abschnitt 7): (a) „Unsicherheits-bewusst ≤ beide“ bei „Kaum brauchbar“ gilt nur in 62 % der Seeds und wurde gestrichen (im Mittel ist die Regel dort trotzdem am besten: 58,1 gegen 60,7 und 75,0); (b) „Voller Block: Bestfit ≥ 0,4 pro Container“ war ein Wert von N=200 – bei N=120 sind es im Mittel 0,36 (46 % der Seeds ≥ 0,4). Neues Kriterium: ≥ 1,5× die Umstapelungen des 80-%-Blocks (gemessen 1,85×) und ≥ 0,25 pro Container.
- **Kipppunkt hängt vom Durchsatz ab:** bei N=120 und Füllgrad 60 % liegt er bei 56 % (in der Planmessung mit N=200: 75 %). Die App rechnet ihn live.
- Was jedes Preset in der Oberfläche zeigt (Seed 7 bzw. 30): Perfekte Info: Bestfit spart 70 %; Realistisch: 31 %; Kaum brauchbar: der Ausgleich ist die beste Regel, Urteil „kippt“, Kipppunkt 56 %; Voller Block: 59 % (beste Regel: Unsicherheits-bewusst, 40 gegen 41); Kleiner Block: 50 %, Optimum 3.
