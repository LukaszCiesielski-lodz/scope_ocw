# CLAUDE.md — projekt SCOPE: eksperyment topologiczny

> Ten plik to handoff z rozmowy na claude.ai (2026-07-23). Wrzuć go do
> katalogu głównego repo — Claude Code przeczyta go automatycznie jako
> kontekst projektu. Maszyna obliczeniowa: GPU na vast.ai przez SSH.

## 1. Kontekst naukowy (skrót rozmowy)

**Punkt wyjścia.** Praca Ł. Ciesielskiego "Eksport złożoności w układach
sferycznych: model SCOPE i analogia troposferyczna" (04.2026). Model:
wskaźnik eksportu κ(t) = K_border(t)/K_inner(t) w symulacji Gray-Scotta
na domenie sferycznej vs kontrola kartezjańska. Wyniki oryginalne:
κ(T)=1.003 (sfera) vs 0.998 (kartezjan), sweep (F,k) — delty 0.02–0.03.

**Recenzja (główne zarzuty do naprawienia):**
1. **κ→1 to prawdopodobnie homogenizacja, nie eksport** — κ nigdy nie
   przekracza parytetu, tylko do niego dochodzi; skończona domena
   wypełniana wzorem da κ→1 niezależnie od geometrii. Test rozstrzygający:
   skalowanie rozmiaru domeny.
2. **Różnica geometrii (0.005) jest na poziomie szumu** — brak ensemble,
   brak słupków błędu, pojedyncze przebiegi. Ryzyko motte-and-bailey:
   teza o geometrii upada, a "protokół" jest niefalsyfikowalny.
3. **K_border/K_inner nigdy nie było zdefiniowane** — teraz jest (patrz §3).
4. **R²=0.947 użyte dwukrotnie** (rejestr astrofizyczny i "kalibracja") —
   to ta sama liczba, pozór korroboracji; wyciąć albo znaleźć niezależne proxy.
5. Ψ = 36πV²/A³ zdefiniowane, ale nieużyte — właściwy test tezy
   geometrycznej to sweep po Ψ (kula→elipsoida→sześcian→kształt gwiaździsty).

**Rozszerzenie hipotezy (kierunek obecny).** Intuicja autora: troposferę
Ziemi/loty kosmiczne, powierzchnie gwiazd/supernowe i promieniowanie
czarnych dziur łączy topologia złożoności ułożonej w sferach. Po dyskusji
zawężone do dwóch falsyfikowalnych pytań:
- (a) **Co decyduje o przepuszczalności sferycznej granicy dla struktury?**
  (Czarna dziura = kontrprzykład na osi przepuszczalności: promieniowanie
  Hawkinga jest termiczne = zero eksportu struktury. Oś: troposfera →
  fotosfera/szok SN → horyzont zdarzeń.)
- (b) **Czy topologia PRZESTRZENNA akumulacji złożoności przewiduje
  statystykę CZASOWĄ eksportu?** Rama: dynamika relaksacyjna / SOC
  (Bak). Przewidywanie: akumulacja rdzeniowa → długie τ, zrzut
  jednorazowy globalny (supernowa); akumulacja powłokowa → serie
  potęgowe (trzęsienia, rozbłyski); rozproszona z transportem →
  ciągły wyciek przez punktową singularyzację (kosmodrom na sferze).
- Docelowo: bezwymiarowe kryterium przebicia Π(t) (energia swobodna
  procesu organizującego / energia wiązania na jednostkę eksportowanej
  struktury); "moment ekspansji" = pierwsze przejście Π(t) przez Π_c.
  Rozróżniać złożoność od entropii (garb "complextropy" Carroll/Aaronson:
  złożoność niska→wysoka→niska, napędzana eksportem entropii, Prigogine).

## 2. Stan kodu

Plik: `scope_topology.py` (PyTorch, auto-detekcja CUDA; przetestowany
smoke-testem na CPU 28³/600 kroków — działa, sanity OK).

