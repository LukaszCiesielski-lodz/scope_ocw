# Kryteria decyzyjne v2 — ZAMROŻONE 2026-07-23

Ratyfikowane przez ŁC. Zastępują §5 CLAUDE.md. Historia zmiany i jawne
oznaczenie tego, co jest decyzją badacza, a co wynikiem:
[CHANGELOG.md](CHANGELOG.md). Uzasadnienie z danymi:
[FINDINGS.md](FINDINGS.md).

> **Ostrzeżenie proceduralne.** Obserwabla główna została wybrana po
> obejrzeniu danych pilotażowych — jest to wybór **post hoc**. Przebiegi
> pilotażowe (`results_x1`, `viab288_*`, `cmp_metrics`, `scan_*`) mają
> status eksploracyjnych i **nie służą do orzekania**. Prawo do słowa
> „potwierdzone" ma wyłącznie zestaw konfirmacyjny na świeżych ziarnach
> RNG, oceniany wyłącznie pod niniejszymi kryteriami.

## 0. Podział pilot / konfirmacja

- **Pilot** — wszystko policzone do 2026-07-23 włącznie. Służy wyłącznie
  do wyboru obserwabli, punktu pracy i długości przebiegu. Raportowany
  jako eksploracyjny; wnioski z niego mają status „sugeruje".
- **Konfirmacja** — świeże ziarna RNG (`--seed-base 2000`, rozłączne z
  pilotem), te same parametry, ta sama procedura. Wyłącznie ten zestaw
  orzeka.

## 1. Obserwabla główna — jedna

**τ_border** — czas pierwszego przejścia gęstości dyssypacji w powłoce
granicznej przez próg równy 10% jej wartości końcowej w danym przebiegu.

Próg samokalibrujący, nie bezwzględny: „struktura dotarła do granicy" nie
ma definicji bez progu, bo wykładniczy ogon dociera natychmiast
(zmierzone: diss_border = 3.1e-9 przy t=90 wobec stanu ustalonego
1.6e-3). Skalowanie wartością końcową każdego przebiegu unika
importowania stałej skali, która nie przenosi się między (F,k) ani
rozmiarami siatki. W pilocie uporządkowanie było **stabilne dla progów
1%–50%**, co uzasadnia wybór 10% jako środka tego pasma.

Runy bez przejścia do horyzontu T są **cenzorowane prawostronnie**, nie
usuwane.

### Cechy drugorzędne — opisowe, nie testowane

Zadeklarowane jawnie, żeby multiplicity nie zjadła istotności. Nie
podlegają testom i nie mogą być podstawą wniosku:
wysokość piku diss_ratio, czas do piku, całka nad parytetem,
diss_ratio(T), κ_gzip(T), κ_exc(T), fill(T).

κ_gzip raportowane wyłącznie dla ciągłości z papierem.

## 2. Bramki ważności (przed jakąkolwiek analizą)

Ramię, które ich nie przechodzi, jest raportowane jako nieważne, nie jako
wynik.

- **B1 Żywotność.** `diss_inner(T) > DISS_FLOOR` (=1e-8).
- **B2 Nienasycenie.** `fill(T) < 0.9`.
- **B3 Wyrównanie zasiewu.** `|match_ratio − 1| < 0.01` dla wszystkich trzech topologii.
- **B4 Czystość regionu pomiarowego.** 0 wokseli zasiewu w powłoce `border` w t=0.

## 3. Test

**Log-rank (Mantel-Cox)** na krzywych **Kaplana-Meiera**, parami między
topologiami. Wybrany, bo τ_border jest cenzorowane na wspólnym horyzoncie
— Mann-Whitney nie ma rangi dla braku zdarzenia i jest tu formalnie
niepoprawny. MW zachowany wyłącznie jako kontrola w przypadku zerowej
cenzury, gdzie oba testy powinny się zgadzać.

**Korekta Holma** na 3 pary × 2 rozmiary siatki = 6 porównań, α = 0.05.

Krzywe KM są też obowiązkową ilustracją do papieru: ramię martwe lub
nieeksportujące widać jako plateau, zamiast znikać z wykresu — tak właśnie
ukryło się wygasłe ramię `shell` w v1.

