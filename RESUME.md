# RESUME — stan pracy na 2026-07-23, przerwane na stop instancji

Instancja vast.ai 45611992 (4× RTX 4090) zatrzymana przez ŁC. Wszystkie
zadania GPU zatrzymane czysto, żadne obliczenie nie było w trakcie zapisu.

## Jedyna rzecz blokująca

**Ratyfikacja wariantu B′ trójkąta rozplątującego.** Nic więcej nie stoi
na przeszkodzie uruchomieniu konfirmacji.

Ramię B z §6.3 CRITERIA_v2 (192³, powłoka 2-wokselowa) **padło warunek
wstępny** — powłoka wygasa natychmiast (`viab192_th2/`, fill=0 od t=90,
κ_gzip(T)=0.9390 = podłoga dla n=192). Powód ogólny: przeżywalność
dyfuzyjna zależy od grubości bezwzględnej w wokselach, nie od frakcji
objętości, więc samopodobieństwo jest realizowalne wyłącznie w górę.

Wariant zastępczy, zweryfikowany geometrycznie, czeka na decyzję:

| | siatka | grubość | frakcja | central max_r | B5 |
|---|---|---|---|---|---|
| **A** podstawowy | 192³ | 3.0 | 5.71% | 0.385R | OK |
| **B′** rozplątujące | 288³ | 4.5 | 5.73% | 0.386R | OK |
| **C** kontrolny | 288³ | 3.0 | 3.81% | 0.337R | OK |

bok A→B′ = czysty efekt n przy stałej frakcji; bok B′→C = czysty efekt
frakcji przy stałym n. Powłoka wszędzie ≥3 wokseli.

Koszt B′ rośnie z ~12 min (gdyby był na 192³) do ~75 min (na 288³).

## Co jest ustalone i nie wymaga powtórzenia

- **Punkt pracy: (F,k) = (0.042, 0.062).** Jedyny z testowanych, przy
  którym wszystkie trzy topologie żyją i żadna nie ociera się o bramkę
  nasycenia (fill 0.616–0.618).
- **Horyzont z reguły §7 = 12060** → **67000 kroków przy 288³**,
  odpowiednio 45000 przy 192³ (kroki ∝ n). Reguła zastosowana do
  `viab288_fixed_60k`: plateau shell 3060, distributed 3240, central 6030;
  wszystkie trzymają ostatnie 20%.
- **Kryteria zamrożone** (`CRITERIA_v2.md`), historia zmian w
  `CHANGELOG.md`.

## Wynik pilotażowy — status „sugeruje", NIE orzeka

τ_border (n=1, `viab288_fixed_60k`, czysty zasiew):

```
distributed 900  <  shell 1890  <  central 4770
```

Uporządkowanie stabilne dla progów 1%–50% wartości końcowej.

## Do zrobienia po powrocie, w kolejności

1. **Ratyfikować B′** (lub wskazać inny wariant).
2. **Miarka wrażliwości** — przerwana w połowie, `sens_192/` jest pusty.
   Powtórzyć w całości:
   ```
   python3 scope_sensitivity.py --grid 192 --steps 45000 --record-every 500 \
     --F 0.042 --k 0.062 --pct 2.0 --shell-thickness 3.0 \
     --topology central --seed 1000 --outdir sens_192
   ```
   ~12 min.
3. **Zestaw konfirmacyjny**, ziarna 2000+ (rozłączne z pilotem 1000+):
   ```
   # A — podstawowy, n=16
   python3 scope_topology_v2.py --grid 192 --steps 45000 --record-every 500 \
     --F 0.042 --k 0.062 --shell-thickness 3.0 --n-runs 16 --seed-base 2000 \
     --outdir conf_A_192

   # B' — rozplatujace, shell only, n=12   (PO RATYFIKACJI)
   python3 scope_topology_v2.py --grid 288 --steps 67000 --record-every 500 \
     --F 0.042 --k 0.062 --shell-thickness 4.5 --n-runs 12 --seed-base 2000 \
     --topologies shell --outdir conf_B_288

   # C — kontrolny, n=12
   python3 scope_topology_v2.py --grid 288 --steps 67000 --record-every 500 \
     --F 0.042 --k 0.062 --shell-thickness 3.0 --n-runs 12 --seed-base 2000 \
     --outdir conf_C_288
   ```
   Razem ~6 h na 4× RTX 4090.
4. **Werdykt**:
   ```
   python3 scope_analyze.py --primary conf_A_192 --control conf_C_288 \
     --yardstick sens_192/sensitivity.json
   ```
5. **Wykładnik skalowania τ z n** (warunek rewizji kroków z §7) — policzyć
   z pary A→B′ przez `scope_horizon.tau_scaling_exponent`. Jeśli > 1,
   kroki ∝ n są nieważne i trzeba je podnieść.

## Odtworzenie środowiska po restarcie instancji

Jeśli kontener przetrwał stop, nic nie trzeba robić. Jeśli został
odtworzony od zera:

```
pip install numpy matplotlib scipy
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

**Uwaga:** domyślne `pip install torch` daje build cu130, który nie działa
ze sterownikiem 575.51.03 (CUDA 12.9) — kończy się błędem „NVIDIA driver
too old". Konieczny jest indeks cu128.

Klucz wdrożeniowy do GitHuba: `/root/.ssh/id_ed25519_scope` plus wpis w
`/root/.ssh/config`. Jeśli kontener został odtworzony, klucz przepadł —
trzeba wygenerować nowy i dodać jako Deploy key (write access) w
`LukaszCiesielski-lodz/scope_ocw`.

## Stan repo

Wszystko wypchnięte na `github.com/LukaszCiesielski-lodz/scope_ocw`,
gałąź `main`. Poza gitem tylko `__pycache__/` i
`.claude/settings.local.json`.
