# FINDINGS — eksperyment topologiczny, 2026-07-23

Zapis audytowy. Maszyna: 4× RTX 4090 (vast.ai, instancja 45611992),
torch 2.11.0+cu128. Sterownik `scope_run.py` zweryfikowany jako **bitowo
identyczny** z `scope_topology.py` (6/6 przebiegów, max |Δκ| = 0.000e+00),
więc żadne z poniższych nie wynika ze zrównoleglenia.

Przebieg `results_x1` (96³, 20000 kroków, 3 topologie × 8 przebiegów)
wykonany zgodnie z §4 CLAUDE.md, w 1,7 min. Wynik jest **zdegenerowany**.
Poniżej trzy niezależne wady, każda wystarczająca, by unieważnić κ jako
miarę eksportu w obecnej postaci.

---

## Wada 1 — κ→1 to podłoga nagłówka gzip, rosnąca z rozmiarem siatki

Dla pola **całkowicie jednorodnego** (zero struktury) `K_compress` zwraca
sam narzut nagłówka gzip na woksel. Ponieważ `border` jest ~3× większy
objętościowo niż `inner` (0.386 vs 0.125 objętości kuli R), narzut na
woksel jest mniejszy w `border`, a iloraz dąży do 1 wraz z n:

| n | 32 | 48 | 64 | 96 | 128 | 192 | 256 | 288 |
|---|---|---|---|---|---|---|---|---|
| κ_floor | 0.379 | 0.420 | 0.501 | **0.704** | 0.830 | **0.939** | 0.973 | 0.980 |

W `results_x1` topologie `shell` i `distributed` dają κ(T) = **0.7036269**
z odchyleniem **dokładnie 0.0** we wszystkich 8 przebiegach, przy
K_inner = 0.00173 i K_border = 0.00122 — co do cyfry wartości podłogi dla
n=96. Te pola są martwe; mierzony jest kompresor, nie dynamika.

