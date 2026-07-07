# Security Policy

## Supported versions

This project is currently in active development as a Casper Agentic Buildathon 2026 submission. Only the latest version on the `main` branch is supported.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send an email to:

**ardayaesteban@gmail.com**

Include in your report:
- A description of the vulnerability
- Steps to reproduce it
- The potential impact
- Any suggested fix if you have one

You can expect an acknowledgment within 48 hours. We will keep you informed of the progress toward a fix.

## Scope

- Smart contract (`smart-contract/`) — Rust / Odra, deployed on Casper Testnet
- Agent (`agent/`) — Python autonomous agent and FastAPI server
- Frontend (`frontend/`) — React dashboard (static, no server-side logic)

## Out of scope

- Issues in third-party dependencies (report those to the respective projects)
- Issues that require physical access to the machine running the agent
- Social engineering attacks
