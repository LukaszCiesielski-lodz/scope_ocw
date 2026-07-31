# CHANGELOG — kryteria decyzyjne projektu SCOPE

Zapis zmian w kryteriach oceny, prowadzony jawnie. Zamrożenie kryteriów,
które raz zmieniono pod wpływem danych, jest wiarygodne tylko wtedy, gdy
ślad tej zmiany jest publiczny.

---

## 2026-07-31 — pre-registration, przed odpaleniem B′

Widełki wyniku dla ramienia B′ (test skalowania samopodobnego, 288³, `shell`
only, n=12, ziarna 2000–2011) zarejestrowane przed odpaleniem w
`sensitivity.json` (`b_prime_scaling_prereg`): τ(B′)/τ(A) ∈ [1.25, 1.75] →
transport frontowy, ≤ 1.15 → homogenizacja, poza tymi zakresami →
nierozstrzygnięte.

---

## 2026-07-24 — `torch.compile` domyślnie włączony w pipeline v2 (ZMIANA IMPLEMENTACYJNA, nie protokołu)

**To nie jest zmiana kryteriów ani obserwabli**, z tego samego powodu co
wpis niżej o conv3d: dotyczy tylko tego, ile przebiegów mieści się w
sesji Kaggle, nie definicji obserwabli.

**Zmiana domyślnego zachowania.** `scope_topology_v2.py` kompiluje teraz
ścieżkę laplasjanu (`scope_laplacian.py`) i krok Eulera przez
`torch.compile`, bez flagi — **zawsze włączone, gdy urządzenie to CUDA**.
Wcześniej cała ścieżka była czysto eager. Na CPU (np. smoke test lokalny
bez GPU) zachowanie niezmienione — `torch.compile` nie jest nawet
próbowany.

**Fallback.** Jeśli kompilacja lub pierwsze wywołanie skompilowanej
funkcji rzuci wyjątkiem (np. brak Tritona na danym obrazie Kaggle),
proces drukuje ostrzeżenie i przełącza się trwale na wersję
nieskompilowaną (eager) dla reszty procesu — bieg NIE jest przerywany.
Nie ma trybu „spróbuj ponownie": po jednym niepowodzeniu dana sesja
workera zostaje w eager do końca, żeby nie płacić wielokrotnie kosztu
nieudanej rekompilacji.

**Powód.** Ten sam motyw budżetu godzin GPU co przy przepisaniu
laplasjanu na conv3d — `scope_bench_laplacian.py` miał opcję `--compile`
jako drugi krok, jeśli sam conv3d nie da ≥3×; to włącza tamten drugi
krok na stałe w ścieżce produkcyjnej zamiast zostawiać go opcjonalnym.

**Nie zweryfikowane na docelowym sprzęcie.** Jak przy conv3d: przyspieszenie
i poprawność (brak rozjazdu trajektorii z powodu innej kolejności
sumowania w skompilowanym grafie) trzeba potwierdzić na Kaggle (2×T4),
nie tylko wnioskować z tego, że kod się importuje.

---

## 2026-07-24 — `masked_laplacian` → conv3d w pipeline v2 (ZMIANA IMPLEMENTACYJNA, nie protokołu)

**To nie jest zmiana kryteriów ani obserwabli.** CRITERIA_v2.md §0–§7
niezmienione: dalej τ_border/diss, log-rank na KM, ta sama definicja
horyzontu i te same bramki ważności. Wpis tylko dlatego, że koszt
obliczeniowy jednego przebiegu jest częścią tego, co decyduje, czy dana
konfirmacja mieści się w budżecie sesji Kaggle (patrz RESUME.md) — nie
dlatego, że wynik naukowy się zmienia.

**Powód.** Sonda 2×T4/192³/40000 kroków ujawniła w tracebacku wąskie
gardło w `masked_laplacian` (`scope_topology.py`): 12 wywołań
`torch.roll` na krok (6 sąsiadów × 2 tensory — pole i maska domeny), ~24
tensory pełnowymiarowe na krok przy 192³. Zmierzony realny czas: 1010
s/przebieg (~16.8 min) na T4.

**Zmiana.** Nowy plik `scope_laplacian.py` implementuje ten sam operator
przez `F.conv3d` ze stałym kernelem 3×3×3 (środek=−6, sześciu sąsiadów=
+1) plus jednorazowo (per siatka, nie per krok) policzoną korektą
brzegową `(6 − deg)`, gdzie `deg` to liczba sąsiadów w domenie —
implementacja no-flux Neumanna równoważna maskowaniu w wersji
roll-based (wyprowadzenie w docstringu pliku). `scope_topology_v2.py`
przełączony na tę funkcję. **`scope_topology.py` i `scope_run.py` (v1,
zapis audytowy, `scope_run.py` bitowo identyczny z `scope_topology.py`)
NIE zostały dotknięte** — inwariant z wpisu 2026-07-23 (v1 zachowane bez
zmian) utrzymany.

