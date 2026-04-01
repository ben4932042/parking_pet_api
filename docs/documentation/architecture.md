# Documentation Architecture

## Purpose

This document records the documentation structure used in this repository.

## Principles

- Keep `AGENTS.md` minimal.
- Store durable rules, workflows, and feature-specific guidance in `docs/`.
- Organize the first level of `docs/` by functional area.
- Use file names to communicate document intent.
- Make it easy for an agent to find entry points before reading code deeply.
- Keep dependency direction aligned with layer boundaries.

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

## File Naming Rules

### `architecture.md`

Use `architecture.md` for structure-oriented documents.

This includes:

- module boundaries
- layering decisions
- ownership and responsibility splits
- design constraints
- taxonomy or classification rules

### `workflow-*.md`

Use `workflow-*.md` for operational documents.

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

## Decision Rule

When deciding between document types:

- If the document explains how the system is structured, use `architecture.md`.
- If the document explains how work should be executed, use `workflow-*.md`.

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
- `Related Files`

### Feature `workflow-*.md`

Prefer this structure:

- `Scope`
- `When To Read This Doc`
- `Entry Points`
- `Rules`
- `Validation`
- `Related Files`

These sections do not need to be long. The goal is fast orientation, not exhaustive prose.

## Relationship With `AGENTS.md`

- `AGENTS.md` should contain only repository-wide rules and lightweight pointers.
- Feature-specific instructions should not be expanded inside `AGENTS.md`.
- If an agent needs feature context, it should follow the pointers in `AGENTS.md` and read the relevant files under `docs/`.

## Agent Expectations

- Before changing a feature, read the relevant feature docs listed in `AGENTS.md`.
- Before changing development workflow or tooling behavior, read the relevant development docs listed in `AGENTS.md`.
- When adding or updating docs, follow the structure and naming rules in this file unless there is a strong reason not to.
- When changing exception flow, keep application errors and interface error mapping separate.
