> **UWAGA (2026-07-23): protokół opisany poniżej nie daje wyniku.**
> Przebieg wykonano — `results_x1/` — i jest zdegenerowany. Znaleziono
> cztery wady, każda samodzielnie unieważniająca κ jako miarę eksportu:
> podłoga nagłówka gzip rosnąca z n (κ_floor: 0.704 przy 96³ → 0.980 przy
> 288³), artefakt nasycenia, niewykonalne wyrównanie objętości zasiewu
> `shell`, oraz zasiew `distributed` wprost w region pomiarowy.
> **Szczegóły i dane: [FINDINGS.md](FINDINGS.md).**
>
> Sekcja „Jak czytać wynik" poniżej jest w szczególności niebezpieczna:
> kryterium „odstępy > 2σ" przechodzi automatycznie dla ramion martwych,
> bo mają σ = 0. Zastępcze kryteria: [CRITERIA_v2.md](CRITERIA_v2.md)
> (projekt, czeka na zamrożenie).
>
> Nowy tor: `scope_topology_v2.py` (zasiew `scope_seed.py`, obserwable
> kosztowe `scope_thermo.py`, analiza `scope_analyze.py`).
> `scope_topology.py` pozostaje nietknięty jako referencja audytowa —
> `scope_run.py` zweryfikowano jako bitowo z nim identyczny.
>
> Poniższa treść zachowana jako zapis historyczny.

---

# SCOPE topology experiment — instrukcja (vast.ai / dowolne GPU)

## Setup (raz)
```bash
pip install torch numpy matplotlib
```

## Przebieg główny (3 topologie × 8 przebiegów, siatka 96³)
```bash
python scope_topology.py --grid 96 --steps 20000 --n-runs 8 --outdir results_x1
```

## Kontrola rozmiaru domeny (KLUCZOWA — rozstrzyga homogenizację vs eksport)
```bash
python scope_topology.py --grid 192 --steps 20000 --n-runs 8 --scale 2 --outdir results_x2
```

## Co odsyłasz
`results_x1/` i `results_x2/`: `runs.json`, `summary.json`, `kappa_topologies.png`

## Jak czytać wynik
- **Teza topologiczna potwierdzona**, jeśli: uporządkowanie κ(T) i/lub τ
  (first passage przez parytet) jest spójne między przebiegami w ensemble
  (odstępy > 2σ) ORAZ przeżywa zmianę siatki 96→192.
- **Homogenizacja (wynik negatywny)**, jeśli: κ(t) przy 96³ i 192³ nakłada
  się w czasie wzorca niezależnie od topologii — wtedy κ→1 to equilibracja,
  nie eksport.
- τ ma rozdzielczość `--record-every * dt`; przy głównym przebiegu = 36 j.cz.

## Definicja K (jawna, do metod w papierze)
K(region) = bajty po gzip(kwantyzacja 8-bit pola v w regionie) / liczba
wokseli. κ(t) = K_border/K_inner, border = powłoka 0.85R–R, inner = kula 0.5R.
Uwaga: na małych siatkach (<48³) narzut nagłówka gzip zawyża K jednorodnych
regionów — nie porównuj wartości bezwzględnych między rozmiarami siatki,
porównuj kształty krzywych i uporządkowania.

## Czas na GPU (rząd wielkości)
96³ × 20k kroków ≈ kilka minut/przebieg na RTX 3090/4090; 192³ ≈ ~8× dłużej.
Całość (2 rozmiary × 3 topologie × 8 przebiegów) zmieści się w 1–2 h.
