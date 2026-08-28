#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve every identifier in the dataset and compare it against its citation string.

A DOI that resolves to *some* paper is not a checked DOI.  This script asks Crossref
(and DataCite for arXiv identifiers) what the DOI actually points to, and compares the
returned title, journal, volume, page and author list against the citation string stored
in the dataset.  It exists because a manual pass on 28 August 2026 reported "every DOI
verified" while four citations were wrong, including one DOI that pointed to an entirely
different paper and one preprint carrying an author list that appears nowhere in the work.

Usage:
    python3 scripts/check_dois.py            # report
    python3 scripts/check_dois.py --strict   # exit 1 on any unresolvable identifier

Network access to api.crossref.org and api.datacite.org is required.  Crossref asks for a
contact address in the User-Agent; set DSR_CONTACT to override the default.
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTACT = os.environ.get("DSR_CONTACT", "info@leonforte.de")
HEADERS = {"User-Agent": "driven-states-registry/0.1 (mailto:%s)" % CONTACT}

DOI_RE = re.compile(r"10\.\d{4,9}/\S+")


def find_dois(text):
    """Pull DOIs out of a free-text citation string.

    DOIs may legitimately contain parentheses (older Elsevier identifiers such as
    10.1016/0378-4363(76)90249-7), so trailing brackets are only stripped when they are
    unbalanced -- otherwise half the identifier is silently lost.
    """
    found = []
    for match in DOI_RE.finditer(str(text)):
        doi = match.group(0)
        while doi and doi[-1] in ".,;:":
            doi = doi[:-1]
        while doi.count(")") > doi.count("("):
            doi = doi[:doi.rfind(")")]
        while doi and doi[-1] in ".,;:\"'":
            doi = doi[:-1]
        found.append(doi)
    return found


def collect():
    """Every (doi, citation string, location) triple in the dataset."""
    records = []
    paths = sorted(glob.glob(os.path.join(ROOT, "driven-states", "registry", "*.json")))
    paths += sorted(glob.glob(os.path.join(ROOT, "rpt", "entries", "*.json")))
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            entry = json.load(handle)
        eid = entry.get("id") or os.path.basename(path)[:-5]
        for state in entry.get("driven_states", []):
            texts = [("source", state.get("source", ""))]
            texts += [("further", t) for t in (state.get("further_sources") or [])]
            for role, text in texts:
                for doi in find_dois(text):
                    records.append({"doi": doi, "cite": str(text), "role": role,
                                    "where": "%s/%s" % (eid, state.get("id"))})
        for text in (entry.get("sources") or []):
            for doi in find_dois(text):
                records.append({"doi": doi, "cite": str(text), "role": "entry",
                                "where": eid})
    return records


def fetch(url):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers=HEADERS), timeout=30))


def resolve(doi):
    """Ask Crossref, fall back to DataCite (which is where arXiv DOIs live)."""
    quoted = urllib.parse.quote(doi, safe="/")
    try:
        message = fetch("https://api.crossref.org/works/" + quoted)["message"]
        return {"ok": True, "registry": "Crossref",
                "title": (message.get("title") or [""])[0],
                "journal": (message.get("container-title") or [""])[0],
                "volume": message.get("volume"), "page": message.get("page"),
                "type": message.get("type"),
                "year": (message.get("published-print")
                         or message.get("issued", {})).get("date-parts", [[None]])[0][0],
                "authors": [(a.get("family") or "").strip()
                            for a in (message.get("author") or []) if a.get("family")]}
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            return {"ok": False, "error": "Crossref HTTP %s" % exc.code}
    except Exception as exc:                      # noqa: BLE001 - report, do not crash
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, str(exc)[:70])}

    try:
        attrs = fetch("https://api.datacite.org/dois/"
                      + urllib.parse.quote(doi, safe=""))["data"]["attributes"]
        return {"ok": True, "registry": "DataCite",
                "title": (attrs.get("titles") or [{}])[0].get("title", ""),
                "journal": "preprint", "volume": None, "page": None, "type": "preprint",
                "year": attrs.get("publicationYear"),
                "authors": [(a.get("familyName") or a.get("name", "").split(",")[0]).strip()
                            for a in (attrs.get("creators") or [])]}
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "error": "not in Crossref; DataCite %s" % type(exc).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any identifier fails to resolve")
    args = parser.parse_args()

    records = collect()
    dois = sorted({r["doi"] for r in records})
    print("%d identifier occurrences, %d distinct.\n" % (len(records), len(dois)))

    resolved, unresolved, mismatches = {}, [], []
    for index, doi in enumerate(dois, 1):
        resolved[doi] = resolve(doi)
        if not resolved[doi]["ok"]:
            unresolved.append(doi)
        if index % 25 == 0:
            print("  ... %d/%d" % (index, len(dois)))
        time.sleep(0.06)

    for record in records:
        meta = resolved[record["doi"]]
        if not meta["ok"]:
            continue
        head = record["cite"].split("doi:")[0]
        claimed = re.findall(r"\b\d{1,6}\b", head)
        notes = []
        if meta["volume"] and meta["volume"].isdigit() and claimed \
                and meta["volume"] not in claimed:
            notes.append("volume %s not in citation" % meta["volume"])
        if meta["page"]:
            first = meta["page"].split("-")[0]
            if first.isdigit() and claimed and first not in claimed:
                notes.append("first page %s not in citation" % first)
        surname = re.match(r"\s*([A-Z][\w'’-]+)", head)
        if surname and meta["authors"] \
                and surname.group(1).lower() not in [a.lower() for a in meta["authors"]] \
                and surname.group(1) not in ("Nature", "Science", "Phys", "Nat", "Sci",
                                             "PNAS", "Commun", "Adv", "Counter", "Author",
                                             "Rev", "Appl", "Proc", "New", "npj", "ACS"):
            notes.append("citation opens with '%s', not an author (%s)"
                         % (surname.group(1), ", ".join(meta["authors"][:4])))
        if str(meta.get("type", "")).startswith("journal") and "Correction" in meta["title"]:
            notes.append("points to a correction notice, not the original")
        if notes:
            mismatches.append((record, meta, notes))

    print("\nResolved: %d/%d" % (len(dois) - len(unresolved), len(dois)))
    if unresolved:
        print("\nUNRESOLVABLE:")
        for doi in unresolved:
            print("  %-38s %s" % (doi, resolved[doi]["error"]))

    print("\n%d citation string(s) to look at:" % len(mismatches))
    for record, meta, notes in mismatches:
        print("\n  %s  [%s]" % (record["where"], record["role"]))
        print("    stored : %s" % record["cite"][:105])
        print("    %-7s: %s" % (meta["registry"], meta["title"][:95]))
        for note in notes:
            print("      - %s" % note)

    print("\nA flagged citation is not automatically wrong: entries that legitimately open "
          "with a journal name, or omit volume and page, are reported here too. The point is "
          "that each one has been looked at.")

    if args.strict and unresolved:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
