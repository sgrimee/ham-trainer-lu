# NOVICE → HAREC: what to study

Internal note. Source: `data/questions.jsonl` (catalogue ra-2024), questions tagged
`harec` only.

- HAREC pool: 509 questions. NOVICE pool: 235, all included in HAREC.
- Delta: **274 questions**, all technical (sections 1.x). **No new regulation.**
- Much more calculation, plus reading schematics, block diagrams and graphs.

| Section | New questions |
|---|---|
| 1.3 Circuits | 82 |
| 1.1 Electricity / radio theory | 39 |
| 1.2 Components | 36 |
| 1.4 Receivers | 36 |
| 1.6 Antennas and feeders | 35 |
| 1.5 Transmitters | 21 |
| 1.7 Propagation | 13 |
| 1.8 Measurement | 7 |
| 1.9 Interference | 4 |
| 1.10 Safety | 1 |

## 1.3 Circuits (82, the largest block, entirely new)

- **RC timing:** τ = RC; after 1τ discharge is at 37 %. Voltage divider charging a capacitor.
- **Reactance:** XC = 1/(2πfC), XL = 2πfL, both directions (find f, L or C).
  Frequency where XC = R. Capacitor current at mains frequency.
- **Impedance:** series R + X, Z = √(R² + X²).
- **Filters:** identify low/high-pass and band-pass from schematic and curve;
  RC cutoff f = 1/(2πRC).
- **Resonance:** f0 = 1/(2π√LC). Halving f0 needs 4× L or C. Series vs parallel
  resonance curves. XL = XC at resonance.
- **Q factor:** Q = XL/R, Q = f0/bandwidth.
- **Rectifiers:** bridge (Graetz), spotting a wrong diode, peak voltage = Ueff × √2,
  voltage doubler, diode reverse-voltage rating, C-L-C smoothing.
- **Diodes:** forward drop 0.7 V, LED series resistor, power in a diode,
  back-to-back diodes (protection/limiter).
- **Zener regulators:** min load resistance, Zener current, stacked Zeners, clipping.
- **Transistors:** CE / CB / CC configurations (CC = highest input impedance,
  CE = highest gain), β = IC/IB, Darlington gain, operating point, emitter-follower output.
- **Amplifiers / oscillators:** negative feedback stops parasitic oscillation;
  oscillation needs in-phase feedback. Crystal most stable; crystal equivalent circuit;
  pulling a crystal. VCO, PLL (divider in the loop), crystal vs PLL phase noise.
- **Demodulators:** product detector (SSB), envelope detector (AM), FM discriminator,
  chosen from schematics.
- **Misc.:** frequency tolerance in ppm, Wheatstone bridge balance, resistor networks.

## 1.1 Electricity / radio theory (39)

- **dB everywhere:** power and voltage ratios, dBm (10 W = 40 dBm, 46 dBm ≈ 40 W),
  chained gains/losses, S-units (1 S = 6 dB) and field strength vs distance (1/d).
- ERP from TX power, cable loss and antenna gain. Field strength from ERP:
  E ≈ 7√P / d.
- Source internal resistance (voltage source low, current source high), Uq and Ri,
  voltage drop on supply leads.
- RF power in matched lines: I = √(P/Z).
- FM modulation index = deviation / audio frequency. CW bandwidth vs WPM.
  RTTY uses FSK/AFSK.
- PEP from peak voltage. PA efficiency (P_out / P_in).
- Phase shift graphs (180°), reading RMS and frequency from an oscilloscope trace.
- Harmonic attenuation in dB → absolute power.

## 1.2 Components (36)

- Phase: capacitor current leads voltage 90°, inductor current lags 90°.
- Air capacitor vs plate spacing; inductance ∝ turns².
- **Transformers:** U ratio = turns ratio, current inversely; impedance ratio = turns²;
  laminated core reduces eddy currents. Turn counts and currents.
