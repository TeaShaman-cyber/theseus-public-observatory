# Security Policy

## Public Data Only

This repository must not contain:

- API keys, tokens, passwords, cookies, or private headers;
- local machine telemetry;
- account usage limits;
- private chat logs;
- AutoMem, MemPalace, or Theseus private-lab exports;
- backup archives or database dumps.

## Workflow Rules

- GitHub Actions use public HTTP endpoints only.
- Workflows do not require repository secrets.
- Reports must avoid causal claims and should describe only observed public
  source state.
- If a source starts requiring authentication, remove it from the public
  collector until reviewed.

## Reporting

Open a GitHub issue for suspected data leaks or incorrect public-data handling.
