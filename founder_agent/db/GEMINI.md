# Database Module Rules

- All DB operations must be async.
- No blocking logic allowed.
- Enforce strict typing.
- Never allow raw dict injection into queries.
- Ensure all fields validated via Pydantic.
- Avoid global mutable defaults.
- Check for missing indexes.
