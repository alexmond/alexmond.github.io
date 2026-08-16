# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-repository documentation hub built with **Antora** that aggregates AsciiDoc documentation from multiple open-source Spring Boot projects into a unified site deployed at https://www.alexmond.org/. The site uses the Spring IO Antora UI theme with custom header navigation and theming.

## Build Commands

```bash
# Full build (installs Node/NPM via Maven, generates Antora docs)
mvn -B package

# Same as CI
mvn -B package --file pom.xml --no-transfer-progress
```

There are no test or lint commands — the project is purely documentation.

## Architecture

**Build pipeline:** Maven (`pom.xml`) → `frontend-maven-plugin` (installs Node v24.4.1 / NPM 11.4.2) → `antora-maven-plugin` (runs Antora) → generates static site in `target/site/` and `pages/`.

**Content sources** are defined in `antora-playbook.yml`. The playbook pulls docs from 7 repositories:
- Local (`./`) — main site pages
- 6 remote GitHub repos (some pinned to tags, some tracking `main` branch), each with docs in a `docs/` start path

**Key files:**
- `antora-playbook.yml` — Antora playbook: content sources, UI bundle, site config, analytics
- `projects.yml` — **single source of truth for the project list**; four surfaces are generated from it
- `bin/gen-project-lists.py` — renders those surfaces; `--check` is the CI drift gate
- `antora.yml` — local component descriptor (component name: `home`)
- `pom.xml` — Maven build: Node/NPM versions, plugin versions
- `modules/ROOT/pages/index.adoc` — main homepage content (card blocks *generated*)
- `modules/ROOT/nav.adoc` — home sidebar (*fully generated*)
- `supplemental-ui/` — UI customizations (header, CSS, icons, verification files)
- `supplemental-ui/partials/header-content.hbs` — custom Handlebars navbar (dropdowns *generated*)
- `supplemental-ui/ui.yml` — declares supplemental static files

**Deployment:** GitHub Actions (`.github/workflows/deploy_docs.yml`) builds on push to `main`, deploys to both GitHub Pages and a remote server via SCP.

## Common Changes

**Bumping a project version:** Edit the `tags` value for the relevant source in `antora-playbook.yml`.

**Adding a new project:** Two edits, then regenerate.

1. Add the entry under `content.sources` in `antora-playbook.yml` (what Antora builds).
2. Add the project to `projects.yml` (what the site *shows* — label, url, repo, group, blurb, tags).
3. Run `python3 bin/gen-project-lists.py` and commit the result.

The project list appears on four surfaces — the home sidebar (`modules/ROOT/nav.adoc`), the
homepage cards (`modules/ROOT/pages/index.adoc`), and both navbar dropdowns
(`supplemental-ui/partials/header-content.hbs`). **All four are generated from
`projects.yml`; never hand-edit them** — the generator rewrites the whole nav file and the
regions between the `BEGIN`/`END` markers in the other two.

CI (`.github/workflows/project-lists.yml` on PRs, and a step in the deploy workflow) runs
`bin/gen-project-lists.py --check`, which fails on a stale generated file *and* on a
playbook content source with no `projects.yml` entry (or vice versa) — so a half-added
project can't ship.

**UI customization:** Modify files in `supplemental-ui/`. The site uses Spring IO Antora UI bundle v0.4.15 with supplemental overrides.
