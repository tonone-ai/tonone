# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Tonone, please report it responsibly.

**Do not open a public issue.**

Email: **<security@tonone.ai>**

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to provide a fix or mitigation within 7 days for critical issues.

## Scope

Tonone is a prompt-based agent system — agents execute through Claude Code, not through arbitrary code execution. The primary security surface is:

- **Skill definitions** — prompts that instruct Claude Code behavior
- **Hook scripts** — shell scripts that run on install (`setup.sh`)
- **Plugin manifests** — JSON configuration files

If you find a way that a skill prompt could be manipulated to produce harmful Claude Code behavior, that's in scope.
