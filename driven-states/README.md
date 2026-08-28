# Driven States Registry

An open, openly graded record of material states that exist **only while a drive is running** —
light-induced phases and Floquet-engineered bands. They are not eigenstates of the undriven
Hamiltonian, which is why no equilibrium data model can represent them, and why no such
collection existed before.

A prior-art search on 20 August 2026 found **no template at all** for this class of state:
not in Materials Project, AFLOW, OQMD, NOMAD or OPTIMADE, not in the NeXus application
definitions of the ultrafast facilities, not in the Floquet computation codes. The field
*evidence level* has no precedent in any materials schema either.

## Status, 20 August 2026

**82 driven states across 58 host materials**, from six fully searched domains: photoinduced
insulator–metal and Mott transitions, light-induced superconductivity, Floquet engineering,
hidden phases and charge density waves, driven ferroelectricity and magnetism, photoinduced
topology.

| Metric | Distribution |
|---|---|
| Evidence | 11 established · 13 reproduced · 49 single group · 9 contested |
| Stability | 44 driven · 16 metastable · 12 driven-to-metastable |
| Mechanism | 31 electronic · 16 mixed · 14 lattice/strain · 5 thermal · 4 unresolved · 2 field tunnelling |
| Lifetime | 1e-13 s to 1e7 s — **20 orders of magnitude** |
| Equilibrium equivalent | 50 no · 9 partial · 1 yes |

The distribution is itself a result: **49 of 82 states come from a single group.** That is the
central weakness of the field, and no review article makes it as visible as a table that counts
it.

## What the registry does that reviews do not

Null results and controls sit alongside positive findings, with equal weight:

- **LBCO x = 0.125** — no photo-superconductor under near-infrared pumping
- **LSCO x = 0.14** — artifact warning about the two-layer reconstruction on which nearly all
  positive cuprate findings rest
- **Bi2212** — the most heavily studied cuprate, never a defensible signature
- **KTaO₃** — the same experimental signature, traced to defect physics rather than
  ferroelectricity
- **κ-Cl and κ-NCS** — the effect appears only in κ-Br, not across the organic family
- **Sr₂IrO₄** — the measurement refutes the material's own Mott classification
- **FeRh** — kept as a calibration point: a thermal shortcut to a phase that is stable anyway.
  Anyone reporting a new case should be able to show it is not an FeRh.

## Two entry types

`../rpt/entries/` holds full entries with a coupling graph, actuators and an evaluator.
`registry/` holds light entries: material, equilibrium context, driven states with sources —
**without** a coupling graph. The separation is deliberate. For most materials no defensible
coupling data exists, and inventing a graph just to satisfy the schema would be data
fabrication. The interface hides the graph and propagation tabs for registry entries and says
so.

## What the prototype can do

- **Registry** filtered by evidence level, drive type, stability and full text
- **Drive parameters** per state: photon energy, wavelength, fluence, pulse duration,
  polarization, threshold, lifetime, switching time
- **Evidence grading** in four levels, colour-coded, each with a written justification —
  `contested` is a permitted and important value
- **Coupling graph** of the host material as SVG: actuators, degrees of freedom, observables;
  edge weight by confidence, dashed for qualitative edges
- **Propagation** in the browser: set actuator values, inspect path, latency, energy cost and
  triggered transitions. The evaluator is a complete port of `rpt_eval.py` to JavaScript
- **Overview** with a scatter of all states — lifetime against drive photon energy, both axes
  logarithmic — and a sortable table

## Build

```bash
python3 build_site.py     # reads ../rpt/entries/*.json and registry/*.json -> index.html
```

`index.html` is fully self-contained: all data inline, no CDN, no network dependency. A double
click is enough; no server required.

## Verification

The JavaScript evaluator is checked against the Python reference and returns identical values:

| Test case | Python | JavaScript |
|---|---|---|
| VO₂ thermal, critical path | 0.002 s | 0.002 s |
| VO₂ optical, critical path | 3.0e-13 s | 3.0e-13 s |
| Bi₂Se₃ Dirac gap at 0.4 mJ/cm² | 0.052 eV | 0.052 eV |
| YBCO Tc at δ = 0.3 | 60 K | 60 K |

The measured value for the Bi₂Se₃ gap is 53 ± 4 meV.

`python3 ../rpt/test_rpt.py` runs 29 tests covering both schemas, the relation algebra,
propagation, control loops and the registry: every source must carry a DOI or arXiv identifier,
every state must carry a caveat of substantial length, and preprint-only entries must stay
`pending`.

## Language

Everything in this project is English — data, identifiers, code comments, CLI output,
documentation. The registry is meant to be used and cited by researchers worldwide; German
identifiers and caveats inside an English interface would exclude exactly that audience.

## Open work

1. **Maintain the data.** Six domains are covered. Adjacent fields remain open: driven states in
   cold atoms (deliberately excluded, not a solid), excitonic insulators such as Ta₂NiSe₅,
   moiré systems, and 2026 preprints without a journal version.
2. **Repository structure.** Contribution guide, JSON-schema validation as a GitHub action,
   issue template for new entries, Zenodo deposition for a citable DOI.
3. **Package.** `rpt_eval.py` as a pip-installable package with a CLI.
4. **Visibility.** A short paper describing schema and registry. Without a citable reference the
   community adopts nothing.

## Limits of this version

- Two entries stay `pending` because they rest on preprints without a journal version
  (SnS, bismuth). A test enforces this.
- Microstructure — pinning, grain boundaries, defects — cannot be represented, though it
  belongs physically. See `gaps` in `nb.json`.
- Fabrication parameters and runtime parameters are not separated. A field
  `actuation_stage: fabrication | runtime` belongs in v0.2. See `c.json`.
- Interfaces and heterostructures need their own entry type. See `gan.json`.

## Patent situation

The prior-art gate of 20 August 2026 found **US 11 138 772 B2**: a materials-property coupling
graph with a relation formula and confidence per edge, confidence as edge weight, and path
search. The coupling graph as such is therefore anticipated. What remained free: actuators as a
node class, latency and energy cost per edge, the evaluation rule (energy sum plus critical
path), the feedback binding — and, with no template found at all, the class of driven states
with an evidence level.

## Licence

Code MIT, data CC-BY-4.0. Kept separate because software and data collections are reused
differently in research.

## Stance

The registry is only useful if it is honest. K3C60 is `contested` because the Meissner test came
back negative and the counter-position of Dodge et al. has not been cleared. Bi₂Se₃ is
`single_group` because every measurement on that material comes from the same group, even
though the phenomenon is independently confirmed elsewhere. A collection that levels such
differences would be worse than none.

© 2026 Daniel Leonforte / Eigenart Filmproduktion
