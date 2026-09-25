# Driven States Registry & Reactive Periodic Table

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22142490.svg)](https://doi.org/10.5281/zenodo.22142490)
[![validate](https://github.com/dl-eigenart/driven-states-registry/actions/workflows/validate.yml/badge.svg)](https://github.com/dl-eigenart/driven-states-registry/actions/workflows/validate.yml)
[![Code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)

Two connected pieces of open infrastructure for **non-equilibrium materials**:

- **[`driven-states/`](driven-states/)** — a registry of material states that exist *only while a
  drive is running*: light-induced phases and Floquet-engineered bands. 82 states across 58 host
  materials, each with drive parameters, lifetime, mechanism, an explicit evidence level and a
  primary source with a verified DOI. The searched domains are light-driven
  throughout; non-optical drives are admitted by the schema but not yet surveyed.
- **[`rpt/`](rpt/)** — a machine-readable description layer for the **controllability** of matter,
  with an evaluator that propagates actuator values through a coupling graph and reports the
  critical path, energy costs and control-loop behaviour.

**[Open the explorer →](https://dl-eigenart.github.io/driven-states-registry/)** — or open `index.html` from a local clone. It is
self-contained: all data inline, no CDN, no network, no server.

---

## Why this exists

Materials databases catalogue what a material *is* at equilibrium. Driven states are not
eigenstates of the undriven Hamiltonian, so no equilibrium data model can hold them — and a
prior-art search in August 2026 confirmed that none does. Not Materials Project, AFLOW, OQMD,
NOMAD or OPTIMADE; not the NeXus application definitions of the ultrafast facilities; not the
Floquet computation codes. The field *evidence level* has no precedent in any materials schema
either, although the dispute over light-induced superconductivity shows exactly why it is needed.

## Provenance — read this first

Literature search and field extraction were performed by **AI agents under human direction**.
**No entry has undergone peer review.** `peer_reviewed: false` holds for all 82 states.
One entry was revised in September 2026 after comments from a domain expert; that was
correspondence, not review.

On 28 August 2026 all 147 distinct identifiers in the dataset were resolved
programmatically against Crossref and DataCite, and the returned title, journal, volume,
page and author list compared against the citation string stored here. All 147 resolve.
The pass found and fixed four errors: one DOI pointing to an entirely different paper, one
wrong volume and year, one preprint carrying the author list of a different paper, and one secondary reference
labelled ambiguously. It also found that three primary sources in `rpt/entries/` carried no
identifier at all, because the tests enforcing that rule read only `driven-states/registry/`.
Both gaps are closed. This is stated rather than summarised as "verified" because the
earlier wording claimed more than had been done.

This is a structured, fully sourced starting point, not a reviewed reference. Every entry carries
its sources so that any claim can be checked against the original. Corrections are the intended
path to improvement — see [CONTRIBUTING.md](CONTRIBUTING.md).

## What the numbers say

| Metric | Distribution |
|---|---|
| Evidence | 11 established · 13 reproduced · **49 single group** · 9 contested |
| Stability | 50 driven · 17 metastable · 15 driven-to-metastable |
| Mechanism | 35 electronic · 17 mixed · 15 lattice/strain · 6 thermal · 6 unresolved · 3 field tunnelling |
| Lifetime | 1e-13 s to 1e7 s — 20 orders of magnitude |

The distribution is itself a finding. **Forty-nine of eighty-two states rest on a single group.**
No review article makes that as visible as a table that counts it.

Null results and controls carry equal weight: LBCO x = 0.125 (no photo-superconductor), LSCO
(artifact warning about the reconstruction method underlying most positive cuprate results),
Bi2212 (never a defensible signature despite heavy study), KTaO₃ (same signature, traced to defect
physics), κ-Cl and κ-NCS (the effect appears only in κ-Br), Sr₂IrO₄ (the measurement refutes the
material's own Mott classification). FeRh is kept as a calibration point: a thermal shortcut to a
phase that is stable anyway — anyone reporting a new case should be able to show theirs is not an
FeRh.

## Quick start

```bash
pip install jsonschema

python3 rpt/rpt_eval.py list              # the 12 full entries
python3 rpt/rpt_eval.py show vo2          # one entry in detail
python3 rpt/rpt_eval.py lint              # schema and consistency
python3 rpt/test_rpt.py                   # 29 tests

# the same degree of freedom, two actuation routes:
python3 rpt/rpt_eval.py eval vo2 --set temperature=350            # 2 ms, thermal
python3 rpt/rpt_eval.py eval vo2 --set temperature=300 --set pump_pulse=10   # 0.3 ps, optical

cd driven-states && python3 build_site.py # rebuild the explorer
```

## Repository layout

```
rpt/                    Reactive Periodic Table: schema, 12 full entries, evaluator, tests
driven-states/          Registry: schema, 54 light entries, explorer build
  registry/             one JSON file per host material
  index.html            the built explorer (committed; CI checks it is current)
index.html              identical mirror at the repository root, so GitHub Pages serves the
                        short address. Generated - edit template.html, not this.
scripts/check_publish.py  states exactly which files are public
.github/workflows/      schema validation, tests, and a build-freshness check
```

## Licence

Code MIT ([LICENSE](LICENSE)), data CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)). Kept separate
because software and data collections are reused differently in research.

## Citation

See [CITATION.cff](CITATION.cff). Archived on Zenodo:

> Leonforte, D. (2026). *Driven States Registry and Reactive Periodic Table* (v0.1.2)
> [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22788908

**10.5281/zenodo.22142490** is the concept DOI and always resolves to the latest version.
Cite this one unless you depend on a specific snapshot. Every version also carries its own
DOI that never changes; for v0.1.2 that is **10.5281/zenodo.22788908**.

## Language

Everything here is English — data, identifiers, code comments, CLI output, documentation.

© 2026 Daniel Leonforte
