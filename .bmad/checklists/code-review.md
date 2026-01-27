# Code Review Checklist - Red Letters

## Correctness
- [ ] Logic handles all specified cases
- [ ] Edge cases addressed
- [ ] Error paths handled appropriately
- [ ] Unicode/Greek text handled correctly (NFC normalization)

## Code Quality
- [ ] Functions are small and focused
- [ ] Names are clear and descriptive
- [ ] No code duplication
- [ ] Follows existing patterns in codebase

## Type Safety
- [ ] All functions have type hints
- [ ] Pydantic models used for API data
- [ ] No `Any` types without justification

## Testing
- [ ] Unit tests for new functions
- [ ] Edge cases tested
- [ ] Test coverage maintained (≥80%)
- [ ] Tests are readable and maintainable

## Documentation
- [ ] Docstrings for public functions
- [ ] Complex logic explained
- [ ] ADR written for architectural decisions

## Red Letters Specific
- [ ] Receipts include all required fields
- [ ] Provenance tracked for data
- [ ] No hidden theological assumptions
- [ ] Morphology codes handled correctly
- [ ] Greek text normalized (NFC)

## Performance
- [ ] No obvious N+1 queries
- [ ] Appropriate use of indexes
- [ ] No unbounded loops

## Security
- [ ] No SQL injection vulnerabilities
- [ ] Input validation present
- [ ] No sensitive data logged
