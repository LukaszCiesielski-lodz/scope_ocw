# RESUME — stan pracy

## Aktualizacja 2026-08-19 — Figure 1 wygenerowana (`make_figure1.py`)

Napisano `make_figure1.py` (czyste numpy + matplotlib, bez torcha —
odpalane lokalnie, nie na Kaggle) i wygenerowano `figure1.pdf`/`figure1.png`
do preprintu. Panel (a): krzywe przeżycia Kaplana-Meiera τ_border, 3
topologie × 2 siatki (192³/288³), próg detekcji 10% (ten sam co werdykt
`scope_analyze.py`). Panel (b): mediana τ_border w funkcji progu detekcji
(1–50%), sprawdza stabilność wyboru progu. Definicja τ_border identyczna
jak w `scope_analyze.py` (pierwsze przejście `diss_border` przez `frac`
własnej wartości końcowej; nieosiągnięte = cenzurowane na horyzoncie).

Wejście: `conf_A_192/runs.json`, `conf_C_288/runs.json` (pełne n=12 po
scaleniu C1+C2, patrz aktualizacja 2026-08-18 niżej). Mediany @ 10%
wypisane przez skrypt jako sanity check zgodne z wcześniej raportowanym
`scope_analyze.py`:

```
192³: distributed=360  shell=1350  central=3330
288³: distributed=855  shell=1890  central=4770
```

Porządek `distributed < shell < central` widoczny na obu panelach, bez
przecięć krzywych/serii między siatkami — wizualne potwierdzenie tego, co
już stwierdzał werdykt automatyczny. `make_figure1.py`, `figure1.pdf`,
`figure1.png` zacommitowane do repo (commity `97192a5`, `ca7c475`).

## Aktualizacja 2026-08-18 — ramię C domknięte w pełni, n=12, `conf_C_288`

Ramię C zostało pre-registered jako n=12 (ziarna 2000–2011), ale z powodu
limitu sesji Kaggle 9h wykonane technicznie w dwóch połowach: C1 (ziarna
2000–2005, zamknięte 2026-08-01, opisane niżej jako "połowa zestawu") i C2
(ziarna 2006–2011, dograne 2026-08-18). Oba przebiegi identyczne parametry
(288³, F=0.042, k=0.062, grubość powłoki 3.0, wszystkie 3 topologie).
Scalone w `conf_C_288/` (`runs.json` — 36 przebiegów, `summary.json` —
reagregacja; `conf_C1_288/` i `conf_C2_288/` pozostają nietknięte jako
źródła audytowe). Sanity check reagregacji: `n_alive=12/12` na każdą
topologię, `seeded_fraction` shell ≈3.81% (zgodne z obiema połowami),
`tau_diss_mean` shell ≈2760 (zgodne z ~2745 widzianym w C1 i C2 osobno).

Werdykt automatyczny przeliczony na pełnym zestawie
(`scope_analyze.py --primary conf_A_192 --control conf_C_288
--yardstick sens_192_shell_narrow/sensitivity.json`): **POTWIERDZONE
(warunkowo — decyzja o interpretacji miarki wrażliwości nadal pozostawiona
autorowi)**, ten sam werdykt jakościowy co przy n=6, ale teraz na pełnym
pre-registered n. Sekcja "Ramię C" niżej zaktualizowana na dane n=12;
sekcje odwołujące się do C1 (n=6) jako "połowy zestawu" zachowane w
historii jako opis stanu z 2026-08-01, ale **`conf_C_288` jest teraz
zestawem kontrolnym używanym w werdykcie**, nie `conf_C1_288`.

## Konfirmacja zamknięta 2026-08-01 (patrz aktualizacja 2026-08-18 wyżej)

