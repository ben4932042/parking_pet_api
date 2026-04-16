# Docstring Workflow

## Scope

This document defines the required docstring expectations for Python code in this repository.

## When To Read This Doc

Read this document when:

- adding a new Python module
- adding or changing a public class, function, or method
- reviewing code for maintainability and developer readability
- deciding whether a helper needs documentation

## Rules

- New Python code in `domain/`, `application/`, `interface/`, and `infrastructure/` should include docstrings for public modules, public classes, and public functions or methods.
- Treat names without a leading underscore as public unless there is a strong local convention that clearly says otherwise.
- Write docstrings to explain purpose, behavior, and important side effects or invariants; do not restate obvious implementation details from the signature.
- Add or update docstrings in the same change when behavior changes in a way that affects callers, reviewers, or future maintainers.
- Private helpers may omit docstrings when the logic is short and obvious from the code and surrounding context.
- Private helpers should still get docstrings when they encode non-obvious business rules, normalization rules, heuristics, or edge-case handling.
- Prefer concise multi-line docstrings over long prose blocks.
- Keep examples, if needed, short and directly tied to repository behavior.
- Tests do not need blanket docstring coverage by default. Add test docstrings only when they clarify an unusual setup, fixture contract, or regression scenario.

## Guidance By Layer

- `domain/`: document entities, value objects, and repository contracts when the meaning of fields, invariants, or lifecycle expectations is not completely obvious from types alone.
- `application/`: document use-case services and business-rule helpers, especially when they coordinate multiple repositories, ranking rules, or interpretation logic.
- `interface/`: document public API helpers and route-adjacent utilities when they perform mapping, validation, or response-shaping that is not trivial from the framework decorator alone.
- `infrastructure/`: document adapters where external-system behavior, persistence assumptions, retries, caching, or serialization choices matter.

## Non-Goals

- Do not add noisy docstrings to every trivial getter, setter, or one-line data container if the docstring would only repeat the symbol name and type hints.
- Do not use docstrings as a substitute for clear naming or small functions.

## Validation

- When touching a public API surface, confirm the affected public symbols still have accurate docstrings before finishing.
- When introducing a new module with several public entry points, do a quick pass for consistency so the file does not mix documented and undocumented public symbols without a reason.
- If automated docstring linting is added later, align this document and the lint configuration in the same change.

## Related Files

- `AGENTS.md`
- `docs/README.md`
- `docs/documentation/architecture.md`
