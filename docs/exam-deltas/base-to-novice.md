# BASE → NOVICE: what to study

Internal note. Source: `data/questions.jsonl` (catalogue ra-2024), questions tagged
`novice` but not `base`.

- NOVICE pool: 235 questions. BASE pool: 77, all included in NOVICE.
- Delta: **158 questions**. About 110 technical, about 48 regulation.
- No new questions in section 1.3 (Circuits).

## Technical (~110)

### 1.1 Electricity basics (48, the largest block)

- Resistors in series and parallel: equivalent resistance, how voltage and current
  divide, which resistor has the largest voltage drop.
- Ohm's law and power, P = UI = U²/R = I²R. Typical: max current or voltage for a
  resistor or a 50 Ω dummy load; series resistor for a 9 V lamp on a higher supply.
- Kirchhoff's current law at a junction.
- Resistor colour codes (4 bands).
- Wire cross-section and length vs resistance. Semiconductors: Si, Ge, Se.
- λ = 300/f, both directions. Mains 50 Hz → 6000 km. Audio range 20 Hz–20 kHz.
- Peak = RMS × √2.
- Harmonics (integer multiples); square wave = fundamental + harmonics. Distortion factor.
- AM vs SSB: bandwidth 2×fmax for AM, fmax−fmin for SSB (6 / 2.7 kHz for 0.3–3 kHz audio).
  Sidebands, modulation index, reading oscilloscope traces.
- E and H fields are perpendicular.

### 1.2 Components (18)

- Capacitors: series raises voltage rating, parallel raises capacitance.
  Inductors in series/parallel.
- Batteries: series adds voltage, parallel adds Ah.
- Electrolytic and tantalum capacitors are polarised. Dielectric sets capacitance;
  core material sets inductance.
- Purpose of: transformer, filter, transistor, diode, LED, Zener.
  Diodes in series raise voltage rating; in parallel raise current rating.

### 1.6 Antennas (16)

- Lengths: λ/4 ground plane at 145 MHz ≈ 50 cm; λ/2 dipole with shortening factor.
- Polarisation of GP and Yagi. Yagi directors shorter than the reflector.
- ERP uses a λ/2 dipole reference, EIRP an isotropic one, so EIRP > ERP.
- Beamwidth, tuner/matchbox, twin-lead line, Pi vs T matching networks.
  End-fed λ/2 also resonates on harmonics.

### 1.9 + 2.8 Interference / EMC (12 + 3)

- Which filter goes where:
  - Low-pass at the TX to stop harmonics into TV.
  - High-pass at the TV/FM receiver or its antenna amplifier.
  - Band-pass for spurious emissions.
  - Mains filter on audio gear.
- Attenuator for overloaded receivers.
- Dummy load (50 Ω). Harmonic and image interference examples.
- Primary vs secondary services.

### 1.4 + 1.5 Transmitters and receivers (10)

- Bandwidth: CW narrowest, then SSB, then AM.
- Frequency drift barely matters in FM but shifts the audio in SSB.
- Direct-conversion vs superhet. Put the preamp at the antenna.

### 1.7 Propagation (7)

E and F layers, 1.8–30 MHz range, fading, 11-year sunspot cycle, SID/Dellinger,
ground-wave + sky-wave interaction.

### 1.8 Measurement (3)

DC range reads 0 on AC. Grid dip meter for resonance, SWR meter for antenna system.

### 1.10 + 1.11 Safety and lightning (6)

- Class II (double-insulated) gear may use a 2-pin plug.
- Protective earth is green-yellow and goes to the case; neutral never does.
- Lightning conductor: ≥ 6 mm copper; Al or steel OK with the right cross-section.

## Regulation (~48, mostly open-answer recall)

### 3.4 National law (15)

- Licence classes and standards: HAREC = T/R 61-01/02, NOVICE = ECC REC (05)06.
- Power limits: BASE 25 W, NOVICE 100 W PEP, HAREC reduced in year 1 then 1000 W.
  Above 1000 W only by request.
- Use abroad; CEPT site for the country list.
- Environment administration permit; 3 transmitter classes.
- Group stations (procedure, not usable abroad). Who can apply for a beacon/repeater.

### 3.1–3.3 + 2.5.1 International bodies (~11)

- ITU-R mission. IARU: iaru.org, 3 regions, Luxembourg in Region 1, its purpose.
- CEPT documents and activities.
- ITU RR definitions: amateur and amateur-satellite service and station.
  RR Article 5 = frequency allocation.

### 2.3–2.7 Operating (~8)

- LX callsign structure; digit meaning (0 = automatic stations).
- Suffixes /M /P /MM. Group-station callsign.
- Primary bands below 30 MHz.
- Secrecy of communications. Logbook contents. State emergency powers (Art. 4).

## Priority

1. Electricity calculations (Ohm/power, series/parallel, λ, RMS/peak, bandwidth):
   about a third of the delta and needs practice.
2. Filter placement for interference; antenna lengths.
3. Regulation last: memorise.
