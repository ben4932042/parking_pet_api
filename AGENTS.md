# AGENTS.md

Repository-wide instructions for coding agents working in this project.

## Index

- [Testing Rules](#testing-rules)
- [Architecture Guardrails](#architecture-guardrails)
- [Development Docs](#development-docs)
- [Feature Docs](#feature-docs)

## Testing Rules

- Any code change must keep unit tests stable.
- If an interface, abstract class, protocol, shared dependency contract, fixture, or repository API changes, update all related unit-test doubles, stubs, fakes, and mocks in the same change.
- Do not stop after running only targeted tests when the change can affect shared contracts; run the relevant full unit test suite before finishing.
- A task is not complete if unit tests are broken.

## Architecture Guardrails

- This project follows clean-architecture-oriented layering: `domain -> application -> interface`.
- Keep business logic out of framework orchestration layers.
- Rules that encode product behavior, query interpretation, heuristics, or decision policy belong in `application/` or `domain-adjacent` modules, not in framework adapters.
- `infrastructure/` should focus on adapters, prompts, external integrations, persistence details, and orchestration glue.
- If a function would still be meaningful without LangGraph, FastAPI, MongoDB, or vendor SDKs, treat it as business logic first and place it outside infrastructure unless there is a strong reason not to.
- `application/` must not depend on `interface/`; application errors belong in `application.exceptions`, and `interface/` is responsible for mapping them to API responses.

## Development Docs

- Keep `AGENTS.md` minimal. Detailed workflows and conventions should live in `docs/`.
- For documentation structure and naming conventions, read `docs/documentation/architecture.md`.
- When working with user feedback during development, read `docs/development/workflow-user-feedback.md`.
- Before changing development workflow, tooling behavior, or documentation structure, read the relevant development docs first.

## Feature Docs

- Before changing a feature, read the relevant feature docs first and follow their validation rules.
- When working on search, read `docs/search/workflow-optimization.md`.
- When working on nearby property search, read `docs/search/workflow-nearby.md`.
- When working on property architecture or shared property behavior, read `docs/property/architecture.md`.
- When working on property creation, read `docs/property/workflow-creation.md`.
- When working on property management, read `docs/property/workflow-management.md`.
- When working on property favorite flows, read `docs/property/workflow-favorite.md`.