Eksperyment: 3 topologie zasiewu × ensemble, domena sferyczna (R=0.46n),
Gray-Scott z no-flux (masked Laplacian) na nieregularnym brzegu:
- `central` — kula w centrum
- `shell` — cienka powłoka na 0.75R
- `distributed` — losowe małe kule w obrębie 0.9R
- objętość zasiewu WYRÓWNANA między topologiami (~0.7% domeny) — różni
  się tylko rozkład przestrzenny.

Parametry domyślne: F=0.06, k=0.062, Du=0.16, Dv=0.08, dt=0.18
(zgodne z papierem SCOPE).

## 3. Definicja K (do sekcji metod papieru)

K(region) = len(gzip(kwantyzacja 8-bit pola v w regionie)) / n_wokseli.
κ(t) = K_border/K_inner; border = powłoka 0.85R–R, inner = kula ≤0.5R.
τ = czas pierwszego przejścia κ(t) ≥ 1 (rozdzielczość record_every·dt).
Pułapka: na siatkach <48³ narzut nagłówka gzip zawyża K jednorodnych
regionów — porównywać kształty krzywych i uporządkowania, nie wartości
bezwzględne między rozmiarami siatek.

## 4. Do zrobienia na GPU (kolejność)

```bash
pip install torch numpy matplotlib
# przebieg główny
python scope_topology.py --grid 96 --steps 20000 --n-runs 8 --outdir results_x1
# kontrola skali domeny (ROZSTRZYGAJĄCA dla zarzutu homogenizacji)
python scope_topology.py --grid 192 --steps 20000 --n-runs 8 --scale 2 --outdir results_x2
```
Szacunkowo: 96³ ≈ minuty/przebieg na RTX 3090/4090; 192³ ≈ 8× dłużej;
całość 1–2 h.

## 5. Kryteria decyzyjne (ustalone PRZED przebiegami — nie zmieniać po)

- **Teza topologiczna potwierdzona**: uporządkowanie κ(T) i/lub τ między
  topologiami spójne w ensemble (odstępy > 2σ) ORAZ przeżywa 96³→192³.
- **Homogenizacja / wynik negatywny**: κ(t) nakłada się między 96³ a 192³
  w czasie wzorca niezależnie od topologii → κ→1 to equilibracja;
  wynik negatywny też publikujemy, bez przebierania go za sukces.
- Smoke test (28³, niewiążący) dał uporządkowanie central > shell >
  distributed w κ(T), distributed nie przekroczył parytetu — kierunek
  zgodny z intuicją supernowej, ale to NIE jest wynik.

## 6. Następne kroki po eksperymencie topologicznym

1. Analiza pierwszego przejścia z results_x1/x2 (runs.json): rozkłady τ,
   test skalowania, wykładniki jeśli seria zdarzeń.
2. **Sweep po sferyczności Ψ** (kula→elipsoida→sześcian) przy stałych
   (F,k) i kontroli rozmiaru — właściwy test tezy geometrycznej z papieru.
3. Konstrukcja Π dla trzech fizyk (rakieta z troposfery / ejekta SN /
   Hawking) — analiza wymiarowa, sprawdzić czy próg może być wspólny.
4. Poprawki papieru wg §1 (zarzuty 1–5); rozważyć niezależne proxy
   złożoności zamiast podwójnego R²=0.947; assembly index lub koszt
   termodynamiczny jako alternatywne K stosowalne do strumienia Φ(t).

## 7. Konwencje pracy

- Język rozmowy: polski; kod i identyfikatory: angielski.
- Wyniki (runs.json/summary.json/png) commitować do repo — służą jako
  zapis audytowy; kryteria z §5 są zamrożone przed analizą.
- Styl naukowy projektu: rozdzielać wynik modelowy / kalibrację / analogię
  (jak w oryginalnym papierze — to jego najmocniejsza strona).
