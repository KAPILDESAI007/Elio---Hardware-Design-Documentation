# AI Rules

# ELIO AI RULES

## Core Design Principles

1. Domain logic MUST NOT depend on UI
2. Infrastructure must not contain business logic
3. Services must be stateless
4. Models must be pure data
5. Orchestrator is the only cross-layer coordinator

## Allocation Rules

- Signals must be classified before allocation
- Spare % applied per module type
- No module over-allocation beyond channel capacity
- Controllers must not exceed node capacity
- Mounting rules must be validated before final export

## Refactor Rule

Any AI agent refactoring must preserve:
- Domain isolation
- Service statelessness
- Deterministic allocation