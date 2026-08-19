# SCOPE — mapa literatury do preprintu

Sonda Firecrawl przeprowadzona 2026-08-17. Trzy searche: (1) first-passage
times reaction-diffusion spherical, (2) Gray-Scott spherical domain
dissipation, (3) Falasco Rao Esposito information thermodynamics Turing
patterns.

## Trzy obowiązkowe cytowania

### 1. Falasco, Rao, Esposito (2018) — formalna rama termodynamiczna

Cytacja: G. Falasco, R. Rao, M. Esposito, "Information Thermodynamics of
Turing Patterns", Phys. Rev. Lett. 121, 108301 (2018). arXiv:1803.05378.

Co robią: rigorous thermodynamic description of RDS out of equilibrium.
Total entropy production rate Σ̇ = Σ̇_dff + Σ̇_rct (diffusion + reaction
parts). Klasyfikują pattern formation jako thermodynamic phase transition.
Analiza analityczna na 1D Brusselator.

Rola w preprincie SCOPE:
- Introduction: cytowana jako formalna rama termodynamiczna, w której SCOPE
  żyje operacyjnie
- Methods: wprost powiedzieć, że diss_border operacyjnie mierzy Σ̇_dff na
  powłoce r∈[0.85R, R], a diss_inner analog Σ̇_rct we wnętrzu
- Discussion: kalibracja diss_border/inner wobec formalnego free energy G
  z FRE jest przedmiotem przyszłej pracy

Czego NIE robią (twoja luka): 1D Brusselator (nie 3D Gray-Scott),
stacjonarna analiza (nie first-passage), jeden typ zasiewu (nie różne
topologie), brak sferycznej geometrii/granicy.

### 2. Liang, Jiang, Liu, Wang, Zhang (2024) — thermodynamically-consistent Gray-Scott

Cytacja: J. Liang, N. Jiang, C. Liu, Y. Wang, T. Zhang, "On pattern
formation in the thermodynamically-consistent variational Gray-Scott
model", arXiv:2409.04663 (2024).

Co robią: rozszerzenie klasycznego GS o 4-species variational model
(dodatkowe Y, P) — czyni go termodynamicznie zamkniętym. Klasyczny GS jest
podsystemem w granicy ε→0. Analiza pattern persistence time vs ε.
1D domena, no-flux boundary.

Rola w preprincie SCOPE:
- Introduction: cytowana jako niedawna praca łącząca Gray-Scotta z
  termodynamiką; uczciwie odróżnić — oni zamykają model termodynamicznie
  na 1D, my mierzymy transport topologiczny w 3D sferycznym
- Discussion: wariacyjna formulacja Liang et al. może być formalnym
  podłożem dla przyszłej wersji SCOPE z jawnym free energy

Czego NIE robią: first-passage times (mają pattern persistence, inna
wielkość), topologii zasiewu jako parametru, geometrii sferycznej,
eksportu vs wnętrze.

### 3. Serna, Muñuzuri, Barragán (2017) — rozłączność morfologii i termodynamiki

Cytacja: H. Serna, A. P. Muñuzuri, D. Barragán, Phys. Chem. Chem. Phys.
19, 14401 (2017). Cytowana przez FRE 2018.

Co robią: pokazują, że różne wzorce mogą mieć tę samą entropię względną —
morfologia i termodynamika mogą być rozłączne.

Rola w preprincie SCOPE:
- Introduction: cytowana jako punkt kontrastu — SCOPE de facto testuje
  przeciwną hipotezę w reżimie transjentu: topologia zasiewu przewiduje
  statystykę czasową transportu, czyli morfologia MA implikacje
  termodynamiczne (przynajmniej w kinetyce eksportu, nie w stacjonarnym
  free energy)

## Klasa first-passage w spherical geometry — kontekst metodologiczny

Klasa aktywna 2020-2025 (Grebenkov, Krapivsky, Bressloff i in.). Wszystkie
prace dotyczą czystej dyfuzji Browna cząstek w spherical/shell domains
(mean first-passage time, narrow escape, absorbing/reflecting patches).
Nikt nie zastosował tego do transportu struktury w reaction-diffusion.

Kluczowe prace do zacytowania w Methods jako metodologicznych przodków:
- Grebenkov, "Diffusion toward non-overlapping partially reactive
  spherical traps", J. Phys. A (2020), arXiv:2005.13279
- Grebenkov, "First-passage times to anisotropic partially reactive
  targets", J. Phys. A (2022), arXiv:2203.10898
- "Narrow escape problem in two-shell spherical domains", PMID:34781502
- Prace o stochastic resetting w sferach (arXiv:2109.11101) — pokazują,
  że klasa jest żywa

Rola: metodologiczny przodek, nie konkurencja. SCOPE przenosi tę
metodologię z pojedynczych cząstek na transport zorganizowanej struktury
w reakcji-dyfuzji.

## Klasyczni przodkowie (bez potrzeby weryfikacji przez sondę)

- Prigogine, Nicolis (1977) — struktury dyssypatywne jako klasa układów,
  w której SCOPE żyje
- Bak, Tang, Wiesenfeld (1987) — SOC + first-passage lifetime methodology
- England (2013, 2015) — dissipation-driven adaptive organization;
  jakościowa spójność uporządkowania distributed < shell < central z
  dryfem ku wyższej dyssypacji
- Pearson (1993), Science 261, 189 — klasyczny Gray-Scott, cytacja
  obowiązkowa w Methods dla modelu

## Luka, którą SCOPE wypełnia (jedno zdanie do Introduction)

"Chociaż rigoryczne ramy termodynamiczne dla systemów reakcji-dyfuzji
istnieją (Falasco et al. 2018) i termodynamicznie zamknięte rozszerzenia
Gray-Scotta zostały niedawno zaproponowane (Liang et al. 2024), obie
prace są ograniczone do jednowymiarowych domen z jednorodnym zasiewem.
Metodologia first-passage w geometrii sferycznej jest dobrze rozwinięta
dla dyfuzji Browna (Grebenkov 2020-2025), ale nie została zastosowana do
transportu struktury w systemach reakcji-dyfuzji. SCOPE wypełnia obie
luki: mierzy first-passage times struktury do granicy sferycznej w 3D
Gray-Scotcie, z topologią zasiewu jako parametrem kontrolnym."

## Wstępny plan struktury Introduction (do napisania później)

1. Kontekst Prigogine — struktury dyssypatywne, dS = d_eS + d_iS
2. Falasco-Rao-Esposito — rigorous EPR decomposition Σ̇ = Σ̇_dff + Σ̇_rct
3. BTW — first-passage lifetime methodology z SOC
4. Luka: brak analizy topologii zasiewu jako parametru kontrolnego w 3D
   sferycznym Gray-Scott
5. Wkład SCOPE: mierzalny, ograniczony, uczciwie z granicami (margines
   shell-distributed 1.57× nad rozrzutem parametrycznym)
