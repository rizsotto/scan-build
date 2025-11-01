# Agent Contribution Guidelines

This document provides guidelines for AI agents contributing to the clanganalyzer project.

## Project Overview

**clanganalyzer** is a Python package that runs the Clang static analyzer against projects with existing compilation databases. It provides a simplified interface to the Clang static analyzer for C/C++ code analysis.

### Key Objectives
- Maintain a simple, focused tool for Clang static analysis
- Support modern Python (3.10+) with proper type annotations
- Keep the codebase clean and maintainable
- Provide reliable static analysis for C/C++ projects

## Architecture

### Current Structure
```
clanganalyzer/
├── __init__.py          # Common utilities and shared functions
├── analyze.py           # Main analysis logic and entry point
├── arguments.py         # Command-line argument parsing
├── clang.py             # Clang-specific functionality
├── compilation.py       # Compilation database handling
└── report.py            # Report generation and output formatting
```

### Design Principles
1. **Single Responsibility**: Each module has a clear, focused purpose
2. **Minimal Dependencies**: Keep external dependencies to a minimum
3. **Type Safety**: Use modern Python type annotations throughout
4. **Testability**: Write testable code with clear interfaces

## Code Standards

### Type Annotations
- Use modern Python 3.6+ function annotations: `def func(arg: str) -> int:`
- Avoid old comment-style annotations: `# type: (str) -> int`
- Import types from `typing` module when needed
- Use `Optional[T]` for nullable values
- Use `Union[T, U]` for multiple possible types

### Code Style
- Follow PEP 8 style guidelines
- Use `ruff` for linting and formatting
- Line length: 127 characters (configured in pyproject.toml)
- Use meaningful variable and function names
- Add docstrings for public functions and classes

### Error Handling
- Use specific exception types rather than generic `Exception`
- Provide meaningful error messages
- Log errors appropriately using the `logging` module
- Handle edge cases gracefully

## Common Tasks

### Adding New Features
1. **Identify the appropriate module** for your feature
2. **Write tests first** (TDD approach when possible)
3. **Add type annotations** to all new functions
4. **Update documentation** if the feature affects the API
5. **Run the full test suite** before submitting

### Refactoring Existing Code
1. **Understand the current behavior** by reading tests
2. **Add missing type annotations** during refactoring
3. **Simplify over-engineered patterns** where appropriate
4. **Maintain backward compatibility** for public APIs
5. **Update tests** to reflect any changes

### Bug Fixes
1. **Write a failing test** that reproduces the bug
2. **Fix the bug** with minimal changes
3. **Ensure the test passes** and no other tests break
4. **Add logging** if it helps with debugging similar issues

## Testing

### Test Structure
- Unit tests in `tests/unit/`
- Functional tests in `tests/functional/`
- Use `pytest` for test execution
- Aim for high test coverage (current target in config)

### Test Guidelines
- Write tests for both happy path and error cases
- Mock external dependencies (file system, subprocess calls)
- Use descriptive test method names
- Keep tests focused and independent

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=clanganalyzer

# Run specific test file
uv run pytest tests/unit/test_compilation.py
```

## Common Patterns

### Command Processing Chain
The analyzer uses a functional chain pattern for processing compilation commands:
```python
@require(['source', 'flags'])
def process_step(opts, continuation=next_step):
    # Process opts
    return continuation(opts)
```

### Error Reporting
Use the established logging patterns:
```python
import logging

logging.debug("Detailed information for debugging")
logging.info("General information")
logging.warning("Something unexpected happened")
logging.error("An error occurred")
```

### File Operations
Use context managers for file operations:
```python
with open(filename, 'r') as handle:
    content = handle.read()
```

## Legacy Cleanup

The project has been refactored from a multi-package structure (`libscanbuild`, `libear`) to a single `clanganalyzer` package. When working on the codebase:

1. **Remove references** to old packages in configuration files
2. **Simplify over-engineered patterns** that were needed for the previous multi-package structure
3. **Focus on the core functionality** of Clang static analysis
4. **Avoid adding complexity** unless it serves the single-purpose goal

## Tools and Commands

### Development Setup
```bash
# Install development dependencies
uv sync --all-extras

# Run linting
uv run ruff check .
uv run ruff format .

# Run type checking
uv run ty clanganalyzer

# Run tests
uv run pytest tests/unit
uv run lit -v tests
```

### Pre-commit Checklist
- [ ] Code follows style guidelines (`ruff check/format`)
- [ ] Type annotations are present and correct (`ty`)
- [ ] Tests pass (`pytest`)
- [ ] New functionality is tested
- [ ] Documentation is updated if needed

## Getting Help

1. **Read the existing code** to understand patterns and conventions
2. **Check the tests** to understand expected behavior
3. **Review the project history** in git to understand design decisions
4. **Look at similar functionality** in other parts of the codebase

## Anti-Patterns to Avoid

1. **Over-engineering**: Don't add flexibility that isn't needed
2. **Complex inheritance**: Prefer composition over deep inheritance
3. **Global state**: Avoid global variables and mutable state
4. **Implicit dependencies**: Make dependencies explicit and testable
5. **Comment-style type hints**: Use modern function annotations instead

## File-Specific Guidelines

### `analyze.py`
- Contains the main analysis pipeline and entry point
- Uses functional chain pattern for processing steps
- Each step should be independently testable

### `compilation.py`
- Handles compilation database parsing and processing
- Focus on correctness of compiler command parsing
- Handle edge cases in build system variations

### `arguments.py`
- Keep argument parsing simple and well-documented
- Validate arguments early and provide clear error messages
- Use argparse best practices

### `clang.py`
- Interface with Clang static analyzer
- Handle different Clang versions gracefully
- Provide clear error messages for Clang-related issues

### `report.py`
- Generate analysis reports in various formats
- Keep report generation separate from analysis logic
- Support both human-readable and machine-readable outputs

Remember: This project aims to be a simple, reliable tool for Clang static analysis. Keep changes focused on that goal and avoid unnecessary complexity.