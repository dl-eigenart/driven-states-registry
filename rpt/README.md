# Reactive Periodic Table (RPT) v0.1

A machine-readable description layer for the **controllability** of matter. Existing databases
(Materials Project, AFLOW, OQMD, NOMAD) catalogue what a material *is*. This layer describes
what can be *done* with it: which degree of freedom is reachable through which actuator, at what
latency, at what energy cost, with what coupling to other degrees of freedom.

The catalogue is the easily copied part. The independent part is the **evaluation rule** in
`rpt_eval.py`.

## Files

| File | Content |
|---|---|
| `rpt.schema.json` | JSON schema of the element descriptor (draft 2020-12) |
| `entries/*.json` | 12 seed entries, each independently validatable |
| `rpt_eval.py` | Validator, linter, coupling-graph evaluator, CLI |
| `test_rpt.py` | 29 tests (dataset, relations, propagation, control loop, registry) |

## Usage

```bash
python3 rpt_eval.py list                 # overview
python3 rpt_eval.py show vo2             # entry in detail
python3 rpt_eval.py lint                 # schema and consistency
python3 rpt_eval.py driven               # all driven states
python3 test_rpt.py                      # tests

# propagation: same degree of freedom, two actuation routes
python3 rpt_eval.py eval vo2 --set temperature=350
python3 rpt_eval.py eval vo2 --set temperature=300 --set pump_pulse=10

# close a control loop (feed an observable back onto an actuator)
python3 rpt_eval.py eval gd --set magnetic_field=5 --set temperature=293 \
    --bind adiabatic_temp_change=temperature
python3 rpt_eval.py eval si --set temperature=400 \
    --bind conductivity=temperature@1e6
```

## What the evaluator does

1. **Propagation** of actuator values through the directed coupling graph in topological order,
   with typed relations (linear, affine, power, exponential, threshold, hysteretic, saturating,
   lookup, resonant, qualitative).
2. **Latency on the critical path.** Where actuation routes compete, the edge that actually sets
   the value also sets the latency - otherwise a slow side path masks a fast one. VO2 shows the
   case: the same degree of freedom, 2 ms thermally, 0.3 ps optically.
3. **Energy cost**, kept separate by model (per_volume, per_cycle, ...). Deliberately not summed
   into a single unit; that would be false precision.
4. **Multiple edges** into the same node resolved through `combine`: overwrite (default), add,
   max. Carrier density contributions add, phase states overwrite.
5. **Domain bounds** as physics, not numerics: a degree of freedom is clamped at its domain and
   this is reported. A control loop running into the bound is the statement that the model has
   left its range of validity.
6. **Irreversible edges** are detected and excluded from control loops.
7. **Control loops** through explicit bindings `--bind observable=actuator[@gain]`. The evaluator
   sets the actuator rather than accumulating onto it - cumulative addition is the most common
   modelling error and produces spurious divergence.

## The finding that came out of building it

None of the three declared feedback loops (Fe, Gd, Si) is closed within the graph. Observable
and actuator are separate nodes; the loop closes through the physical world, not through the
model. The linter reports this as a finding, not an error. A real measurement-feedback loop
needs an explicit binding - precisely the distinction between description and control that
separates layers 1 and 2 from layer 3 in the QFI bridge.

## Source verification

All twelve entries have been checked against primary literature. Found and corrected, among
others: two factor-1000 errors in conductivity constants (Si, GaN), a factor-10 error
(graphene), an inverted sign (VO2 strain coupling), a physically wrong excitation model (NV
centre: a resonance was modelled as a threshold), three deviating support points of the YBCO
doping dome, and a wrong scaling exponent (Bi2Se3). Two citations were misattributed.

All twelve entries now read `verified`. New since v0.1: the relation type `resonant`, and for
VO2 the transition temperature as its own degree of freedom.

## Limits of this version

- Microstructure (pinning, grain boundaries, defects) cannot be represented although it belongs
  physically. See `gaps` in `nb.json`.
- Fabrication parameters and runtime parameters are not separated. A field
  `actuation_stage: fabrication | runtime` belongs in v0.2. See `c.json`.
- Interfaces and heterostructures need their own entry type. See `gan.json`.

## Patent situation

The prior-art gate of 20 August 2026 found **US 11 138 772 B2**: a materials-property coupling
graph with relation formula and confidence per edge, confidence as edge weight, and path search.
The coupling graph as such is therefore anticipated. What remained free: actuators as a node
class, latency and energy cost per edge, the evaluation rule (energy sum plus critical path),
the feedback binding - and, with no template found at all, the class of driven states with an
evidence level.

## Language

Everything in this project is English - data, identifiers, code comments, CLI output,
documentation.

## Licence

Code MIT, data CC-BY-4.0.

(c) 2026 Daniel Leonforte / Eigenart Filmproduktion
