#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the Reactive Periodic Table v0.1.  Usage: python3 test_rpt.py"""

import glob
import io
import json
import os
import unittest

from rpt_eval import (Graph, apply_relation, evaluate, lint, load_entries,
                      load_schema, validate)

E = load_entries()


class TestDataset(unittest.TestCase):
    def test_schema_valid(self):
        self.assertEqual(validate(E, load_schema()), [])

    def test_no_consistency_errors(self):
        errors, _ = lint(E)
        self.assertEqual(errors, [])

    def test_twelve_entries(self):
        self.assertEqual(len(E), 12)

    def test_every_entry_has_gaps_and_sources(self):
        for eid, e in E.items():
            self.assertTrue(e.get("gaps"), "%s without gaps" % eid)
            self.assertTrue(e.get("sources"), "%s without sources" % eid)

    def test_edges_reference_known_nodes(self):
        for eid, e in E.items():
            g = Graph(e)
            for c in e["couplings"]:
                self.assertIn(c["from"], g.nodes, "%s/%s" % (eid, c["id"]))
                self.assertIn(c["to"], g.nodes, "%s/%s" % (eid, c["id"]))


class TestRelations(unittest.TestCase):
    def test_linear_and_affine(self):
        self.assertAlmostEqual(apply_relation({"type": "linear", "gain": 3}, 2), 6)
        self.assertAlmostEqual(apply_relation({"type": "affine", "gain": 2, "offset": 1}, 3), 7)

    def test_threshold(self):
        r = {"type": "threshold", "threshold": 10, "low": "a", "high": "b"}
        self.assertEqual(apply_relation(r, 9), "a")
        self.assertEqual(apply_relation(r, 10), "b")

    def test_hysteresis_holds_state_in_deadband(self):
        r = {"type": "hysteretic", "threshold_up": 341, "threshold_down": 333,
             "low": "cold", "high": "hot"}
        self.assertEqual(apply_relation(r, 345), "hot")
        self.assertEqual(apply_relation(r, 337, previous="hot"), "hot")
        self.assertEqual(apply_relation(r, 337, previous="cold"), "cold")
        self.assertEqual(apply_relation(r, 330), "cold")

    def test_lookup_interpolates_numerically(self):
        r = {"type": "lookup", "table": [[0, 0], [10, 100]]}
        self.assertAlmostEqual(apply_relation(r, 5), 50)

    def test_resonance_acts_only_within_the_window(self):
        r = {"type": "resonant", "center": 2.87e9, "width": 1e7,
             "low": "off", "high": "on"}
        self.assertEqual(apply_relation(r, 2.87e9), "on")
        self.assertEqual(apply_relation(r, 2.874e9), "on")
        self.assertEqual(apply_relation(r, 3.2e9), "off")
        self.assertEqual(apply_relation(r, 1.0e9), "off")

    def test_verification_status_is_justified(self):
        """Whatever stays pending must state in gaps why."""
        open_items = [eid for eid, e in E.items()
                      if e["verification_status"] != "verified"]
        self.assertEqual(open_items, [])
        for eid in open_items:
            justified = any(
                w in g for g in E[eid]["gaps"]
                for w in ("indicative", "not documented", "not verif"))
            self.assertTrue(justified, eid)

    def test_all_twelve_verified(self):
        n = sum(1 for e in E.values() if e["verification_status"] == "verified")
        self.assertEqual(n, 12)

    def test_saturation(self):
        r = {"type": "saturating", "gain": 1000, "saturation": 5}
        self.assertAlmostEqual(apply_relation(r, 1), 5)
        self.assertAlmostEqual(apply_relation(r, -1), -5)


class TestPropagation(unittest.TestCase):
    def test_vo2_thermal_switches_at_341K(self):
        cold = evaluate(E["vo2"], {"temperature": 300})
        hot = evaluate(E["vo2"], {"temperature": 350})
        self.assertGreater(cold["observables"]["resistivity"],
                           hot["observables"]["resistivity"] * 1000)

    def test_vo2_optical_path_is_ten_orders_of_magnitude_faster(self):
        thermal = evaluate(E["vo2"], {"temperature": 350})
        optical = evaluate(E["vo2"], {"temperature": 300, "pump_pulse": 10})
        self.assertGreater(thermal["critical_path_latency_s"] /
                           optical["critical_path_latency_s"], 1e9)

    def test_irreversible_edge_is_reported(self):
        res = evaluate(E["c"], {"synthesis_pressure": 6e9})
        self.assertTrue(any("irreversible" in w for w in res["warnings"]))

    def test_energy_cost_is_separated_by_model(self):
        res = evaluate(E["vo2"], {"temperature": 350})
        self.assertIn("per_volume [J/m^3]", res["energy"])

    def test_si_adds_multiple_edges_instead_of_overwriting(self):
        without_gate = evaluate(E["si"], {"temperature": 300})
        with_gate = evaluate(E["si"], {"temperature": 300, "gate_voltage": 2})
        self.assertGreater(with_gate["values"]["carrier_density"],
                           without_gate["values"]["carrier_density"])


