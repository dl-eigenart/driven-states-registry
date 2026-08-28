# Contributing

The registry improves through corrections. If an entry misrepresents your work, or a value is
wrong, that is the single most valuable contribution you can make — please open an issue rather
than letting it stand.

## What this project is, and what it is not

Every entry was compiled with AI assistance under human direction, checked against the cited
primary literature, and carries a verified DOI. **No entry has been reviewed by a domain
expert.** `peer_reviewed: false` is true for all of them. The registry is a structured, fully
sourced starting point — not a reviewed reference. It is only useful if it stays honest about
that.

## Reporting an error

Open an issue with the entry id, the field, and the source that shows the correct value. A one
line message is enough:

> `tas2_1t / ds_hidden_optical`, `threshold.value`: the fluence threshold is 0.5 mJ/cm², not
> 1.0 — see Stojchevska et al. 2014, Fig. 2b.

You do not need to open a pull request. Errors reported in an issue are fixed by the maintainer.

## Adding an entry

Two entry types exist and the difference matters:

- **Registry entry** (`driven-states/registry/`) — material, equilibrium context, driven states
  with sources. No coupling graph. This is the right type for almost every contribution.
- **RPT full entry** (`rpt/entries/`) — adds actuators, degrees of freedom and a coupling graph
  that the evaluator can propagate. Only add one if defensible coupling data exists. Inventing a
  graph so the schema validates would be data fabrication and will be rejected.

Copy an existing registry entry as a template — `driven-states/registry/ti3o5.json` is a compact
one, `driven-states/registry/tas2_1t.json` a rich one — and follow these rules.

### Hard rules

1. **No entry without a primary source carrying a verified DOI or arXiv identifier.** A test
   enforces this. If you cannot verify the identifier, the entry does not go in.
2. **Every driven state needs a `caveat`.** State what is *not* shown, what is contested, which
   counter-position exists. A test rejects caveats shorter than 40 characters. This field is the
   scientific value of the register; an entry without limitations is an advertisement.
3. **Assign the evidence level conservatively.** When in doubt, go lower.
   - `established` — independently reproduced by several groups
   - `reproduced` — at least two independent works
   - `single_group` — every measurement on *this material* comes from one group, even if the
     phenomenon is confirmed elsewhere
   - `contested` — published counter-positions exist
4. **Report ranges as ranges.** Where the literature scatters, use `fluence_range_mJ_per_cm2` or
   `lifetime_range_s` and say so in the caveat. A single number where the literature gives a
   spread is worse than no number.
5. **Distinguish measured from inferred.** `measured_quantity` records what the instrument
   actually returned. Many topological assignments are inferred from symmetry plus computation,
   not measured — say so.
6. **`stability` follows the endpoint, not the lifetime.** `driven` exists only while energy is
   supplied; `metastable` occupies a local minimum after the drive stops that equilibrium would
   not occupy at that temperature; `equivalent_equilibrium_state: yes` marks switching between
   equilibrium states, which is a borderline case that must stay visible.
7. **Null results and controls belong in the registry.** A material where the effect was looked
   for and not found is as informative as one where it was. See `lbco125`, `bi2212`, `ktao3`.
8. **Preprints without a journal version stay `verification_status: pending`.** A test enforces
   this too.

### Before you open a pull request

```bash
python3 rpt/test_rpt.py          # 29 tests, all must pass
python3 rpt/rpt_eval.py lint     # schema and consistency
cd driven-states && python3 build_site.py   # rebuild index.html
```

The build writes **two identical copies** of the explorer: `driven-states/index.html` and a
mirror at the repository root, which is what GitHub Pages serves. Commit both together with your
data change. Continuous integration rebuilds them and fails if either is stale or if the two
differ.

## Reviewing

If you work in this field and are willing to review entries in your area, that is the
contribution the registry needs most. Reviewing means checking the values and the caveat against
the cited work and saying whether the assessment holds. A reviewed entry gets
`peer_reviewed: true` and your name in `provenance.reviewer`. Open an issue saying which
materials you can cover.

## Language

Everything in this repository is English — data, identifiers, code comments, CLI output,
documentation.

## Licence

Contributions are accepted under the licences of this repository: MIT for code, CC BY 4.0 for
data. By opening a pull request you agree to that.
