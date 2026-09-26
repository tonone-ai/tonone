# tonone-core

An engineering team for Claude Code. Fifteen specialist agents and 80 skills, led by **Apex**, the engineering lead, which scopes each request and routes it to the right specialists.

This is the core of [tonone](https://github.com/tonone-ai/tonone). The full plugin adds product, design, legal, operations, data science, security operations, developer experience, infrastructure and AI operations teams (100 agents, 429 skills).

## What you get

| Agent  | Owns                                                                                                  |
| ------ | ----------------------------------------------------------------------------------------------------- |
| Apex   | Engineering lead: scopes work into S/M/L options with token and cost estimates, routes to specialists |
| Forge  | Cloud infrastructure, networking, IaC, cost                                                           |
| Relay  | CI/CD, deployments, GitOps                                                                            |
| Spine  | Backend APIs, system design, performance                                                              |
| Flux   | Databases, migrations, data pipelines                                                                 |
| Warden | Security: IAM, secrets, threat modeling, hardening                                                    |
| Vigil  | Observability, alerting, SLOs, incident response                                                      |
| Prism  | Frontend UI and internal tools                                                                        |
| Cortex | ML and LLM integration, prompts, evals                                                                |
| Touch  | iOS, Android and cross-platform mobile                                                                |
| Volt   | Embedded, firmware, IoT                                                                               |
| Atlas  | Architecture docs, ADRs, diagrams, onboarding                                                         |
| Lens   | Dashboards, metrics, reporting                                                                        |
| Proof  | Test strategy, E2E and integration tests                                                              |
| Pave   | Developer experience, golden paths, service catalogs                                                  |

Every specialist has three kinds of skill: **build** (`/forge-infra`, `/spine-api`), **review** (`/warden-audit`, `/relay-audit`) and **recon** (`/forge-recon`, `/apex-takeover`) for getting oriented in an unfamiliar codebase.

## Usage

```text
> /apex-plan Add SSO to our admin dashboard
> /warden-audit Run a security audit on this repo
> /apex-takeover Get me oriented in this codebase
```

Or just describe the task and let Apex pick the specialists.

## Privacy and data

tonone-core is markdown only: agent prompts and skill workflows that Claude Code reads. It has no hooks, no server, no telemetry and makes no network requests of its own. Skills run inside Claude Code and follow its data handling. Any command a skill runs, such as a security scanner, goes through Claude Code's normal permission prompts.

## License

MIT. Source and issues: https://github.com/tonone-ai/tonone
