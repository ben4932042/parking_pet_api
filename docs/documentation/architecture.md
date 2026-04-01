# Documentation Architecture

## Purpose

This document records the documentation structure used in this repository.

## Principles

- Keep `AGENTS.md` minimal.
- Store durable rules, workflows, and feature-specific guidance in `docs/`.
- Organize the first level of `docs/` by functional area.
- Use file names to communicate document intent.
- Make it easy for an agent to find entry points before reading code deeply.

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
