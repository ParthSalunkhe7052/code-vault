# CodeVault CLI

The official command-line interface for the CodeVault platform. Manage projects, licenses, and run builds locally or in the cloud.

## Installation

```bash
pip install codevault-cli
```

## Usage

```bash
codevault [COMMAND] [OPTIONS]
```

## Commands

### `login`
Authenticate with the CodeVault platform.

```bash
codevault login
```

### `build`
Compile your application with license protection.

```bash
# Build the project in the current directory
codevault build

# Build a specific project ID
codevault build <project_id>

# Build options
codevault build --fast          # Enable Fast Mode (directory output, no onefile)
codevault build --jobs 4        # Use 4 CPU cores for compilation
codevault build --license <key> # Embed a specific license key
```

**Build Modes:**
- **Standard (Default)**: Produces a single `.exe` file. Slower (~20 mins) but easier to distribute.
- **Fast Mode (`--fast`)**: Produces a directory. 3-4x faster. Best for testing.

### `projects`
List all your projects.

```bash
codevault projects
```

### `licenses`
Manage licenses for a project.

```bash
codevault licenses <project_id>
```

### `status`
Check your current login status and environment health (Nuitka/Pkg installation).

```bash
codevault status
```

## Local Development

If you are developing the CLI itself:

```bash
cd cli
pip install -e .
```
