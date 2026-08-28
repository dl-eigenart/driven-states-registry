#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the static explorer page from the RPT and registry entries.

The data is embedded inline so that index.html works without a server and
without a network connection - a double click from the file system is enough.
The same build serves the later GitHub Pages version; only the data source
moves into the repository directory.
"""

import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRIES = os.path.join(os.path.dirname(HERE), "rpt", "entries")
REGISTRY = os.path.join(HERE, "registry")
TEMPLATE = os.path.join(HERE, "template.html")
OUT = os.path.join(HERE, "index.html")
# Zweite Kopie im Wurzelverzeichnis, damit GitHub Pages die kurze Adresse bedient.
# Beide werden im selben Lauf geschrieben, damit sie nicht auseinanderlaufen koennen.
OUT_ROOT = os.path.join(os.path.dirname(HERE), "index.html")


def load():
    """Load RPT full entries and registry light entries separately.

    A registry entry deliberately carries no coupling graph. Inventing one just
    to satisfy the schema would be data fabrication - the interface hides the
    graph and propagation tabs for such entries instead.
    """
    full, reg = [], []
    for p in sorted(glob.glob(os.path.join(ENTRIES, "*.json"))):
        with io.open(p, encoding="utf-8") as fh:
            e = json.load(fh)
            e["entry_type"] = "full"
            full.append(e)
    for p in sorted(glob.glob(os.path.join(REGISTRY, "*.json"))):
        with io.open(p, encoding="utf-8") as fh:
            reg.append(json.load(fh))
    return full, reg


def main():
    full, reg = load()
    # Only materials with driven states enter the registry.
    hosts = [e for e in full if e.get("driven_states")] + reg
    data = {"entries": hosts,
            "generated_from": "rpt v0.1 + dsr registry v0.1",
            "n_rpt_entries": len(full),
            "n_registry_entries": len(reg),
            "date": "2026-08-20"}
    with io.open(TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*__DATA__*/", payload)
    for target in (OUT, OUT_ROOT):
        with io.open(target, "w", encoding="utf-8") as fh:
            fh.write(html)
    n_states = sum(len(e["driven_states"]) for e in hosts)
    n_graph = sum(1 for e in hosts if e.get("couplings"))
    print("%s\n%s\n  %d host materials (%d with coupling graph), %d driven states, "
          "%d kB" % (OUT, OUT_ROOT, len(hosts), n_graph, n_states,
                     os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