**Kryterium przyjęcia, ustalone przed uruchomieniem testu:** smoke test
32³/400 kroków, max|Δ| < 1e-6 na obu polach (u, v) względem trajektorii
liczonej starą implementacją; przy niepowodzeniu zmiana nie jest
mergowana do ścieżki produkcyjnej. Implementacja i test:
`scope_test_laplacian_equivalence.py`.

**Wynik testu.** Uruchomiony lokalnie na CPU (ten sandbox nie ma GPU) —
max|Δu| = 2.68e-7, max|Δv| = 2.38e-7 (najgorsza z trzech topologii przy
(F,k)=(0.042, 0.062)) — **PASS**, margines > 3× wobec progu. Rozszerzony
niewiążący check do 4000 kroków pokazuje wzrost błędu w przybliżeniu
liniowy (≈2.4e-6), bez oznak rozjazdu wykładniczego, co jest przesłanką
(nie dowodem) stabilności na horyzontach produkcyjnych 45000–67000
kroków.

**Nie jest jeszcze uznane za w pełni zweryfikowane.** Ścieżka
zmiennoprzecinkowa cuDNN-conv3d na GPU różni się kolejnością sumowania od
zarówno CPU-conv3d, jak i roll-based — zgodność zmierzona na CPU jest
mocną przesłanką (ten sam operator algebraicznie), nie dowodem
równoważności na T4. Test musi zostać powtórzony na Kaggle przed pushem;
komenda w RESUME.md, sekcja „Aktualizacja 2026-07-24".

**Speedup nie zmierzony na docelowym sprzęcie.** Skrypt
`scope_bench_laplacian.py` gotowy (192³/2000 kroków, z opcją
`--compile` jako drugim krokiem, tylko jeśli sam conv3d nie da ≥3×). Na
CPU wynik wyszedł na niekorzyść conv3d (0.4×) — nieinformacyjne dla
kierunku na GPU, bo zysk ma wynikać ze zmniejszenia liczby uruchomień
kerneli i ruchu w pamięci na GPU (cuDNN), czego CPU nie odtwarza; liczba
wiążąca dopiero z Kaggle.

**Status pusha: WSTRZYMANY.** Zgodnie z instrukcją — miarę przyspieszenia
mierzy się przed pushem, a bramkę równoważności trzeba potwierdzić na
docelowym sprzęcie, nie tylko lokalnie.

---

## 2026-07-23 — v1 → v2

**Zmienione po obejrzeniu danych pilotażowych `results_x1` (96³) oraz
sond 288³, przed uruchomieniem zestawu konfirmacyjnego.**

To zdanie jest istotą tego wpisu. Obserwabla główna została wybrana po
zobaczeniu, która z nich różnicuje topologie — jest to wybór **post hoc**
i podlega wszystkim zastrzeżeniom garden of forking paths. Dlatego
przebiegi, na których zapadła ta decyzja, mają status **pilotażowych**, a
prawo do słowa „potwierdzone" przysługuje wyłącznie zestawowi
konfirmacyjnemu na świeżych ziarnach RNG.

### Co zostało zmienione i dlaczego

| element | v1 (§5 CLAUDE.md) | v2 | powód |
|---|---|---|---|
| obserwabla główna | κ(T) = K_border/K_inner na gzip | τ_border (czas pierwszego przejścia struktury do powłoki granicznej), na gęstości dyssypacji | κ ma dwie bezfizyczne drogi do 1 (podłoga gzip zależna od n; nasycenie). Stan końcowy jest bezpamięciowy: diss_inner zbiega do 1.64/1.65/1.66e-3 niezależnie od topologii. |
| test | odstęp > 2σ | log-rank (Mantel-Cox) na krzywych Kaplana-Meiera | (a) σ=0 w ramieniu martwym dawało nieskończoną „istotność"; (b) τ_border jest cenzorowane prawostronnie na wspólnym horyzoncie T, a Mann-Whitney na danych cenzorowanych jest formalnie niepoprawny |
| multiplicity | brak | korekta Holma na 3 pary × 2 rozmiary siatki | 6 porównań bez korekty |
| kategorie wyniku | 2 (potwierdzone / homogenizacja) | 3 (potwierdzone / negatywne / nierozstrzygnięte), rozłączne i operacyjne | brak trzeciej szuflady wymusza wciskanie szarych wyników do jednej z dwóch, zwykle przyjemniejszej |
| „negatywne" | brak istotności | **aktywnie pokazana równoważność**: przekrywające się pasma ufności KM na całej długości | brak dowodu różnicy to nie dowód braku różnicy |
| walidacja | pojedynczy zestaw | podział pilot / konfirmacja na świeżych ziarnach | pilot nie może sędziować we własnej sprawie |

### Etap pośredni, odrzucony