**Konsekwencja dla §5.** Zamrożone kryterium („κ(t) nakłada się między 96³
a 192³ → homogenizacja") jest skonfundowane: przy zerowej fizyce κ i tak
rośnie z 0.704 na 0.939. Model zerowy przesuwa się razem z testem, więc
tak zapisany test nie rozróżnia eksportu od homogenizacji w żadną stronę.

**Konsekwencja dla papieru.** Raportowane κ(T)=1.003 (sfera) vs 0.998
(kartezjan) leży w zakresie, który produkuje martwe lub prawie jednorodne
pole na dużej siatce. To nie dowodzi, że wynik papieru jest artefaktem —
ale dopóki nie pokazano K ponad podłogą, nie jest odróżnialny od artefaktu.
Zarzut 3 z recenzji (§1 CLAUDE.md) okazuje się poważniejszy niż zakładano:
problemem nie jest brak definicji K, tylko że K bez korekty podłogi nie
jest miarą złożoności.

## Wada 2 — drugi, niezależny kanał do κ≈1: nasycenie domeny

Skan (F,k) (`scan_fk/scan.json`, 63 punkty, 96³, 20000 kroków) pokazuje,
że gdy wzorzec **wypełnia** domenę (fill→1), oba regiony są jednakowo
ustrukturyzowane i κ→1 trywialnie. Wartości κ_raw dla żywych,
propagujących punktów: 0.901, 0.958, 0.967, 0.976, 0.985, 0.988, 1.003,
1.004, 1.032, 1.039, 1.049.

Rozrzut po samych (F,k) wynosi **~0.15**, przy czym rozrzut wokół 1.00
to ±0.03. Papier raportuje różnicę geometrii 0.005 i delty sweepu
0.02–0.03 — czyli **poniżej lub na poziomie rozrzutu generowanego przez
sam wybór parametrów**, niezależnie od geometrii. To kwantyfikuje zarzut 2
z recenzji: różnica nie jest „na poziomie szumu" w sensie szumu losowego,
tylko na poziomie systematycznej wrażliwości na (F,k).

## Wada 3 — zasiew `shell` jest wadliwy i łamie własną kontrolę

`seed_fields` dla `shell` startuje z półgrubością th=0.5 i **tylko ją
zwiększa**, przerywając na pierwszej próbie, która przekracza cel. Cel
(0.7% domeny) jest przekroczony już przy th=0.5, więc pętla kończy się
natychmiast:

| n | central | shell | distributed |
|---|---|---|---|
| 96 | 2512 (0.697%, 1.00× celu) | **14088 (3.908%, 5.58× celu)** | 2503 (0.694%, 0.99× celu) |
| 192 | 20336 (0.705%, 1.01× celu) | **55568 (1.926%, 2.75× celu)** | 19996 (0.693%, 0.99× celu) |

Trzy skutki:

1. **Deklarowana kontrola nie obowiązuje.** Docstring i §2 CLAUDE.md
   twierdzą, że objętość zasiewu jest wyrównana i różni się tylko rozkład
   przestrzenny. `shell` dostaje 5,6× więcej materiału.
2. **Naruszenie zależy od rozmiaru siatki** (5.58× → 2.75×). Test
   skalowania 96³→192³ zmienia więc ramię `shell` w sposób, w jaki nie
   zmienia pozostałych — kontrola skali miesza topologię z objętością
   zasiewu.
3. **Powłoka ma 1 woksel grubości** i jest niszczona przez dyfuzję, zanim
   reakcja zdąży ją wzmocnić. W teście żywotności (`scan_topo/`) `shell`
   **wygasł przy wszystkich 8 testowanych parach (F,k)**, w tym przy
   wariantach dobrze oddalonych od bifurkacji.

Ramię `shell` nigdy więc realnie nie działało.

## Co z tego wynika dla wyniku smoke-testu z §5

CLAUDE.md §5 notuje uporządkowanie `central > shell > distributed` z
28³ jako „kierunek zgodny z intuicją supernowej". Przy 96³ z ensemble:

- κ(T): central **0.301 ± 0.010** (żywy), shell **0.7036 ± 0.000**
  (martwy, podłoga), distributed **0.7036 ± 0.000** (martwy, podłoga).
- τ: `shell` przekracza parytet w **8/8** przebiegów z τ = 36.0 ± 0.0 —
  ale to pierwszy zapis po starcie, czyli **własna struktura zasiewu przed
  wygaśnięciem**, nie zdarzenie eksportu. `central` i `distributed`: 0/8.

Zastosowanie zamrożonych kryteriów §5 dosłownie dałoby wniosek „shell
eksportuje najszybciej, τ=36±0, odstęp nieskończenie wielu σ" — czyli
wynik maksymalnie „istotny" i całkowicie pozbawiony treści fizycznej.
Dwa martwe ramiona mają σ=0, więc każde kryterium typu „odstęp > 2σ"
przechodzi automatycznie.

To jest samodzielny wniosek metodologiczny: **kryterium oparte na odstępie
w jednostkach σ jest niebezpieczne przy mierze, która ma zdegenerowaną
podłogę.**

## Uwaga do warunku bifurkacji

Domyślne (F,k) = (0.060, 0.062) spełnia warunek istnienia niezerowego
jednorodnego stanu stacjonarnego GS, F ≥ 4(F+k)², z zapasem **+0.78%**.
Zastrzeżenie: ten warunek dotyczy stanu **jednorodnego**; struktury
zlokalizowane (reżim Pearsona, samoreplikujące się plamy) utrzymują się
też poniżej progu — w skanie punkty z ujemnym marginesem (np. F=0.030,
k=0.060, margines −7.4%) pozostawały żywe. Marginalność (F,k) nie jest
więc sama w sobie dowodem błędu, ale w połączeniu z Wadą 3 tłumaczy,
czemu akurat `shell` ginie najpierw.

---

## Rozstrzygnięcie: czy test zakłada koszt termodynamiczny? Nie — i to jest przyczyną

Diagnoza (ŁC, w trakcie sesji): κ oparta na gzip mierzy **długość opisu**
konfiguracji i jest ślepa na koszt jej utrzymania. Gray-Scott jest układem
dyssypatywnym — `F(1−u)` pompuje, `(F+k)v` odprowadza — więc koszt w
modelu istnieje, tylko κ go nie czyta. To jest wspólny mechanizm Wady 1
i Wady 2: ani pole martwe, ani nasycone nie jest za nic obciążane.

Obserwable kosztowe (`scope_thermo.py`), gęstości, więc intensywne
względem siatki:

- `D(x) = Du|∇u|² + Dv|∇v|²` — dyssypacja, **dokładnie zero** dla pola
  jednorodnego; brak podłogi, brak zależności od n
- `R(x) = u v²` — przepustowość autokatalizy
- `W(x) = F(1−u)` — praca pompowania

Pomiar równoległy na tych samych trajektoriach (`cmp_metrics/compare.json`,
96³, 20000 kroków):

| (F,k) | topologia | κ_gzip | κ_exc | diss_ratio | fill |
|---|---|---|---|---|---|
| 0.060, 0.062 | central | 0.3011 | 0.3004 | 0.3634 | 0.425 |
| 0.060, 0.062 | shell | 0.7036 | nan | **0.0** (diss 1.6e-14) | 0.000 |
| 0.060, 0.062 | distributed | 0.7036 | nan | nan (diss 4.7e-15) | 0.000 |
| 0.046, 0.060 | central | **1.0041** | 1.0046 | **1.2029** | 0.846 |
| 0.046, 0.060 | distributed | 0.9964 | 0.9969 | 0.9672 | 0.868 |
| 0.042, 0.062 | central | 0.9014 | 0.9018 | 1.0878 | 0.589 |
| 0.042, 0.062 | distributed | 0.9829 | 0.9834 | 1.0037 | 0.612 |

Trzy wnioski:

1. **Martwe pole dostaje twarde zero.** κ_gzip raportuje 0.7036 — liczbę
   wyglądającą na pomiar. Dyssypacja raportuje 10⁻¹⁴.
2. **Sama korekta podłogi jest niewystarczająca.** κ_exc różni się od
   κ_gzip dopiero na czwartym miejscu po przecinku (0.3004 vs 0.3011;
   1.0046 vs 1.0041). Korekta podłogi naprawia przypadek martwy, ale nie
   nasycony. Dopiero miara kosztowa wnosi informację: tam gdzie κ_gzip
   spłaszcza do 1.004, diss_ratio daje 1.2029.
3. **Miara kosztowa może przekroczyć parytet.** To bezpośrednia odpowiedź
   na zarzut 1 z recenzji. κ_gzip nie przekracza parytetu, bo jest
   zaduszona sufitem nasycenia — nie dlatego, że układ nie eksportuje.
   diss_ratio = 1.20 to realny nadmiar kosztu na granicy nad rdzeniem.

Zastrzeżenie rejestrowe (§7): GS nie jest modelem zgodnym
termodynamicznie, a |∇|² to **analogia** dyssypacji, nie produkcja
entropii. Uzasadnienie jest operacyjne — to miara kosztu z prawdziwym
zerem, czyli dokładnie tym, czego proxy gzip nie ma.

## Wada 3 jest głębsza, niż wygląda: wyrównanie objętości jest geometrycznie niewykonalne

Powłoka o objętości 0.7% domeny wymaga grubości **subwokselowej**:

| n | grubość dla 0.7% | powłoka 1-wokselowa | powłoka 3-wokselowa |
|---|---|---|---|
| 96 | 0.18 wok. | 3.82% domeny (5.46× celu) | 11.46% |
| 192 | 0.37 wok. | 1.91% (2.73×) | 5.73% |
| 288 | 0.55 wok. | 1.27% (1.82×) | 3.82% |
| 384 | 0.73 wok. | 0.96% (1.36×) | 2.87% |

To nie jest usterka implementacji — to sprzeczność w projekcie
eksperymentu. Deklarowana kontrola („objętość wyrównana, różni się tylko
rozkład przestrzenny") nie jest osiągalna przy 0.7% w żadnej
implementacji na siatce 96³. Dodatkowo powłoka musi mieć ~3 woksele, by
przeżyć dyfuzję (droga dyfuzyjna √(Dv·T) ≈ 17 wokseli w trakcie
przebiegu), a to podnosi wymuszoną frakcję zasiewu jeszcze bardziej.
Rozdzielczość jest jedyną dźwignią, która to łagodzi.

## Wada 4 — `distributed` zasiewa wprost w region pomiarowy

Bloby były rozmieszczane w obrębie 0.9R, podczas gdy region pomiarowy
`border` zaczyna się na 0.85R. Przy 288³ **12.91% zasiewu `distributed`
lądowało wewnątrz border**, wobec dokładnie 0% dla `central` i `shell`.
Widać to w danych: `diss_border(t=0)` = 3.28e-4 dla distributed przy 0.0
dla pozostałych dwóch, a pierwsze przejście „struktura dotarła do
granicy" wynosi dla niego τ = 0 z konstrukcji.

Topologia wstępnie ładuje region, do którego mierzone jest przybycie.
Każde porównanie czasów pierwszego przejścia z udziałem `distributed`
było przez to zdyskwalifikowane.

Poprawka (`scope_seed.py`): środki blobów ograniczone do
`0.85R − r_blob`, więc bloby leżą w całości poza powłoką pomiarową.
Po poprawce kontaminacja wynosi 0.00% dla wszystkich trzech topologii,
przy zachowanym wyrównaniu objętości (match 1.0009 / 1.0000 / 1.0065).

## Pułapka miary kosztowej — błąd popełniony i naprawiony w tej sesji

Miara kosztowa ma własną wersję artefaktu progowego i wpadłem w nią.
Pierwotny strażnik dzielenia w `thermo_observables` stał na `ci > 1e-14`.
Zmierzona trajektoria `shell` przechodzi:

```
diss_inner:  0 → 2.9e-39 → 2.2e-33 → 2.1e-32 → … → 2.3e-16 → 7.6e-4 → 1.65e-3
```

czyli szum zmiennoprzecinkowy rozciąga się do ~1e-16, a fizyka zaczyna
się od ~1e-4. Próg 1e-14 leżał **na krawędzi pasma szumu**. Gdy
mianownik, fizycznie wciąż zerowy, przez niego przedryfował, iloraz
osiągnął **1.54e10** i wygenerował **fałszywe pierwsze przejście
τ = 1980** — tę samą klasę błędu co artefakt τ = 36 w kanale gzip.

Poprawka: `DISS_FLOOR = 1e-8`, osadzony w dwunastorzędowej przepaści
między szumem a fizyką (8 rzędów nad szumem, 4 pod fizyką), a nie dobrany
arbitralnie. Iloraz jest `nan`, dopóki rdzeń nie niesie kosztu — iloraz
względem fizycznie pustego mianownika jest **nieokreślony, a nie duży**.
Po poprawce τ dla `shell` wynosi 2700 zamiast 1980.

Wniosek ogólny: przejście na miarę kosztową usuwa podłogę, ale **nie
usuwa potrzeby jawnego progu ważności**. Każdy iloraz dwóch wielkości,
które mogą być zerowe, wymaga zadeklarowanego pasma ważności.

## Obserwacja projektowa: pomiar w t=T jest niediagnostyczny

Sonda 288³ (30000 kroków, (F,k)=(0.042,0.062)) pokazuje, że pod koniec
przebiegu topologie **zbiegają się**:

| topologia | diss_inner(T) | diss_ratio(T) | fill(T) | τ_border (diss_bd > 1e-6) |
|---|---|---|---|---|
| central | 1.64e-3 | 0.7053 | 0.503 | 4410 |
| shell | 1.65e-3 | 1.0041 | 0.615 | 1170 |
| distributed | 1.66e-3 | 0.9969 | 0.612 | 0 (kontaminacja, przed poprawką) |

`diss_inner` zrównuje się do trzeciego miejsca znaczącego. Informacja
różnicująca leży w **transjencie i w czasach**, nie w stanie końcowym —
co jest dokładnie tym, o co pyta hipoteza (b) z §1 CLAUDE.md („czy
topologia PRZESTRZENNA przewiduje statystykę CZASOWĄ"). Sugeruje to
przesunięcie obserwabli głównej z `diss_ratio(T)` na czasy pierwszego
przejścia `τ_border`. Wymaga decyzji przed zamrożeniem kryteriów.

Sygnał wstępny (n=1, **nie jest wynikiem**): `shell` oddaje strukturę do
granicy ~3.8× wcześniej niż `central` (1170 vs 4410).

## Warunek wstępny ramienia rozplątującego — NIE przechodzi

Test powłoki 2-wokselowej przy 192³, (F,k) = (0.042, 0.062),
`viab192_th2/`: **wygasa natychmiast.** fill = 0.038 w t=0, fill = 0 od
t=90, diss_inner(T) = 8.2e-15, κ_gzip(T) = 0.9390 — co do cyfry podłoga
dla n=192.

Wniosek ogólny: **przeżywalność dyfuzyjna zależy od grubości bezwzględnej
w wokselach, nie od frakcji objętości.** Teza „grubość ∝ n daje
samopodobieństwo" jest geometrycznie poprawna, ale fizycznie fałszywa —
skalowanie w dół przekracza próg przeżywalności. Interpretacja B
(samopodobieństwo) z §6.2 CRITERIA_v2 jest więc realizowalna wyłącznie
w górę.

Przy okazji ujawniony błąd w `run_one_v2`: flaga `alive` była liczona jako
**maksimum po trajektorii**, więc wczesny transjent przed wygaśnięciem
przepuszczał martwy przebieg jako żywy (raport: `alive=1` dla powyższego).
Poprawione na odczyt w t=T względem `DISS_FLOOR`. To ta sama klasa błędu,
którą wcześniej poprawiono w bramkach analizatora — tu przetrwała
w rekorderze.

### Wariant zastępczy trójkąta (do ratyfikacji)

Zamiast ścieniać powłokę na mniejszej siatce, pogrubić ją na większej:

| | siatka | grubość | frakcja | central max_r | B5 |
|---|---|---|---|---|---|
| **A** podstawowy | 192³ | 3.0 | 5.71% | 0.385R | OK |
| **B′** rozplątujące | 288³ | 4.5 | 5.73% | 0.386R | OK |
| **C** kontrolny | 288³ | 3.0 | 3.81% | 0.337R | OK |

- bok **A→B′**: stała frakcja (5.71 vs 5.73), zmienne n → czysty efekt n
- bok **B′→C**: stałe n = 288, frakcja 5.73 → 3.81 → czysty efekt frakcji
- powłoka wszędzie ≥ 3 wokseli, więc próg przeżywalności zachowany

`shell` pozostaje właściwą topologią dla ramienia B′ z powodu mocniejszego
niż ekonomia: zmiana frakcji realizuje się dla niego przez grubość, przy
**niezmienionym r₀ = 0.75R**, więc odległość do granicy jest stała. Dla
`central` zmiana frakcji zmienia promień kuli (0.337R → 0.386R), czyli
mieszałaby efekt frakcji z efektem odległości do granicy.

## Stan plików

- `results_x1/` — przebieg wg §4, zachowany jako zapis audytowy mimo
  zdegenerowanego wyniku (§7: wyniki commitować).
- `scan_fk/scan.json` — 63 punkty (F,k), diagnostyka alive/reach/fill.
- `scan_topo/viability.json` — 8 kandydatów × 3 topologie.
- `results_x2/` — **nie uruchomiono.** Przy obecnej definicji κ ten
  przebieg zmierzyłby przesunięcie podłogi gzip, nie fizykę.

## Ramię A (konfirmacja) — wynik, 2026-07-31

Ramię A (192³, n=16, τ_border, próg 10% wartości końcowej): distributed
360 < shell 1350 < central 3330; log-rank p_Holm=7.7e-08 dla wszystkich
par; stabilne dla progów 1–50%; wszystkie 48 przebiegów alive,
seeded_fraction ~5.72%; werdykt NIEROZSTRZYGNIETE zgodnie z CRITERIA_v2,
oczekuje testu skalowania w B′.

## Dekompozycja τ_border: aktywacja vs transport (2026-08-20)

Recenzja: τ_border może być zdominowane odległością radialną, nie
topologią. `front_from_fill.py` rozkłada τ_border na proxy aktywacji
(czas do 10% znormalizowanego fill φ_norm) i proxy transportu
(τ_border − t_act), korzystając z fill(t) już zapisanego w runs.json.

Kluczowy wynik: `fill(t=0) ≈ 0.057` dla wszystkich trzech topologii (sam
zasiew), więc surowy próg 5% jest zdegenerowany — stąd normalizacja
φ_norm(t) = [φ(t) − φ(0)] / [1 − φ(0)].

Wynik dekompozycji na `conf_A_192` (192³): aktywacja porządkuje
topologie inaczej niż transport. `t_act` szybkie dla shell/distributed
(90/180), rząd wielkości wolniejsze dla central (2250) — spójne z
surface-to-volume pojedynczego zwartego zasiewu. `t_tr` (transport)
krótkie dla distributed (180), ale porównywalne dla shell i central
(1260 vs 1080) mimo maksymalnie różnych promieni środka masy zasiewu
(0.75R vs 0) — model stałej prędkości frontu (odległość/prędkość) tego
nie przewiduje. Tempo ekspansji dφ_norm/dt w oknie 10%→40% różni się
~4× między topologiami (distributed 5.1e-4, central 2.2e-4, shell
1.3e-4), więc pojedyncza prędkość frontu nie zamyka się na danych.

Wniosek wprowadzony do DRAFT.md jako nowa III.E + Tabela IV (Revision
B): roszczenie zawężone z "topology" na "seed geometry"; tytuł i
abstrakt zmienione; IV.A/B/C/D zrewidowane pod kątem uczciwej atrybucji
mechanistycznej. Statystyka i Tabele I–III bez zmian.

Pełny output `front_from_fill.py --runs conf_A_192/runs.json`:

```
=== time to reach RAW fill milestones (median over runs) ===
 level | distributed |       shell |     central
    5% |           0 |           0 |           0
   10% |          90 |          90 |        1980
   20% |         270 |        1620 |        2520
   30% |         360 |        2070 |        3060
   40% |         630 |        2250 |        3420
   50% |         990 |        2610 |        3780

=== time to reach NORMALIZED f_norm milestones (f_norm = (fill-fill0)/(1-fill0)) (median over runs) ===
 level | distributed |       shell |     central
    5% |          90 |          90 |        2070
   10% |         180 |          90 |        2250
   20% |         270 |        1890 |        2700
   30% |         450 |        2160 |        3240
   40% |         765 |        2340 |        3600
   50% |        1080 |        2790 |        3870

=== mean expansion rate d(f_norm)/dt in the 10%->40% window ===
(if topologies share a rate, tau ordering is geometry/distance;
 if rates differ, there is a shape/topology component)
  distributed: 5.128e-04 /unit   (t10=180, t40=765)
        shell: 1.333e-04 /unit   (t10=90, t40=2340)
      central: 2.222e-04 /unit   (t10=2250, t40=3600)

=== transport time: tau_border - t_act (f_norm=10% activation proxy) ===
   topology |      t_act | tau_border |  transport
distributed |        180 |        360 |        180
      shell |         90 |       1350 |       1260
    central |       2250 |       3330 |       1080

=== referee's model on f_norm-onset: activation + distance/speed ===
seed mass-center radii (voxels, 192^3, R=96): distributed~0, shell~72, central~0
NOTE: distributed and central both have small mass-center radius;
      the discriminating pair is shell (r=72) vs central (r=0).
activation proxy (distributed time to 10% f_norm): 180
```