Zestaw A + B′ + C1 + sonda parametryczna ±0.5% domknięty. Werdykt
automatyczny (`scope_analyze.py --primary conf_A_192 --control conf_C1_288
--yardstick sens_192_shell_narrow/sensitivity.json`): **POTWIERDZONE
(warunkowo — decyzja o interpretacji miarki wrażliwości pozostawiona
autorowi)**. Pełne wyjście skryptu i surowe dane w `conf_A_192/`,
`conf_B_288/`, `conf_C1_288/`, `sens_192_shell/`, `sens_192_shell_narrow/`.
C1 miało wtedy n=6 (połowa zaplanowanego n=12) — patrz aktualizacja
2026-08-18 wyżej dla domkniętego zestawu `conf_C_288` (n=12).

### Ramię A — podstawowe (`conf_A_192/`)

192³, F=0.042, k=0.062, n=16, ziarna 2000–2015, wszystkie 3 topologie.
Wszystkie 48 przebiegów żyje (n_alive=16/16 na topologię), bramki B1–B4
WAŻNE, frakcja zasiewu ~5.72%, fill(T)≈0.619 (poniżej progu nasycenia 0.9).
τ_border (próg 10% wartości końcowej, cenzura na horyzoncie T=8100),
mediany:

```
distributed 360  <  shell 1350  <  central 3330
```

Log-rank (Mantel-Cox) na wszystkich trzech parach, p_Holm ≈ 1.5e-07–1.9e-07
(korekta Holma na 6 porównaniach łącznie z ramieniem C1). Porządek
`distributed < shell < central` stabilny dla progów 1%, 5%, 10%, 25%, 50%
wartości końcowej.

### Ramię B′ — rozplątujące, test skalowania (`conf_B_288/`)

288³, tylko `shell`, grubość powłoki 4.5 (frakcja 5.73%, zachowana wobec A;
r0=0.75R niezmienione — patrz FINDINGS.md, "wariant zastępczy trójkąta"),
n=12, ziarna 2000–2011. 12/12 żyje, bramka WAŻNA. τ_border mediana = 1890.

Iloraz τ(B′)/τ(A, shell) = 1890/1350 = **1.40** — wpada w pre-registered
przedział [1.25, 1.75] zarejestrowany z góry 2026-07-31 (CHANGELOG, przed
uruchomieniem B′) dla hipotezy "transport frontowy" (droga frontu
reakcji-dyfuzji do granicy rośnie z rozmiarem domeny przy ~stałej
prędkości frontu). NIE w paśmie homogenizacji (≤1.15). Czysty efekt n przy
stałej frakcji zasiewu przeżywa więc test skalowania.

### Ramię C — kontrolne, pełny zestaw n=12 (`conf_C_288/`, scalone C1+C2)

288³, wszystkie 3 topologie, grubość 3.0, **n=12** (ziarna 2000–2011 —
pełny pre-registered zestaw ramienia C, wykonany w dwóch sesjach Kaggle ze
względu na limit 9h: C1 ziarna 2000–2005 [2026-08-01], C2 ziarna
2006–2011 [2026-08-18], scalone w `conf_C_288/` [2026-08-18] — patrz
aktualizacja na górze pliku). 36/36 żyje, wszystkie bramki WAŻNE. Frakcja
zasiewu ~3.81–3.83% — **zmniejszona względem A** (5.72%): świadomie
zaakceptowana konfundacja frakcji ze skalą, tak jak opisano przy
ratyfikacji wariantu B′ wyżej w tym pliku (grubość ∝ n nie daje
samopodobieństwa fizycznego, patrz też FINDINGS.md). τ_border mediany
(przeliczone na pełnym n=12, `scope_analyze.py`):

```
distributed 855  <  shell 1890  <  central 4770
```

**Ten sam porządek co A.** Log-rank, p_Holm ≈ 1.291e-06 dla wszystkich
trzech par kontrolnych (korekta Holma współdzielona z A, 6 porównań
łącznie) — o rząd wielkości mocniejsze niż przy n=6 (p_Holm ≈1.19e-03),
zgodnie z oczekiwaniem przy podwojeniu n. Porządek
`distributed < shell < central` zachowany na obu skalach (192³ i 288³) i
stabilny względem progu (1%–50% wartości końcowej, patrz wyjście
`scope_analyze.py`).

