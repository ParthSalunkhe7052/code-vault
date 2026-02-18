# Testing Rules

## Test-Driven Development (TDD)

This project follows strict TDD methodology.

### TDD Cycle
1. **Red Phase**: Write a failing test that defines expected behavior
2. **Green Phase**: Write minimum code to make test pass
3. **Refactor Phase**: Improve code while keeping tests green

### Critical Rules
- Write tests BEFORE implementation
- All tests must fail before implementation (verify Red phase)
- All tests must pass before marking task complete

## Coverage Requirements

- **Minimum coverage**: 80%
- **Target coverage**: >85%
- New code must include corresponding tests

## Test Organization

### Unit Tests
- Mirror source directory structure
- Test file naming: `test_<module_name>.py`
- Each module requires corresponding test file

### Integration Tests
- Test complete user flows
- Verify database transactions
- Test authentication/authorization

### Test Files Location
```
tests/
  test_<module>.py      # Unit tests
  conftest.py           # Fixtures
  test_integration/     # Integration tests
```

## Testing Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_module.py

# Run with verbose output
pytest -v

# Run CI mode (non-interactive)
CI=true pytest
```

## Quality Gates

Before marking task complete:
- [ ] All tests pass
- [ ] Coverage >80% for new code
- [ ] No skipped tests without justification
- [ ] Both success and failure cases tested
- [ ] Edge cases covered

## Test Best Practices

- Use descriptive test names
- One assertion per test when practical
- Use fixtures for common setup
- Mock external dependencies
- Test behavior, not implementation