- **PA efficiency** from anode loss / output / input; anode voltage × current.
- **Logic gates** from truth tables: AND, OR, NAND, NOR, NOT.
- **Symbols:** NPN, PNP, N/P-channel FET, thyristor; silicon diode curve; varicap use.
- FET has the highest input impedance. Lead-acid Ri rises with age.
  Temperature coefficient. Piezo effect.

## 1.4 Receivers (36)

- **Superhet:** image frequency = f ± 2·IF; high first IF pushes image away;
  double conversion (block diagrams, missing blocks). LO / IF / image calculations.
- **Controls:** AGC, BFO, limiter, noise blanker, RIT, IF shift, notch, squelch,
  audio bandwidth limit.
- **Performance:** noise factor/figure, SINAD and S/N sensitivity specs,
  adjacent-channel rejection, selectivity (shape factor −6/−60 dB),
  the RF preamp sets noise figure.
- **Intermod / cross-mod:** 3rd-order products 2f1−f2 and 2f2−f1;
  test with an attenuator to recognise intermod.
- **SDR:** sampling > 2 × max frequency (Nyquist); anti-alias low-pass before ADC.
- Calibration accuracy (ppm), SSB audio shift with tuning error.

## 1.6 Antennas and feeders (35)

- Impedances: λ/2 dipole ≈ 75 Ω, folded dipole ≈ 4× (~240–300 Ω).
- Current vs voltage feed (low vs high impedance); voltage maximum at dipole ends.
- Shorten electrically: series C. Lengthen: series L.
- Dipole length with velocity factor (e.g. 10.125 MHz → 14.07 m).
- Stacking gain (4 × 8 dB Yagis → 14 dB), front/back ratio, radiation patterns,
  ERP with antenna gain.
- Antennas by band (W3DZZ not for VHF/UHF, dish not for HF).
- **Feeders:** coax Z depends on diameter ratio and not length; waves slower than c;
  cable loss in dB; SWR from forward/reflected power; λ/4 transformer
  Z = √(Z1·Z2); coax stub notch length; balun; transformer ratio = √(Z1/Z2);
  delta match not for coax.

## 1.5 Transmitters (21)

- Block diagrams: SSB TX, multiplier TX, transverter, ring modulator.
- Frequency multiplier (non-linear), buffer, ALC, neutralisation.
- AM: at 100 % modulation each sideband = 25 % of carrier power.
- Bandwidth ranking (RTTY 45 Bd narrowest), shaped CW keying.
- FM index; SSB overmodulation (splatter); speech processor raises average power;
  3rd-order IMD in dBm.
- **Amplifier classes:** A = highest bias current; C = best efficiency, lowest bias,
  fine for FM.
- Max power transfer needs matched impedances.

## 1.7 Propagation (13)

- Sporadic-E short skip, ground wave, aurora (VHF).
- MUF (independent of power) vs LUF (can be lowered with more power).
- Radiation angle: high (> 30°) for short range, low (5–15°) for DX.
- Scatter types, temperature inversion (tropo) on 2 m, bands unsuited to meteor scatter.
- Skin effect.

## 1.8 Measurement (7)

AM carrier + sideband → PEP; meter shunt calculation; reading spectrum and envelope
displays (FM, AM modulation index); correct V/I measurement circuit; SWR setup.

## 1.9 + 1.10 Interference and safety (5)

Audio rectification in neighbour's gear, splatter fixes (mic gain, ALC),
vehicle supply filtering, spark suppression, RCD is not absolute protection.

## Priority

1. **1.3 Circuits**: reactance, resonance, Q, rectifiers, Zener, transistors.
   30 % of the delta and calculation-heavy.
2. **dB fluency** (1.1, 1.6, 1.4): dBm, gains, cable loss, S-units, ERP.
3. **Receiver architecture**: superhet/image/IF math, intermod, controls.
4. **Transformers and feeders**: turns/impedance ratios, λ/4 transformer, SWR.
5. Transmitter blocks, amplifier classes, propagation, symbols and logic gates: mostly recall.