Ilorazy τ(C)/τ(A) (informacyjnie, poza formalną definicją testu
skalowania B′→A, która dotyczy wyłącznie `shell` przy stałej frakcji):

| topologia | τ(C, n=12) | τ(A) | iloraz | w widełkach transportu [1.25,1.75]? |
|---|---|---|---|---|
| shell | 1890 | 1350 | **1.40** | tak |
| central | 4770 | 3330 | **1.43** | tak |
| distributed | 855 | 360 | **2.38** | nie — spójne z konfundacją frakcji (3.82% vs 5.72%), nie z efektem skali samym w sobie |

(Przy n=6, czyli tylko C1, iloraz `distributed` wychodził 2.25 —
przesunięcie do 2.38 przy pełnym n=12 to szum próbki na tym ramieniu, nie
zmiana wniosku: nadal poza widełkami transportu, nadal czytane jako
konfundacja frakcji.)

### Sonda parametryczna ±0.5% — miarka wrażliwości (`sens_192_shell_narrow/`)

192³, `shell`, seed=1000 (zakres pilotażowy, rozłączny z konfirmacyjnym
2000+, zgodnie z konwencją projektu), 9 punktów siatki 3×3 w (F,k) wokół
bazy (0.042, 0.062), perturbacja ±0.5%. Rozrzut τ_border = **630 kroków**.
fill(T) w paśmie 0.595–0.643 — pozostaje w reżimie bazowym (baza ≈0.62),
perturbacja nie zmienia reżimu dynamicznego. **Ta miarka jest tą użytą w
werdykcie powyżej.**

Obserwacja z siatki punktów: τ_border w tym punkcie pracy jest znacznie
bardziej wrażliwe na `k` niż na `F` — przy zmianie samego `F` o ±0.5%
τ_border zostaje przy wartości bazowej (1350), przy zmianie samego `k`
o ±0.5% przesuwa się do 1080 / 1710. Rozrzut miarki jest więc niemal
w całości napędzany przez `k`, nie przez `F`.

### Sonda parametryczna ±2% — referencja negatywna (`sens_192_shell/`)

Wcześniejsza, szersza sonda: rozrzut τ_border = 3060, ale fill(T) rozjeżdża
się do 0.51–0.72 (baza 0.62) — perturbacja o tej amplitudzie wypycha część
punktów poza reżim roboczy, więc zmierzony rozrzut miesza szum
parametryczny ze zmianą reżimu. **Nie jest to prawidłowa miarka
wrażliwości** i nie jest użyta w werdykcie; pozostawiona w repo jako
referencja negatywna — przykład, dlaczego trzeba było zawęzić sondę do
±0.5% zamiast przyjąć pierwszy wynik.

### Marginesy efekt topologiczny / rozrzut parametryczny (rozrzut=630)

Trzy różnice median τ_border z ramienia A, podzielone przez rozrzut sondy
wrażliwości ±0.5%:

| para | Δτ_border (A) | margines (Δ / 630) |
|---|---|---|
| central vs distributed | 2970 | **4.71×** |
| central vs shell | 1980 | **3.14×** |
| shell vs distributed | 990 | **1.57×** |

### Uczciwa interpretacja naukowa

