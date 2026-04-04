# Documentation Architecture

## Purpose

This document records the documentation structure used in this repository.

## Principles

- Keep `AGENTS.md` minimal.
- Keep `docs/README.md` as the complete index of documentation in this repository.
- Store durable rules, workflows, and feature-specific guidance in `docs/`.
- Organize the first level of `docs/` by functional area.
- Separate agent-oriented docs from human-oriented docs by document intent and indexing.
- Use file names to communicate document intent.
- Make it easy for an agent to find entry points before reading code deeply.
- Make it easy for a human reader to find explanatory docs and diagrams before reading code deeply.
- Keep a dependency direction aligned with layer boundaries.

## Layer Order

This project follows a clean-architecture-oriented layering model.

The primary dependency direction is:

- `domain`
- `application`
- `interface`

Read this as:

- `domain` is the innermost layer
- `application` depends on `domain`
- `interface` depends on `application`

`infrastructure` is an outer adapter layer and should not pull business decisions away from the inner layers.

## Folder Structure

Use the first level of `docs/` to group documents by function or product area.

Examples:

- `docs/search/`
- `docs/property/`
- `docs/documentation/`

Within each area, keep the audience split explicit in the index:

- agent-oriented docs: execution and structure guidance for implementation work
- human-oriented docs: explanatory guides, walkthroughs, and diagram-heavy references

The repository does not need a separate top-level `agent/` or `human/` folder if the feature area and audience are both clear from naming and indexing.

## File Naming Rules

### `architecture.md`

Use `architecture.md` for structure-oriented, primarily agent-facing documents.

This includes:

- module boundaries
- layering decisions
- ownership and responsibility splits
- design constraints
- taxonomy or classification rules

Prefer concise structure and constraints over walkthrough prose.

If a feature needs diagram-heavy explanation for human readers, keep that material in a separate `guide-*.md` and cross-link the two documents.

### `workflow-*.md`

Use `workflow-*.md` for operational, primarily agent-facing documents.

This includes:

- implementation flow
- optimization loops
- feedback handling
- review or validation steps
- recurring execution rules for a feature

Examples:

- `workflow-user-feedback.md`
- `workflow-optimization.md`
- `workflow-creation.md`
- `workflow-management.md`

### `guide-*.md`

Use `guide-*.md` for human-oriented explanatory documents.

This includes:

- end-to-end walkthroughs
- visual flow explanations
- sequence diagrams or decision trees for readers
- onboarding-oriented summaries
- conceptual explanations that optimize for understanding before implementation

Examples:

- `guide-search-overview.md`
- `guide-auth-sequence.md`

## Decision Rule

When deciding between document types:

- If the document explains how the system is structured, use `architecture.md`.
- If the document explains how work should be executed, use `workflow-*.md`.
- If the document explains how a person should understand the system, especially with diagrams, use `guide-*.md`.
- If a document needs both agent-facing constraints and human-facing walkthroughs, split them into `architecture.md` plus `guide-*.md` instead of mixing both audiences into one file.

## Layering Rules

- Keep the dependency direction aligned with `domain -> application -> interface`.
- `application/` must not depend on `interface/`.
- Application code should raise `application.exceptions` for business and use-case errors.
- `interface/` may depend on `application/` and is responsible for translating application errors into transport-specific responses such as HTTP errors.
- If an error type is meaningful outside FastAPI or HTTP, define it outside `interface/`.
- API-facing exception shapes and status-code mapping belong in `interface/`, not in `application/`.

## Recommended Section Templates

### Feature `architecture.md`

Prefer this structure:

- `Scope`
- `When To Read This Doc`
- `Entry Points`
- `Responsibilities`
- `Design Constraints`
- `Related Files`

### Feature `workflow-*.md`

Prefer this structure:

- `Scope`
- `When To Read This Doc`
- `Entry Points`
- `Rules`
- `Validation`
- `Related Files`

### Human `guide-*.md`

Prefer this structure:

- `Purpose`
- `When To Read This Doc`
- `Diagram`
- `Walkthrough`
- `Related Agent Docs`

These sections do not need to be long. The goal is fast orientation, not exhaustive prose.

## Relationship With `AGENTS.md`

- `AGENTS.md` should contain only repository-wide rules and lightweight pointers.
- `AGENTS.md` should point to the must-read agent docs for each feature.
- Feature-specific instructions should not be expanded inside `AGENTS.md`.
- If an agent needs feature context, it should follow the pointers in `AGENTS.md` and read the relevant files under `docs/`.

## Index Rules

- `docs/README.md` is the canonical documentation index and should list every documentation file under `docs/`.
- Group the index by feature or development area first, then by audience.
- For each feature area, list must-read agent docs explicitly.
- If a human-oriented guide exists, cross-link it from the same feature section and from the related agent docs when useful.
- If a new doc is added under `docs/`, update `docs/README.md` in the same change.

## Agent Expectations

- Before changing a feature, read the relevant feature docs listed in `AGENTS.md`.
- Before changing development workflow or tooling behavior, read the relevant development docs listed in `AGENTS.md`.
- When adding or updating docs, follow the structure, indexing, and naming rules in this file unless there is a strong reason not to.
- When changing exception flow, keep application errors and interface error mapping separate.