Mann-Whitney był w projekcie v2 z 2026-07-23 obserwablą testową
zastępującą odstęp 2σ. Odrzucony tego samego dnia po wskazaniu, że
cenzura prawostronna czyni go niepoprawnym. Pozostaje w kodzie
(`scope_survival.mannwhitney_crosscheck`) wyłącznie jako kontrola dla
przypadku bez cenzury, gdzie oba testy powinny się zgadzać.

### Wady, które wymusiły zmianę

Udokumentowane z danymi w [FINDINGS.md](FINDINGS.md): podłoga nagłówka
gzip rosnąca z n (0.704 → 0.939 → 0.980 przy 96³/192³/288³), artefakt
nasycenia, geometrycznie niewykonalne wyrównanie objętości zasiewu
`shell`, zasiew `distributed` wprost w region pomiarowy, oraz — już w
kodzie v2 — próg dzielenia postawiony na krawędzi szumu.

### Status plików

- `scope_topology.py`, `results_x1/` — v1, **zachowane bez zmian** jako
  zapis audytowy. `scope_run.py` zweryfikowany jako bitowo identyczny.
- `viab288_*`, `cmp_metrics/`, `scan_fk/`, `scan_topo/` — **pilotażowe**.
  Na nich zapadła decyzja o obserwabli. Nie służą do orzekania.
- zestaw konfirmacyjny — świeże ziarna, oceniany wyłącznie pod v2.

---

## 2026-07-23 — zamknięcie §6 (drabina skali) i dodanie §7 (horyzont)

§6 CRITERIA_v2 był otwarty od chwili zamrożenia reszty kryteriów.
Zamknięty tego samego dnia, przed uruchomieniem konfirmacji.

**Uzasadnienie jednym zdaniem:** konfundacja frakcji zasiewu z rozmiarem
siatki nie została złagodzona wyborem kompromisowego punktu, tylko
rozplątana dodatkowym ramieniem przy stałym n, ponieważ „przeżywa zmianę
n" bez takiego ramienia jest zdaniem z gwiazdką.

Postanowienia:

- **96³ wykluczone** regułą B5 (maksymalny promień zasiewu ≤ 0.8 ×
  promień `inner`). Powód nie frakcyjny, tylko kontaminacyjny: przy 11.46%
  kula centralna ma promień 0.485R wobec `inner` sięgającego 0.5R, więc
  zasiew `central` niemal *jest* regionem pomiarowym. Reguła wyznacza
  minimalne n dla danej frakcji (f ≤ 6.4%) i obowiązuje na przyszłość.
- **Drabina: trójkąt** (192³, 5.73%) — (192³, 3.82%) — (288³, 3.82%);
  pierwszy bok mierzy czysty efekt frakcji przy stałym n, drugi czysty
  efekt n przy stałej frakcji.
- **Sprostowanie:** wcześniejsze stwierdzenie „stała frakcja przez drabinę
  jest niemożliwa" było błędne. Prawdziwe wyłącznie przy sztywnej grubości
  3 wokseli; przy grubości ∝ n frakcja jest stała z definicji (2.0 woksela
  przy 192³).
- **n = 16** podstawowy, **n = 12** kontrolny, z regułą jednorazowej
  dolewki +4 ziaren zadeklarowaną przed startem.
- **§7 horyzont czasowy** dopisany i spisany **przed** odczytaniem wyników
  sondy 288³/60k — reguła plateau plus warunek rewizji kroków przy
  nadliniowym skalowaniu τ z n. Powód: ramię martwe musi pozostać
  odróżnialne od wolnego, a horyzont dobrany po obejrzeniu sondy zamieniłby
  jedno w drugie.

### Poprawka progu plateau (§7), tego samego dnia, przed użyciem reguły

Pierwsza redakcja §7 definiowała plateau jako „|d(diss_border)/dt| poniżej
**0.02 na jednostkę czasu**". Wartość 0.02 nie pochodziła z rozstrzygnięcia
ŁC (tam był „próg" bez liczby) — została wpisana przy redakcji bez
sprawdzenia skali zjawiska. Jest ~100× powyżej średniego tempa narastania:
diss_border rośnie od 0 do ~1.6e-3 przez ~5000 jednostek czasu wzorca,
czyli ~2e-4 na jednostkę. Reguła z tą liczbą uznawałaby za plateau ramię
dopiero startujące i zwracałaby horyzont zbyt krótki — czyli **produkowała
cenzurę tam, gdzie jest tylko powolność**, co jest dokładnie tym, przed
czym §7 ma chronić.

Zastąpiona definicją bezwymiarową: plateau = wejście i pozostanie w paśmie
±2% wokół wartości końcowej. Poprawka wprowadzona **zanim reguła została
zastosowana do jakichkolwiek danych**. Implementacja i testy jednostkowe:
`scope_horizon.py`.
