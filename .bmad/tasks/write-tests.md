# Task: Write Tests

## Purpose
Create comprehensive tests following TDD principles.

## Steps

1. **Identify Test Scope**
   - What functionality to test?
   - Unit, integration, or acceptance?
   - Which module/function?

2. **Write Failing Tests First**
   ```python
   def test_[feature]_[scenario]():
       # Arrange
       ...
       # Act
       ...
       # Assert
       ...
   ```

3. **Test Categories**
   - **Happy path**: Normal successful operation
   - **Edge cases**: Boundary conditions
   - **Error cases**: Invalid input handling
   - **Greek-specific**: Unicode, normalization

4. **Red Letters Specific Tests**
   - Receipt completeness
   - Morphology parsing
   - Sense selection
   - Rendering style variations

5. **Fixtures**
   - Reuse existing fixtures in `tests/fixtures/`
   - Create new fixtures if needed
   - Document fixture purpose

6. **Run Tests**
   ```bash
   pytest tests/test_[module].py -v
   pytest --cov=redletters
   ```

## Test Naming Convention
`test_[function]_[scenario]_[expected_result]`

Examples:
- `test_parse_reference_valid_book_chapter_verse`
- `test_parse_reference_invalid_returns_none`
- `test_generate_receipts_includes_all_fields`

## Coverage Target
Maintain ≥80% coverage