Solidny wynik częściowy. Hipoteza transportu topologicznego potwierdzona
ilościowo dla porównań central vs {shell, distributed} — marginesy 3.14×
i 4.71× powyżej rozrzutu parametrycznego, log-rank miażdżąco istotny dla
wszystkich par na obu skalach z korekcją Holma (p_Holm ≈1.5–1.9e-07 na A,
≈1.29e-06 na C przy pełnym n=12), porządek replikuje się 192³→288³, test
skalowania B′ (iloraz 1.40) i ilorazy C/A dla shell i central (1.40, 1.43)
trafiają w przedział pre-registered "transport frontowy". Dla porównania
shell vs distributed margines wynosi 1.57× — na granicy akceptowalności
metodologicznej, wyraźnie bliżej rozrzutu parametrycznego niż pozostałe
dwie pary, więc to porównanie jest tym, które najłatwiej byłoby podważyć
dodatkowym ziarnem albo węższą sondą. Iloraz τ(C)/τ(A) dla `distributed`
(2.38 na pełnym n=12, było 2.25 na n=6) leży poza widełkami transportu —
spójne z tym, że C zmienia frakcję zasiewu wobec A (3.82% vs 5.72%), nie
tylko n, więc to porównanie nie jest czystym testem skalowania i nie
powinno być czytane jako taki.

Wynik nie jest triumfem — jest rzemieślniczo domkniętą pracą do publikacji
z uczciwie opisanymi granicami interpretacji. Zastrzeżenie o n=6 na
ramieniu C (druga połowa nieodpalona) jest **rozwiązane od 2026-08-18** —
`conf_C_288` ma teraz pełne pre-registered n=12 (C1+C2 scalone,
reprodukowalność między sesjami Kaggle potwierdzona: dwie niezależne
połowy dały ten sam porządek i zgodne mediany). Pozostałe zastrzeżenie do
"warunkowo" w werdykcie: miarka wrażliwości pochodzi z jednej topologii
(`shell`) i jednego rozmiaru siatki (192³), nie z zestawu niezależnego od
ramion ocenianych.

---

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

**Stan faktyczny (uzupełnione retrospektywnie):** komórka E dla C
faktycznie nie zmieściła się w jednej sesji 9h nawet po poprawce conv3d,
więc odpalona jako dwie komórki z `--n-runs 6` każda: `--seed-base 2000
--outdir conf_C1_288` (2026-08-01) i `--seed-base 2006 --outdir
conf_C2_288` (2026-08-18), scalone lokalnie w `conf_C_288/` (patrz
aktualizacja 2026-08-18 na górze pliku). Komórki A i B′ zmieściły się w
pojedynczych sesjach zgodnie z planem powyżej.

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

Ta lista jest historyczna (stan sprzed uruchomienia jakichkolwiek
przebiegów konfirmacyjnych); pozycje 1–4 zostały od tego czasu wykonane,
w praktyce innymi konkretnymi komendami/plikami niż tu naszkicowano
(patrz aktualizacje na górze pliku dla faktycznego przebiegu). Zachowana
jako zapis, nie jako aktualny plan.

1. ~~Ratyfikować B′~~ — **zrobione 2026-07-24**, patrz aktualizacja na
   górze pliku.
2. ~~**Miarka wrażliwości**~~ — **zrobione**: sonda ±0.5%
   (`sens_192_shell_narrow/`) jest tą użytą w werdykcie; sonda ±2%
   (`sens_192_shell/`) zachowana jako referencja negatywna. Patrz sekcje
   „Sonda parametryczna" wyżej.
3. ~~**Zestaw konfirmacyjny**, ziarna 2000+~~ — **zrobione**: A
   (`conf_A_192/`, n=16), B′ (`conf_B_288/`, n=12), C (`conf_C_288/`,
   n=12, scalone z C1+C2 2026-08-18 — patrz aktualizacja na górze pliku).
4. ~~**Werdykt**~~ — **zrobione i przeliczone na pełnym C (n=12)**:
   ```
   python3 scope_analyze.py --primary conf_A_192 --control conf_C_288 \
     --yardstick sens_192_shell_narrow/sensitivity.json
   ```
   → POTWIERDZONE (warunkowo), patrz aktualizacja 2026-08-18 na górze
   pliku dla pełnego wyjścia.
5. **Wykładnik skalowania τ z n** (warunek rewizji kroków z §7) — **nadal
   otwarte**. Policzyć z pary A→B′ przez
   `scope_horizon.tau_scaling_exponent`. Jeśli > 1, kroki ∝ n są nieważne
   i trzeba je podnieść.

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
