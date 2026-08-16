#!/usr/bin/env python3
"""Render the hub's project list into every surface that shows it.

`projects.yml` is the single source of truth. This script writes it into:

  * modules/ROOT/nav.adoc                       — the home sidebar (whole file)
  * modules/ROOT/pages/index.adoc               — the homepage cards (between markers)
  * supplemental-ui/partials/header-content.hbs — both navbar dropdowns (between markers)

Usage:
    python3 bin/gen-project-lists.py            # rewrite the generated surfaces
    python3 bin/gen-project-lists.py --check    # verify they are up to date (CI gate)

--check exits 1 on drift and prints a diff, so a forgotten regenerate fails the build
instead of shipping a half-updated site.

It also cross-checks projects.yml against antora-playbook.yml: every content source must
have a project entry and vice versa. That is the check that actually catches the common
mistake — adding a project to the playbook and forgetting the four places it is listed.
The playbook maps repo -> component via this file's `repo` field, since a component name
often differs from its repo name (component `extensions` <- repo
`spring-boot-actuator-extensions`).
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECTS_YML = ROOT / "projects.yml"
PLAYBOOK = ROOT / "antora-playbook.yml"
NAV = ROOT / "modules" / "ROOT" / "nav.adoc"
INDEX = ROOT / "modules" / "ROOT" / "pages" / "index.adoc"
HEADER = ROOT / "supplemental-ui" / "partials" / "header-content.hbs"

SITE = "https://www.alexmond.org"
GENERATED_NOTE = "generated from projects.yml by bin/gen-project-lists.py — do not edit by hand"


# --------------------------------------------------------------------------- loading


def load_projects() -> tuple[list[dict], list[dict]]:
    data = yaml.safe_load(PROJECTS_YML.read_text())
    groups, projects = data["groups"], data["projects"]
    known = {g["id"] for g in groups}
    for p in projects:
        for field in ("component", "label", "group", "url", "repo", "blurb", "tags"):
            if not p.get(field):
                raise SystemExit(f"projects.yml: {p.get('component', '?')} is missing '{field}'")
        if p["group"] not in known:
            raise SystemExit(f"projects.yml: {p['component']} has unknown group '{p['group']}'")
        if not p["url"].startswith("/") or not p["url"].endswith("/"):
            raise SystemExit(
                f"projects.yml: {p['component']} url must be an absolute directory URL "
                f"(leading and trailing slash), got {p['url']!r}"
            )
    for key in ("component", "repo", "label"):
        seen: dict[str, str] = {}
        for p in projects:
            if p[key] in seen:
                raise SystemExit(f"projects.yml: duplicate {key} {p[key]!r}")
            seen[p[key]] = p["component"]
    return groups, projects


def in_group(projects: list[dict], gid: str) -> list[dict]:
    return [p for p in projects if p["group"] == gid]


# --------------------------------------------------------------------------- renderers


def render_nav(groups: list[dict], projects: list[dict]) -> str:
    out = [f"// {GENERATED_NOTE}", "", "* xref:index.adoc[My Dev Hub]", ""]
    for g in groups:
        out.append(f".{g['heading']}")
        for p in in_group(projects, g["id"]):
            out.append(f"* link:{p['url']}[{p['label']}]")
        out.append("")
    out += [".Elsewhere", "* https://github.com/alexmond[GitHub^]", ""]
    return "\n".join(out)


def render_cards(projects: list[dict]) -> str:
    out = ['<div class="hub-cards">']
    for p in projects:
        tags = " · ".join(p["tags"])
        blurb = " ".join(p["blurb"].split())
        out += [
            f'  <a class="hub-card" href="{p["url"]}">',
            f'    <span class="hub-card-name">{p["label"]}</span>',
            f'    <span class="hub-card-desc">{blurb}</span>',
            f'    <span class="hub-card-tags">{tags}</span>',
            "  </a>",
        ]
    out.append("</div>")
    return "\n".join(out)


def render_dropdown(projects: list[dict], kind: str) -> str:
    indent = " " * 24
    rows = []
    for p in projects:
        href = f"{SITE}{p['url']}" if kind == "docs" else f"https://github.com/{p['repo']}"
        rows.append(f'{indent}<a class="navbar-item" href="{href}">{p["label"]}</a>')
    return "\n".join(rows)


# --------------------------------------------------------------------------- markers


def splice(text: str, marker: str, body: str, comment: str = "html") -> str:
    """Replace the region between BEGIN/END markers, keeping the markers."""
    if comment == "html":
        begin, end = f"<!-- BEGIN {marker} -->", f"<!-- END {marker} -->"
    else:
        begin, end = f"// BEGIN {marker}", f"// END {marker}"
    pattern = re.compile(
        rf"({re.escape(begin)}\n).*?(\n[ \t]*{re.escape(end)})", re.S
    )
    if not pattern.search(text):
        raise SystemExit(f"marker {marker!r} not found — expected {begin} ... {end}")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


# --------------------------------------------------------------------------- playbook


def playbook_components(projects: list[dict]) -> tuple[set[str], set[str]]:
    """Return (components the playbook builds, components projects.yml lists)."""
    playbook = yaml.safe_load(PLAYBOOK.read_text())
    by_repo = {p["repo"]: p["component"] for p in projects}
    built: set[str] = set()
    unmapped: list[str] = []
    for src in playbook["content"]["sources"]:
        url = str(src["url"])
        if not url.startswith("http"):
            continue  # the local `./` source is the home component itself
        slug = re.sub(r"^https://github\.com/|\.git$", "", url)
        if slug in by_repo:
            built.add(by_repo[slug])
        else:
            unmapped.append(slug)
    if unmapped:
        raise SystemExit(
            "antora-playbook.yml builds sources with no projects.yml entry:\n  "
            + "\n  ".join(sorted(unmapped))
            + "\nAdd them to projects.yml (or remove the content source)."
        )
    return built, {p["component"] for p in projects}


# --------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify generated files are current; exit 1 on drift")
    args = ap.parse_args()

    groups, projects = load_projects()

    built, listed = playbook_components(projects)
    if missing := listed - built:
        raise SystemExit(
            "projects.yml lists projects the playbook does not build: "
            + ", ".join(sorted(missing))
            + "\nAdd a content source to antora-playbook.yml (or drop them from projects.yml)."
        )

    targets: list[tuple[Path, str]] = [(NAV, render_nav(groups, projects))]

    index = INDEX.read_text()
    for g in groups:
        index = splice(index, f"cards:{g['id']}", render_cards(in_group(projects, g["id"])))
    targets.append((INDEX, index))

    header = HEADER.read_text()
    header = splice(header, "dropdown:docs", render_dropdown(projects, "docs"))
    header = splice(header, "dropdown:repos", render_dropdown(projects, "repos"))
    targets.append((HEADER, header))

    drifted = []
    for path, new in targets:
        old = path.read_text() if path.exists() else ""
        if old == new:
            continue
        drifted.append(path)
        if args.check:
            rel = path.relative_to(ROOT)
            print(f"--- {rel} (committed)\n+++ {rel} (generated from projects.yml)")
            sys.stdout.writelines(
                difflib.unified_diff(old.splitlines(True), new.splitlines(True), n=1, lineterm="\n")
            )
        else:
            path.write_text(new)

    if args.check:
        if drifted:
            print(
                f"\n{len(drifted)} generated file(s) are stale. "
                "Run `python3 bin/gen-project-lists.py` and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"projects.yml: {len(projects)} projects, all generated surfaces up to date.")
        return 0

    print(f"projects.yml: {len(projects)} projects -> rewrote {len(drifted)} file(s).")
    for p in drifted:
        print(f"  {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
