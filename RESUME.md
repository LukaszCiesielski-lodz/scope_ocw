# RESUME — stan pracy

## Aktualizacja 2026-07-24 — przejście na Kaggle, sonda, poprawka wydajności

Wykonawca zmienił się z instancji vast.ai (zatrzymanej, opis niżej,
zachowany jako historia) na notebooki Kaggle (2× T4 na sesję). Patrz
CLAUDE.md §4.

**Wariant B′ (288³, powłoka, grubość 4.5) — RATYFIKOWANY 2026-07-24.**
Blokada opisana niżej w sekcji historycznej jest zdjęta; komórki
konfirmacyjne poniżej używają tego wariantu.

### (1) Sonda na Kaggle użyła złego pipeline'u — do powtórzenia

Sonda 2×T4, 192³, 40000 kroków dała `central kappa(T)=0.46–0.54, tau=None`.
To **nie jest nowy wynik metodologiczny** — sonda wywołała `scope_run.py`
(cienki wrapper na `run_one` z `scope_topology.py`, v1, celowo bitowo
identyczny z oryginałem — patrz CHANGELOG), czyli:

- obserwablą był κ_gzip z podłogą nagłówka (Wada 1, FINDINGS.md), nie
  τ_border/diss z CRITERIA_v2 §1;
- punkt pracy był domyślny (F,k)=(0.06, 0.062) tego skryptu, nie zamrożony
  (0.042, 0.062) z CRITERIA_v2 §0 — `scope_run.py`/`scope_topology.py` nie
  mają nawet flagi na tamten punkt pracy jako domyślną.

κ(T) w paśmie 0.46–0.54 jest więc zgodne z tabelą podłogi gzip dla n≈192
(tam 0.939 dla pola martwego przy DOMYŚLNYM punkcie pracy — różne (F,k)
dają różne podłogi/dynamikę, więc liczba się nie zgadza 1:1, ale
mechanizm — zła obserwabla, zły punkt pracy — jest ten sam). `tau=None`
jest spójne z κ nigdy nie przechodzącym parytetu w tym reżimie.

**Nic z sondy nie unieważnia CRITERIA_v2.** Błąd jest w tym, który skrypt
i z jakimi flagami odpalono, nie w kryteriach. Poprawka: komórki niżej
wywołują `scope_topology_v2.py` jawnie z `--F 0.042 --k 0.062`.

### (2) Wąskie gardło `masked_laplacian` — poprawione w v2, do zweryfikowania na Kaggle

Traceback lokalizował procesy w `masked_laplacian`
(`scope_topology.py`), linia `lap = lap + m_nb * (f_nb - f)` — 12 rolli,
~24 tensory 192³/krok, dławi przepustowość pamięci GPU. Zmierzony realny
czas: 1010 s/przebieg (~16.8 min) na T4 przy 192³.

**Poprawka (`scope_laplacian.py`, nowy plik, `scope_topology.py` NIE
dotknięty):** stały kernel conv3d 3×3×3 (środek=−6, sześć sąsiadów=+1)
plus jednorazowo policzona korekta brzegowa `(6 − deg)` na maskę no-flux
Neumanna (deg = liczba sąsiadów w domenie, 6 w środku, mniej na brzegu —
patrz docstring w pliku dla wyprowadzenia). `scope_topology_v2.py`
przełączony na tę implementację; `scope_topology.py`/`scope_run.py` (v1,
zapis audytowy) **niezmienione**, dalej bitowo identyczne ze sobą.

**Status bramki równoważności (CRITERIA dla tej zmiany: kryterium
przyjęcia = smoke 32³/400 kroków, max|Δ| < 1e-6 na u i v; przy
niepowodzeniu nie mergować):**

- **Zweryfikowane LOKALNIE na CPU** (ten sandbox nie ma GPU/CUDA):
  `python3 scope_test_laplacian_equivalence.py --grid 32 --steps 400` →
  max|Δu|=2.68e-7, max|Δv|=2.38e-7 (najgorsza z 3 topologii) — **PASS**,
  margines >3× wobec progu. Rozszerzony, niewiążący check do 4000 kroków:
  błąd rośnie w przybliżeniu liniowo (≈2.4e-6 przy 4000 kroków), bez
  oznak niestabilności/rozjazdu wykładniczego.
- **NIE zweryfikowane na docelowym sprzęcie (T4).** Ścieżki
  zmiennoprzecinkowe CPU i cuDNN conv3d na GPU różnią się kolejnością
  sumowania — zgodność lokalna nie jest dowodem zgodności na GPU, tylko
  mocną przesłanką (to ta sama operacja algebraicznie, patrz docstring
  `scope_laplacian.py`). **Komórka A niżej musi wypisać PASS na Kaggle
  przed czymkolwiek dalej.**
- **Speedup NIE zmierzony na GPU.** Lokalny (CPU) pomiar
  `scope_bench_laplacian.py` wyszedł na NIEKORZYŚĆ conv3d (0.4×, wolniej
  niż wersja roll-based) — to oczekiwane i nieinformacyjne dla kierunku
  na GPU: cały zysk ma źródło w przepustowości pamięci i liczbie
  uruchomień kerneli na GPU (cuDNN), czego CPU nie odtwarza. **Komórka B
  niżej daje prawdziwą liczbę; jeśli < 3×, doważyć `--compile`
  (torch.compile) zanim szuka się dalszej optymalizacji — zgodnie z
  instrukcją, compile jest drugim krokiem, nie pierwszym.**
- **Nic nie zostało jeszcze commitowane/wypchnięte.** Zmiana czeka na
  zielony wynik komórki A (i najlepiej sensowny wynik komórki B) na
  Kaggle.

