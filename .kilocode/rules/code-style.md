# Code Style Rules

Reference: `conductor/code_styleguides/`

## Python Style Guide

Based on Google Python Style Guide.

### Naming Conventions
- Modules: `snake_case`
- Classes: `PascalCase`
- Functions/Methods: `snake_case`
- Constants: `ALL_CAPS_WITH_UNDERSCORES`
- Internal members: `_leading_underscore`

### Code Formatting
- Line length: Maximum 80 characters
- Indentation: 4 spaces (no tabs)
- Imports: Separate lines, grouped (stdlib, third-party, local)

### Documentation
- Use triple double quotes: `"""docstring"""`
- All public modules, functions, classes, methods require docstrings
- Include `Args:`, `Returns:`, `Raises:` sections

### Type Hints
- Required for all public APIs
- Use `typing` module for complex types

### Linting
Run `ruff check .` before committing.

## TypeScript/React Style Guide

### Naming Conventions
- Components: `PascalCase`
- Files: `PascalCase.tsx` for components
- Hooks: `useCamelCase`
- Utilities: `camelCase`

### Component Patterns
- Use functional components with hooks
- Keep components under 200 lines
- Extract reusable logic to custom hooks

### Styling
- Use Tailwind CSS utility classes
- Follow existing design system
- Dark mode is primary aesthetic

## General Principles

1. **Be Consistent** - Match existing code style
2. **Readability First** - Code is read more than written
3. **DRY** - Don't Repeat Yourself
4. **Single Responsibility** - One purpose per module/function