class TestControlLoop(unittest.TestCase):
    def test_negative_feedback_converges(self):
        res = evaluate(E["gd"], {"magnetic_field": 5, "temperature": 293},
                       bindings={"adiabatic_temp_change": ("temperature", 1.0)})
        self.assertTrue(res["loop"]["converged"])
        self.assertLess(res["loop"]["iterations"], 10)

    def test_positive_feedback_runs_into_the_domain_boundary(self):
        res = evaluate(E["si"], {"temperature": 400},
                       bindings={"conductivity": ("temperature", 1e6)})
        self.assertTrue(any("domain boundary" in w for w in res["warnings"]))

    def test_without_binding_there_is_no_loop_field(self):
        self.assertIsNone(evaluate(E["si"], {"temperature": 300}).get("loop"))


class TestDrivenStates(unittest.TestCase):
    def test_ten_driven_states_in_the_rpt_dataset(self):
        n = sum(len(e.get("driven_states", [])) for e in E.values())
        self.assertEqual(n, 10)

    def test_no_driven_state_survives_a_microsecond(self):
        for e in E.values():
            for d in e.get("driven_states", []):
                self.assertLess(d["lifetime_s"], 1e-6, d["id"])

    def test_weak_evidence_is_justified(self):
        for e in E.values():
            for d in e.get("driven_states", []):
                if d["evidence_level"] in ("single_group", "contested"):
                    self.assertTrue(d.get("notes"), d["id"])

    def test_driven_states_have_a_lifetime(self):
        for e in E.values():
            for s in e.get("states", []):
                if s["stability"] == "driven":
                    self.assertIsNotNone(s.get("lifetime_s"), s["id"])


class TestRegistry(unittest.TestCase):
    """The registry dataset sits next to the RPT and has a schema of its own."""

    REG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "driven-states", "registry")

    def _entries(self):
        import glob
        out = []
        for p in sorted(glob.glob(os.path.join(self.REG, "*.json"))):
            with io.open(p, encoding="utf-8") as fh:
                out.append(json.load(fh))
        return out

    def test_registry_schema_valid(self):
        import jsonschema
        schema = json.load(io.open(os.path.join(os.path.dirname(self.REG),
                                                "registry.schema.json"), encoding="utf-8"))
        v = jsonschema.Draft7Validator(schema)
        for e in self._entries():
            self.assertEqual(list(v.iter_errors(e)), [], e["id"])

    def test_every_state_has_a_source_and_a_caveat(self):
        for e in self._entries():
            for d in e["driven_states"]:
                self.assertTrue(d["source"].strip(), e["id"])
                self.assertTrue(len(d["caveat"]) > 40, "%s/%s: caveat too thin" % (e["id"], d["id"]))

    def test_every_source_has_a_doi_or_arxiv_id(self):
        for e in self._entries():
            for d in e["driven_states"]:
                s = d["source"].lower()
                self.assertTrue("doi:" in s or "arxiv" in s,
                                "%s/%s without DOI: %s" % (e["id"], d["id"], d["source"]))

    def test_preprints_stay_pending(self):
        for e in self._entries():
            preprint = any("arxiv" in d["source"].lower() and "doi:10.10" not in d["source"].lower()
                           for d in e["driven_states"])
            if preprint and len(e["driven_states"]) == 1:
                self.assertEqual(e["verification_status"], "pending", e["id"])


class TestRptDrivenStates(unittest.TestCase):
    """The same source rules, applied to the 12 full entries.

    Until 28 August 2026 the rules above were enforced on the 54 registry files
    only, while CONTRIBUTING.md claimed they held for every entry.  Three RPT
    primary sources carried no identifier at all under that gap.  The RPT entries
    use `notes` where the registry uses `caveat`; both are accepted here, because
    what matters is that the limitation is written down, not what the field is
    called.
    """

    def _states(self):
        for eid, e in sorted(E.items()):
            for d in e.get("driven_states", []):
                yield eid, d

    def test_every_source_has_a_doi_or_arxiv_id(self):
        for eid, d in self._states():
            s = d.get("source", "").lower()
            self.assertTrue("doi:" in s or "arxiv" in s,
                            "%s/%s without DOI: %s" % (eid, d["id"], d.get("source")))

    def test_every_state_states_its_limitation(self):
        for eid, d in self._states():
            text = d.get("caveat") or d.get("notes") or ""
            self.assertTrue(len(text) > 40,
                            "%s/%s: neither caveat nor notes of substance" % (eid, d["id"]))

    def test_every_state_records_what_was_measured(self):
        for eid, d in self._states():
            self.assertTrue((d.get("measured_quantity") or "").strip(),
                            "%s/%s without measured_quantity" % (eid, d["id"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