### Komórki Kaggle (wklejać dokładnie w tej kolejności, nowa sesja)

```python
# Komórka 0 — setup sesji
!git clone https://github.com/LukaszCiesielski-lodz/scope_ocw.git /kaggle/working/scope_ocw 2>/dev/null || true
%cd /kaggle/working/scope_ocw
!git pull
!nvidia-smi --query-gpu=name,memory.total --format=csv
import torch
print(torch.__version__, "gpus:", torch.cuda.device_count())
```

```python
# Komórka A — brama równoważności (MUSI wypisać PASS zanim cokolwiek dalej)
!python3 scope_test_laplacian_equivalence.py --grid 32 --steps 400
```

```python
# Komórka B — pomiar przyspieszenia, 192^3/2000 kroków, PRZED pushem
!python3 scope_bench_laplacian.py --grid 192 --steps 2000
# jeśli speedup < 3x, doważyć compile:
# !python3 scope_bench_laplacian.py --grid 192 --steps 2000 --compile
```

```python
# Komórka C — konfirmacja A: podstawowa, 192^3, n=16, wszystkie 3 topologie
!python3 scope_topology_v2.py --grid 192 --steps 45000 --record-every 500 \
  --F 0.042 --k 0.062 --shell-thickness 3.0 --n-runs 16 --seed-base 2000 \
  --outdir conf_A_192
```

```python
# Komórka D — konfirmacja B': rozplątująca, 288^3, TYLKO shell, n=12
!python3 scope_topology_v2.py --grid 288 --steps 67000 --record-every 500 \
  --F 0.042 --k 0.062 --shell-thickness 4.5 --n-runs 12 --seed-base 2000 \
  --topologies shell --outdir conf_B_288
```

```python
# Komórka E — konfirmacja C: kontrolna, 288^3, n=12, wszystkie 3 topologie
!python3 scope_topology_v2.py --grid 288 --steps 67000 --record-every 500 \
  --F 0.042 --k 0.062 --shell-thickness 3.0 --n-runs 12 --seed-base 2000 \
  --outdir conf_C_288
```

**Czym różnią się A / B′ / C** (identyczne we wszystkich trzech: `--F
0.042 --k 0.062 --record-every 500 --seed-base 2000`):

| | `--grid` | `--steps` | `--shell-thickness` | `--n-runs` | `--topologies` | `--outdir` |
|---|---|---|---|---|---|---|
| **A** | 192 | 45000 | 3.0 | 16 | (domyślne: wszystkie 3) | `conf_A_192` |
| **B′** | 288 | 67000 | 4.5 | 12 | `shell` (tylko) | `conf_B_288` |
| **C** | 288 | 67000 | 3.0 | 12 | (domyślne: wszystkie 3) | `conf_C_288` |

`--steps` różni się między A i B′/C, bo horyzont skaluje się z n (§7
CRITERIA_v2: 12060 przy skalowaniu bazowym → 45000 przy 192³, 67000 przy
288³, kroki ∝ n). Bok A→B′ mierzy czysty efekt n przy stałej frakcji
zasiewu (grubość 3.0 vs 4.5 kompensuje zmianę n — patrz FINDINGS.md,
tabela wariantu zastępczego); bok B′→C mierzy czysty efekt frakcji przy
stałym n=288.

**Budżet sesji Kaggle:** przy starej implementacji (1010 s/przebieg na
T4) sama konfirmacja A (3 topologie × 16 = 48 przebiegów / 2 GPU = 24
sekwencyjnie na GPU) to ~6.7 h — poza jedną sesją. Realny budżet po
poprawce conv3d zależy od zmierzonego na Kaggle speedupu (komórka B).
Podział zestawu A/B′/C na sesje wg budżetu — **czeka na sondy timingowe
(2×T4 vs P100), które ŁC przyniesie po zielonym teście i pushu.** Nie
zakładać podziału z góry.

---

## Historia — stan na 2026-07-23, przerwane na stop instancji vast.ai

Instancja vast.ai 45611992 (4× RTX 4090) zatrzymana przez ŁC. Wszystkie
zadania GPU zatrzymane czysto, żadne obliczenie nie było w trakcie zapisu.
Sekcja zachowana jako zapis audytowy; wykonawca zmienił się na Kaggle
(patrz wyżej).

### Jedyna rzecz blokująca (ROZWIĄZANE 2026-07-24 — patrz wyżej)

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

1. ~~Ratyfikować B′~~ — **zrobione 2026-07-24**, patrz aktualizacja na
   górze pliku.
2. **Miarka wrażliwości** — przerwana w połowie, `sens_192/` jest pusty.
   Powtórzyć w całości:
   ```
   python3 scope_sensitivity.py --grid 192 --steps 45000 --record-every 500 \
     --F 0.042 --k 0.062 --pct 2.0 --shell-thickness 3.0 \
     --topology central --seed 1000 --outdir sens_192
   ```
   Szacunek ~12 min pochodzi z 4× RTX 4090 — na Kaggle (2× T4) przeszacować
   dopiero po sondach timingowych (patrz aktualizacja na górze pliku).
3. **Zestaw konfirmacyjny**, ziarna 2000+ (rozłączne z pilotem 1000+) —
   dokładne komendy (jako komórki Kaggle) i tabela różnic A/B′/C: patrz
   sekcja **„Aktualizacja 2026-07-24"** na górze tego pliku. Budżet czasowy
   ~6 h zakładał 4× RTX 4090 i jest nieaktualny dla 2× T4 — nie
   ekstrapolować bez zmierzonego speedupu (komórka B tamtej sekcji).
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