**Liczebność:** n = 12–16 na ramię. Sanity check wykazał, że przy 4
zdarzeniach i 4 cenzurowanych na ramię log-rank daje p = 0.62 mimo realnej
różnicy — przy cenzurze n = 8 nie ma mocy.

## 4. Miarka wrażliwości (F,k)

Przed testem mierzony rozrzut τ_border wywołany perturbacją samych
parametrów (F,k) o ±2% przy ustalonej topologii, na tej samej siatce i
liczbie kroków. **Różnica między topologiami liczy się jako realna tylko
powyżej tego rozrzutu.** Dla κ rozrzut parametryczny wynosił ~0.15 przy
raportowanej w papierze różnicy geometrii 0.005 — 30× mniej.

## 5. Kategorie wyniku — rozłączne

- **POTWIERDZONE** — log-rank istotny po korekcie Holma na rozmiarze
  podstawowym **ORAZ** ten sam kierunek uporządkowania na rozmiarze
  kontrolnym (istotność tam pożądana, kierunek konieczny) **ORAZ** efekt
  powyżej miarki wrażliwości.
- **NEGATYWNE** — brak istotności na obu rozmiarach **ORAZ** pasma ufności
  KM przekrywają się na całej wspólnej długości dla wszystkich par. Czyli
  **aktywnie pokazana równoważność**, nie sam brak dowodu różnicy.
- **NIEROZSTRZYGNIĘTE** — wszystko pomiędzy. W szczególności:
  - istotność, która nie replikuje kierunku między rozmiarami (scenariusz
    najbardziej prawdopodobny),
  - > 25% przebiegów w ramieniu bez dynamiki lub niestabilnych numerycznie,
  - p po korekcie w paśmie 0.05–0.15,
  - efekt poniżej miarki wrażliwości.

Wynik negatywny publikujemy, bez przebierania go za sukces (§5 CLAUDE.md,
utrzymane).

## 6. Drabina skali — ZAMKNIĘTE 2026-07-23

Rozstrzygnięcie ŁC. Konfundacja frakcji zasiewu z n nie zostaje
„złagodzona" wyborem kompromisowego punktu, tylko **rozplątana dodatkowym
ramieniem**.

### 6.1 Reguła rozdziału zasiewu i regionu pomiarowego (B5)

**Maksymalny promień zasiewu ≤ 0.8 × promień regionu `inner`** (= 0.4R).

Powód twardszy niż sama grubość frakcji: przy 96³ frakcja wymuszona przez
powłokę 3-wokselową (11.46%) daje kulę centralną o promieniu 0.485R, przy
regionie `inner` sięgającym 0.5R. Zasiew `central` **jest wtedy niemal
regionem pomiarowym** — obserwabla w t=0 mierzy kompresowalność samego
zasiewu, a ramię `central` startuje z innym znaczeniem obserwabli niż dwa
pozostałe. To ta sama klasa błędu co Wada 4 (`distributed` w `border`),
tyle że po stronie rdzenia.

Reguła wyznacza minimalne n dla danej frakcji: promień kuli centralnej to
R·f^(1/3), więc warunek daje **f ≤ 6.4%**. Stąd 96³ (11.46%) odpada
automatycznie, 192³ (5.73%) przechodzi, 288³ (3.82%) przechodzi z zapasem.

### 6.2 Co fizycznie znaczy zmiana n

Przy stałym dx i stałych (D,F,k) długość fali wzorca jest stała w
wokselach — większa siatka to **większa domena fizyczna, nie lepsza
rozdzielczość**. Stąd dwie rozłączne interpretacje kontroli skali:

- **A, stały zasiew fizyczny**: ta sama warstwa 3-wokselowa w większym
  świecie; frakcja spada ∝ 1/n. To nie artefakt, tylko treść testu —
  struktura ma dalej do granicy. Jeśli κ→1 jest lokalną equilibracją, τ
  nie będzie skalować z n; jeśli to realny transport, τ_border rośnie
  ∝ odległości (fronty reakcji-dyfuzji biegną ze stałą prędkością, co jest
  spójne z krokami ∝ n). **Skalowanie τ z n jest wtedy samo w sobie
  obserwablą rozstrzygającą homogenizację.**
