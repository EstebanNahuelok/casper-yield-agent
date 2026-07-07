# Contributing to Casper Yield Agent

Thank you for your interest in contributing! This project was built for the Casper Agentic Buildathon 2026.

## How to contribute

### Reporting bugs

Open an issue on GitHub with:
- A clear description of the bug
- Steps to reproduce it
- Expected vs actual behavior
- Logs or screenshots if relevant

### Suggesting features

Open an issue with the `enhancement` label describing the feature and why it would be useful.

### Submitting code

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the structure below
4. Test your changes locally
5. Open a Pull Request with a clear description of what you changed and why

## Project structure

```
casper-yield-agent/
├── smart-contract/   # Rust / Odra smart contract (YieldVault)
├── agent/            # Python autonomous agent + FastAPI
└── frontend/         # React / TypeScript dashboard
```

## Development setup

See the [README](README.md) for full setup instructions.

### Smart contract (Rust / Odra)

```bash
cd smart-contract
cargo odra test          # run tests
cargo odra build -b casper  # build WASM
```

### Agent (Python)

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r agent\requirements.txt
cd agent && python main.py
```

### Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

## Code style

- **Rust**: standard `cargo fmt` formatting
- **Python**: `ruff` linter, line-length 100, target py312
- **TypeScript**: ESLint with the project's existing config

## Questions

Open an issue or reach out via the contacts listed in the README.
