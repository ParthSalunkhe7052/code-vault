# CodeVault CLI: Seller Toolkit

The official command-line interface for the CodeVault Marketplace. Build, protect, and sell your software from the terminal.

## Installation

```bash
pip install codevault-cli
```

## Seller Workflow

### `publish`
Compile your project and push it to the CodeVault Marketplace.

```bash
# Publish the current project
codevault publish

# Publish with specific version note
codevault publish --message "Fixed login bug"

# Set/Update price during publish
codevault publish --price 29.99
```

### `earnings`
Check your sales performance and payout status.

```bash
codevault earnings
```
*Output:*
```text
Total Sales:    $1,240.00
Net Revenue:    $1,054.00
Next Payout:    Friday, Oct 24th
```

## Utility Commands

### `init`
Initialize a new product in the current directory.

```bash
codevault init --name "My Tool" --type python
```

### `build`
Run a local test build (does not publish to store).

```bash
codevault build --local
```

### `login`
Authenticate with your CodeVault account.

```bash
codevault login
```