- **B, samopodobieństwo**: wszystko skaluje się z n, w tym grubość
  powłoki. Grubość ∝ n daje **dokładnie stałą frakcję** (3 × 192/288 = 2.0
  woksela przy 192³), bez patologii 1-wokselowej. Pytanie jest wtedy
  czysto o geometrię rozkładu przy stałej gęstości zasiewu.

### 6.3 Przyjęta drabina — trójkąt rozplątujący

| oznaczenie | siatka | grubość powłoki | frakcja | rola |
|---|---|---|---|---|
| **A** | 192³ | 3 woksele | 5.73% | podstawowy |
| **B** | 192³ | 2 woksele | 3.82% | ramię rozplątujące |
| **C** | 288³ | 3 woksele | 3.82% | kontrolny |

- bok **A→B**: czysty efekt frakcji przy stałym n
- bok **B→C**: czysty efekt n przy stałej frakcji

Ramię B ogranicza się do topologii najczulszej na frakcję (`shell`),
zgodnie z zasadą ekonomii: +8–12 przebiegów, ~kwadrans GPU. Warunek
wstępny: powłoka 2-wokselowa musi przejść bramkę żywotności B1 przy
(0.042, 0.062) — do sprawdzenia przed konfirmacją.

Bez ramienia B zdanie „przeżywa zmianę n" byłoby zdaniem z gwiazdką.

### 6.4 Liczebności i reguła dolewki

- podstawowy (A): **n = 16** na ramię
- kontrolny (C): **n = 12** na ramię — dopuszczalne, bo szczebel
  kontrolny wymaga kierunku, nie istotności
- **Reguła dolewki, zadeklarowana przed startem:** jeśli kierunek na
  szczeblu kontrolnym jest niejednoznaczny (mediany w kolejności
  niezgodnej z podstawowym, a przedziały się przekrywają), dokłada się
  **jednorazowo +4 ziarna** i ocenia ponownie. **Koniec — bez dalszych
  iteracji.** Szczebel kontrolny nie bramkuje p-wartością, więc
  sekwencyjność nie psuje testu konfirmacyjnego na szczeblu głównym;
  reguła spisana z góry odróżnia dolewkę od doliczania aż wyjdzie.

## 7. Horyzont czasowy — reguła spisana PRZED odczytem sondy

Zapisane 2026-07-23, **przed** odczytaniem wyników sondy 288³/60k.
Powód: cenzura gryzie się z log-rankiem w jednym miejscu — ramię
**martwe** musi być odróżnialne od **wolnego**. Horyzont ustalony na oko
po zobaczeniu sondy zamieniłby jedno w drugie.

- **Plateau** ramienia, definicja względna (nie pochodna względem progu
  bezwzględnego): najwcześniejszy czas t*, od którego trajektoria
  `diss_border` pozostaje **w paśmie ±2% wokół swojej wartości końcowej**
  do końca przebiegu. Plateau musi obowiązywać przez co najmniej ostatnie
  20% przebiegu.
- **Horyzont T = 2 × t\* najwolniejszego ramienia sondy.** Jeśli
  którekolwiek ramię nie wchodzi w pasmo, plateau nie istnieje — horyzont
  jest nieznany-ale-większy, sondę **powtarza się dłużej, a nie
  reinterpretuje**.

  *Poprawka wartości progu, 2026-07-23, przed użyciem reguły na
  jakichkolwiek danych:* pierwsza redakcja mówiła „|d(diss_border)/dt|
  poniżej 0.02 na jednostkę czasu". Liczba 0.02 została wpisana bez
  sprawdzenia skali i jest ~100× powyżej średniego tempa narastania
  (diss_border rośnie od 0 do ~1.6e-3 przez ~5000 jednostek, czyli ~2e-4
  na jednostkę) — uznawałaby za plateau ramię dopiero startujące.
  Zastąpiona sformułowaniem bezwymiarowym powyżej. Implementacja:
  `scope_horizon.py`.
- **Warunek rewizji kroków:** jeśli τ_border skaluje z n **szybciej niż
  liniowo** (transport nie jest czysto frontowy), założenie kroki ∝ n jest
  nieważne i liczbę kroków rewiduje się w górę zgodnie ze zmierzonym
  wykładnikiem. To warunek, nie decyzja po fakcie.
