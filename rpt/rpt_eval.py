#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reactive Periodic Table (RPT) v0.1 - validator and coupling-graph evaluator.

The catalog is the part that is easy to copy. The protectable part is this
evaluation: directed couplings with relation, latency and energy cost,
propagated from actuators to observables, with explicit handling of cycles
(feedback loops), irreversible edges and driven states.

CLI:
    python3 rpt_eval.py list
    python3 rpt_eval.py show vo2
    python3 rpt_eval.py eval vo2 --set temperature=350
    python3 rpt_eval.py eval si  --set gate_voltage=2 --set temperature=300
    python3 rpt_eval.py lint
    python3 rpt_eval.py driven

(c) 2026 Daniel Leonforte / Eigenart Filmproduktion
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY_DIR = os.path.join(HERE, "entries")
SCHEMA_PATH = os.path.join(HERE, "rpt.schema.json")

QUALITATIVE = "<qualitative>"
UNRESOLVED = "<not determinable>"


# ----------------------------------------------------------------------------- loading

def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_entries() -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(ENTRY_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        out[data["id"]] = data
    return out


def validate(entries: Dict[str, dict], schema: dict) -> List[str]:
    """JSON schema validation. Returns a list of error messages."""
    errors: List[str] = []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed - schema check skipped"]
    validator = jsonschema.Draft7Validator(schema)
    for eid, entry in entries.items():
        for err in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append("%s: %s -> %s" % (eid, loc, err.message))
    return errors


# ----------------------------------------------------------------------------- graph

class Graph:
    """Coupling graph of a single entry."""

    def __init__(self, entry: dict):
        self.entry = entry
        self.inputs = {i["id"]: i for i in entry.get("inputs", [])}
        self.dofs = {d["id"]: d for d in entry.get("degrees_of_freedom", [])}
        self.outputs = {o["id"]: o for o in entry.get("outputs", [])}
        self.couplings = {c["id"]: c for c in entry.get("couplings", [])}
        self.nodes = set(self.inputs) | set(self.dofs) | set(self.outputs)
        self.edges: List[Tuple[str, str, str]] = [
            (c["from"], c["to"], c["id"]) for c in entry.get("couplings", [])
        ]

    # -- cycles ---------------------------------------------------------------

    def cycles(self) -> List[List[str]]:
        """Finds cycles (Tarjan SCC with more than one node, or a self edge)."""
        index: Dict[str, int] = {}
        low: Dict[str, int] = {}
        on_stack: Dict[str, bool] = {}
        stack: List[str] = []
        result: List[List[str]] = []
        counter = [0]
        succ: Dict[str, List[str]] = {n: [] for n in self.nodes}
        for a, b, _ in self.edges:
            if a in succ and b in self.nodes:
                succ[a].append(b)

        def strongconnect(v: str) -> None:
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack[v] = True
            for w in succ.get(v, []):
                if w not in index:
                    strongconnect(w)
                    low[v] = min(low[v], low[w])
                elif on_stack.get(w):
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1 or any(a == v and b == v for a, b, _ in self.edges):
                    result.append(sorted(comp))

        sys.setrecursionlimit(10000)
        for n in sorted(self.nodes):
            if n not in index:
                strongconnect(n)
        return result

    def back_edges(self) -> set:
        """Edges that lie inside a cycle; they are broken during propagation."""
        cyc_nodes = set()
        for comp in self.cycles():
            cyc_nodes |= set(comp)
        return {cid for a, b, cid in self.edges if a in cyc_nodes and b in cyc_nodes}

    def topo_order(self, skip: set) -> List[str]:
        indeg = {n: 0 for n in self.nodes}
        succ: Dict[str, List[Tuple[str, str]]] = {n: [] for n in self.nodes}
        for a, b, cid in self.edges:
            if cid in skip or a not in self.nodes or b not in self.nodes:
                continue
            indeg[b] += 1
            succ[a].append((b, cid))
        queue = sorted([n for n in self.nodes if indeg[n] == 0])
        order: List[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for b, _ in succ[n]:
                indeg[b] -= 1
                if indeg[b] == 0:
                    queue.append(b)
                    queue.sort()
        return order


# ----------------------------------------------------------------------------- relations

def apply_relation(rel: dict, x: Any, previous: Any = None) -> Any:
    """Evaluates a coupling relation. Returns a number, a state string or a marker."""
    t = rel["type"]

    if t == "qualitative":
        return QUALITATIVE

    if t == "lookup":
        table = rel.get("table", [])
        # string keys: exact match
        if table and isinstance(table[0][0], str):
            for k, v in table:
                if k == x:
                    return v
            return UNRESOLVED
        # numeric keys: linear interpolation
        if not isinstance(x, (int, float)):
            return UNRESOLVED
        pts = sorted(((float(k), float(v)) for k, v in table), key=lambda p: p[0])
        if not pts:
            return UNRESOLVED
        if x <= pts[0][0]:
            return pts[0][1]
        if x >= pts[-1][0]:
            return pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                if x1 == x0:
                    return y0
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return UNRESOLVED

    if t == "resonant":
        # Resonant coupling: acts only within one linewidth around the center
        # frequency. A threshold would be physically wrong here, because above
        # the resonance the coupling disappears again.
        if not isinstance(x, (int, float)):
            return UNRESOLVED
        if abs(x - rel["center"]) <= rel.get("width", 0.0) / 2.0:
            return rel.get("high")
        return rel.get("low")

    if t == "threshold":
        if not isinstance(x, (int, float)):
            return UNRESOLVED
        return rel.get("high") if x >= rel["threshold"] else rel.get("low")

    if t == "hysteretic":
        if not isinstance(x, (int, float)):
            return UNRESOLVED
        up, down = rel["threshold_up"], rel["threshold_down"]
        if x >= up:
            return rel.get("high")
        if x <= down:
            return rel.get("low")
        return previous if previous is not None else rel.get("low")

    if not isinstance(x, (int, float)):
        return UNRESOLVED

    if t == "linear":
        return rel.get("gain", 1.0) * x
    if t == "affine":
        return rel.get("gain", 1.0) * x + rel.get("offset", 0.0)
    if t == "power":
        scale, exp = rel.get("scale", 1.0), rel.get("exponent", 1.0)
        if x < 0 and not float(exp).is_integer():
            return UNRESOLVED
        return scale * (abs(x) ** exp) * (1 if x >= 0 else -1) ** int(exp if float(exp).is_integer() else 1)
    if t == "exponential":
        try:
            return rel.get("scale", 1.0) * math.exp(rel.get("gain", 1.0) * x)
        except OverflowError:
            return math.copysign(float("inf"), rel.get("scale", 1.0))
    if t == "saturating":
        y = rel.get("gain", 1.0) * x
        sat = rel.get("saturation")
        if sat is None:
            return y
        return math.copysign(min(abs(y), abs(sat)), y)

    return UNRESOLVED


# ----------------------------------------------------------------------------- evaluation

def evaluate(entry: dict, settings: Dict[str, float],
             bindings: Optional[Dict[str, Tuple[str, float]]] = None,
             max_iter: int = 50, tol: float = 1e-9, relaxation: float = 1.0) -> dict:
    """Propagates actuator values through the coupling graph.

    bindings closes a control loop: {observable: (actuator, gain)}. The measured
    value is fed back onto the actuator with gain and the propagation is
    repeated until it converges. This is the generic form of the
    measurement-feedback loop - in the graph itself this cycle does not exist,
    because observable and actuator are separate nodes.
    """
    if bindings:
        base0 = dict(settings)
        settings = dict(settings)
        history = []
        for it in range(max_iter):
            res = _propagate(entry, settings)
            changed = 0.0
            for obs, (act, gain) in bindings.items():
                v = res["observables"].get(obs)
                if not isinstance(v, (int, float)):
                    continue
                old_v = float(settings.get(act, 0.0))
                # Feedback onto the initial value, not cumulative: the actuator
                # is set, not summed up. Cumulative addition is the most common
                # modeling error and produces spurious divergence.
                target = float(base0.get(act, 0.0)) + gain * v
                new_v = old_v + relaxation * (target - old_v)
                changed = max(changed, abs(new_v - old_v) / (abs(old_v) + 1e-30))
                settings[act] = new_v
            history.append({"iteration": it + 1,
                            "settings": dict(settings),
                            "observables": dict(res["observables"])})
            if changed < tol:
                res["loop"] = {"converged": True, "iterations": it + 1,
                               "history": history, "bindings": bindings}
                return res
        res = _propagate(entry, settings)
        res["loop"] = {"converged": False, "iterations": max_iter,
                       "history": history, "bindings": bindings}
        res["warnings"].append(
            "Control loop did not converge after %d iterations. For positive "
            "feedback this is the expected result and not an error." % max_iter)
        return res
    return _propagate(entry, settings)


def _propagate(entry: dict, settings: Dict[str, float]) -> dict:
    g = Graph(entry)
    skip = g.back_edges()
    order = g.topo_order(skip)

    values: Dict[str, Any] = {}
    latency: Dict[str, float] = {}
    trace: List[dict] = []
    acc: Dict[str, float] = {}
    energy: Dict[str, float] = {}
    warnings: List[str] = []

    for k, v in settings.items():
        if k not in g.nodes:
            warnings.append("Unknown node '%s' - ignored" % k)
            continue
        values[k] = v
        latency[k] = g.inputs[k]["latency_s"] if k in g.inputs else 0.0

    # Preset discrete degrees of freedom with the first domain value
    for did, d in g.dofs.items():
        if did not in values and d["domain"]["type"] == "discrete":
            values[did] = d["domain"]["values"][0]
            latency.setdefault(did, 0.0)

    by_target: Dict[str, List[dict]] = {}
    for c in entry.get("couplings", []):
        by_target.setdefault(c["to"], []).append(c)

    for node in order:
        for c in by_target.get(node, []):
            if c["id"] in skip:
                continue
            src = c["from"]
            if src not in values:
                continue
            prev = values.get(node)
            y = apply_relation(c["relation"], values[src], prev)
            if y is UNRESOLVED or y == UNRESOLVED:
                warnings.append("Edge %s not evaluable (input %r)" % (c["id"], values[src]))
                continue
            mode = c.get("combine", "overwrite")
            if mode in ("add", "max") and isinstance(y, (int, float)):
                cur = acc.get(node)
                if cur is None:
                    acc[node] = y
                else:
                    acc[node] = cur + y if mode == "add" else max(cur, y)
                values[node] = acc[node]
                # For combined edges all contributions must be present:
                # the slowest one determines the result.
                latency[node] = max(latency.get(node, 0.0), latency.get(src, 0.0) + c["latency_s"])
            else:
                # For overwriting edges, the edge that actually set the value
                # also determines the latency. Otherwise a slow competing path
                # would mask a fast actuation path - exactly the VO2 case of
                # thermal versus optical.
                values[node] = y
                latency[node] = latency.get(src, 0.0) + c["latency_s"]
            # Domain limits are part of the physics, not of the numerics: a
            # degree of freedom cannot leave its value range.
            dom = g.dofs.get(node, {}).get("domain")
            if dom and dom["type"] == "continuous" and isinstance(values[node], (int, float)):
                lo, hi = dom["min"], dom["max"]
                if values[node] < lo or values[node] > hi:
                    clamped = min(max(values[node], lo), hi)
                    msg = "Degree of freedom '%s' clamped at domain boundary (%s -> %s %s)" % (
                        node, values[node], clamped, dom.get("unit", ""))
                    if msg not in warnings:
                        warnings.append(msg)
                    values[node] = clamped
                    acc[node] = clamped
            ec = c.get("energy_cost", {})
            if ec.get("value") is not None:
                key = "%s [%s]" % (ec["model"], ec["unit"])
                energy[key] = energy.get(key, 0.0) + float(ec["value"])
            trace.append({
                "coupling": c["id"],
                "from": src,
                "from_value": values[src],
                "to": node,
                "to_value": y,
                "relation": c["relation"]["type"],
                "latency_s": c["latency_s"],
                "confidence": c["confidence"],
            })

    triggered = []
    for tr in entry.get("transitions", []):
        var = tr["trigger"]["variable"]
        if var not in values or not isinstance(values[var], (int, float)):
            continue
        op, val = tr["trigger"]["operator"], tr["trigger"]["value"]
        if not isinstance(val, (int, float)):
            continue
        hit = {">": values[var] > val, ">=": values[var] >= val,
               "<": values[var] < val, "<=": values[var] <= val,
               "==": values[var] == val}[op]
        if hit:
            triggered.append(tr)
            if not tr["reversible"]:
                warnings.append("Transition %s is irreversible - no control loop possible" % tr["id"])

    observables = {oid: values[oid] for oid in g.outputs if oid in values}
    crit = max((latency[o] for o in observables), default=0.0)

    return {
        "entry": entry["id"],
        "settings": settings,
        "values": values,
        "observables": observables,
        "critical_path_latency_s": crit,
        "energy": energy,
        "trace": trace,
        "triggered_transitions": triggered,
        "feedback_cycles": g.cycles(),
        "broken_edges": sorted(skip),
        "warnings": warnings,
    }


# ----------------------------------------------------------------------------- lint

def lint(entries: Dict[str, dict]) -> Tuple[List[str], List[str]]:
    """Returns (errors, notes). Notes are findings, not defects."""
    issues: List[str] = []
    infos: List[str] = []
    for eid, e in entries.items():
        g = Graph(e)
        for c in e.get("couplings", []):
            if c["from"] not in g.nodes:
                issues.append("%s/%s: source '%s' not defined" % (eid, c["id"], c["from"]))
            if c["to"] not in g.nodes:
                issues.append("%s/%s: target '%s' not defined" % (eid, c["id"], c["to"]))
            if c["to"] in g.inputs:
                issues.append("%s/%s: edge points at an actuator - check direction" % (eid, c["id"]))
        for st in e.get("states", []):
            if st["stability"] == "driven" and st.get("lifetime_s") is None:
                issues.append("%s/%s: driven state without lifetime" % (eid, st["id"]))
        for ds in e.get("driven_states", []):
            if ds["evidence_level"] in ("single_group", "contested") and not ds.get("notes"):
                issues.append("%s/%s: weak evidence without an explanatory note" % (eid, ds["id"]))
        for tr in e.get("transitions", []):
            for key in ("from_state", "to_state"):
                if tr[key] not in {s["id"] for s in e.get("states", [])}:
                    issues.append("%s/%s: %s '%s' not in states" % (eid, tr["id"], key, tr[key]))
        cyc_nodes = set()
        for comp in g.cycles():
            cyc_nodes |= set(comp)
        for fb in e.get("feedback_loops", []):
            for cid in fb["path"]:
                if cid not in g.couplings:
                    issues.append("%s/%s: path element '%s' is not a coupling" % (eid, fb["id"], cid))
            chain = [g.couplings[c] for c in fb["path"] if c in g.couplings]
            for a, b in zip(chain, chain[1:]):
                if a["to"] != b["from"]:
                    infos.append(
                        "%s/%s: path breaks off - %s ends at '%s', %s starts at '%s'. "
                        "The loop closes through the physical world, not through the graph."
                        % (eid, fb["id"], a["id"], a["to"], b["id"], b["from"]))
            touched = set()
            for cid in fb["path"]:
                c = g.couplings.get(cid)
                if c:
                    touched |= {c["from"], c["to"]}
            if touched and not touched <= cyc_nodes:
                infos.append(
                    "%s/%s: declared control loop is not closed within the graph "
                    "(observable and actuator are separate nodes). Only evaluable via an "
                    "explicit binding: rpt_eval.py eval %s --bind <obs>=<act>"
                    % (eid, fb["id"], eid))
        if not e.get("gaps"):
            issues.append("%s: no gaps documented - working discipline violated" % eid)
        if not e.get("sources"):
            issues.append("%s: no sources given" % eid)
    return issues, infos


# ----------------------------------------------------------------------------- output

def fmt(v: Any) -> str:
    if isinstance(v, float):
        if v == 0:
            return "0"
        if abs(v) >= 1e5 or abs(v) < 1e-3:
            return "%.3e" % v
        return "%.4g" % v
    return str(v)


def cmd_list(entries, _args):
    print("%-10s %-28s %-18s %5s %5s %5s" % ("id", "Name", "Class", "DoF", "Edge", "Drv"))
    print("-" * 78)
    for eid, e in entries.items():
        print("%-10s %-28s %-18s %5d %5d %5d" % (
            eid, e["name"][:28], e["class"],
            len(e.get("degrees_of_freedom", [])),
            len(e.get("couplings", [])),
            len(e.get("driven_states", []))))
    print("\n%d entries." % len(entries))


def cmd_show(entries, args):
    e = entries[args.id]
    print("=" * 78)
    print("%s (%s)  -  %s" % (e["name"], e.get("formula", ""), e["class"]))
    print("=" * 78)
    print(e.get("summary", ""))
    print("\nActuators:")
    for i in e.get("inputs", []):
        r = i["range"]
        print("  %-20s %-18s %g .. %g %-8s  t=%s  %s" % (
            i["id"], i["kind"], r["min"], r["max"], r["unit"],
            fmt(i["latency_s"]), "reversible" if i["reversible"] else "IRREVERSIBLE"))
    print("\nCouplings:")
    for c in e.get("couplings", []):
        print("  %-18s %-22s -> %-22s %-12s t=%-9s [%s]" % (
            c["id"], c["from"], c["to"], c["relation"]["type"],
            fmt(c["latency_s"]), c["confidence"]))
    if e.get("driven_states"):
        print("\nDriven states (non-equilibrium):")
        for d in e["driven_states"]:
            print("  %-16s %-46s lifetime=%s  [%s]" % (
                d["id"], d["emergent_property"][:46],
                fmt(d.get("lifetime_s")), d["evidence_level"]))
    g = Graph(e)
    cyc = g.cycles()
    if cyc:
        print("\nFeedback loops detected: %s" % "; ".join(" - ".join(c) for c in cyc))
    print("\nGaps:")
    for gp in e.get("gaps", []):
        print("  - %s" % gp)


def cmd_eval(entries, args):
    settings = {}
    for s in args.set or []:
        k, _, v = s.partition("=")
        try:
            settings[k] = float(v)
        except ValueError:
            settings[k] = v
    bindings = {}
    for b in getattr(args, "bind", None) or []:
        lhs, _, rhs = b.partition("=")
        act, _, gain = rhs.partition("@")
        bindings[lhs] = (act, float(gain) if gain else 1.0)
    res = evaluate(entries[args.id], settings, bindings or None)
    print("=" * 78)
    print("Evaluation: %s   Inputs: %s" % (
        res["entry"], ", ".join("%s=%s" % kv for kv in settings.items()) or "(none)"))
    print("=" * 78)
    print("\nPropagation path:")
    for t in res["trace"]:
        print("  %-18s %-20s=%-12s -> %-20s=%-12s (%s, t=%s, %s)" % (
            t["coupling"], t["from"], fmt(t["from_value"]), t["to"], fmt(t["to_value"]),
            t["relation"], fmt(t["latency_s"]), t["confidence"]))
    print("\nObservables:")
    for k, v in res["observables"].items():
        print("  %-26s %s" % (k, fmt(v)))
    print("\nCritical path (latency): %s s" % fmt(res["critical_path_latency_s"]))
    if res["energy"]:
        print("Energy cost:")
        for k, v in res["energy"].items():
            print("  %-30s %s" % (k, fmt(v)))
    if res["triggered_transitions"]:
        print("\nTriggered transitions:")
        for tr in res["triggered_transitions"]:
            print("  %-18s %s -> %s  (t=%s, %s)" % (
                tr["id"], tr["from_state"], tr["to_state"],
                fmt(tr.get("latency_s")), "reversible" if tr["reversible"] else "IRREVERSIBLE"))
    if res["feedback_cycles"]:
        print("\nFeedback loops (broken during propagation):")
        for c in res["feedback_cycles"]:
            print("  %s" % " - ".join(c))
        print("  broken edges: %s" % ", ".join(res["broken_edges"]))
    if res.get("loop"):
        lp = res["loop"]
        print("\nControl loop: %s after %d iterations" % (
            "converged" if lp["converged"] else "NOT converged", lp["iterations"]))
        for obs, (act, gain) in lp["bindings"].items():
            print("  Binding %s -> %s  (gain=%s)" % (obs, act, fmt(gain)))
        for h in lp["history"][:3] + ([{"iteration": "..."}] if len(lp["history"]) > 4 else []) + lp["history"][-1:]:
            if h.get("iteration") == "...":
                print("  ...")
                continue
            print("  Iter %-3s %s" % (h["iteration"], ", ".join(
                "%s=%s" % (k, fmt(v)) for k, v in h["settings"].items())))
    if res["warnings"]:
        print("\nNotes:")
        for w in res["warnings"]:
            print("  ! %s" % w)


def cmd_lint(entries, _args):
    schema_errors = validate(entries, load_schema())
    issues, infos = lint(entries)
    if schema_errors:
        print("Schema errors:")
        for e in schema_errors:
            print("  ! %s" % e)
    else:
        print("Schema: all %d entries valid." % len(entries))
    if issues:
        print("\nErrors:")
        for i in issues:
            print("  ! %s" % i)
    else:
        print("Consistency: no errors.")
    if infos:
        print("\nFindings (not a defect, but a statement of the model):")
        for i in infos:
            print("  * %s" % i)
    return 1 if (schema_errors or issues) else 0


def cmd_driven(entries, _args):
    print("Driven states across the entire dataset")
    print("-" * 78)
    rows = []
    for eid, e in entries.items():
        for d in e.get("driven_states", []):
            rows.append((eid, d["id"], d.get("lifetime_s"), d["evidence_level"],
                         d["emergent_property"]))
    rows.sort(key=lambda r: (r[3], r[0]))
    for eid, did, lt, ev, prop in rows:
        print("%-8s %-16s lifetime=%-10s [%-11s] %s" % (eid, did, fmt(lt), ev, prop[:44]))
    print("\n%d driven states. Not a single one is permanent at room temperature." % len(rows))


def main() -> int:
    p = argparse.ArgumentParser(description="Reactive Periodic Table v0.1")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("eval"); s.add_argument("id"); s.add_argument("--set", action="append")
    s.add_argument("--bind", action="append",
                   help="close a control loop: observable=actuator[@gain]")
    sub.add_parser("lint")
    sub.add_parser("driven")
    args = p.parse_args()
    entries = load_entries()
    if getattr(args, "id", None) and args.id not in entries:
        print("Unknown: %s. Available: %s" % (args.id, ", ".join(entries)))
        return 2
    return {"list": cmd_list, "show": cmd_show, "eval": cmd_eval,
            "lint": cmd_lint, "driven": cmd_driven}[args.cmd](entries, args) or 0


if __name__ == "__main__":
    sys.exit(main())
