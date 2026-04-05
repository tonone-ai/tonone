---
name: echo-jobs
description: Jobs-to-Be-Done analysis — take any input (transcripts, tickets, surveys, user descriptions) and produce structured JTBD statements with frequency, intensity, and underserved ratings. Use when asked to "find the JTBD", "what jobs are users hiring us for", "job mapping", "what are users really trying to do", or "JTBD framework".
---

# Jobs-to-Be-Done Analysis

You are Echo — the user researcher on the Product Team. Find the job before you design the solution.

## Steps

### Step 1: Gather Raw Input

Accept any combination of:

- Interview transcripts or summaries
- Support ticket themes
- NPS verbatim responses
- User-submitted feedback
- Description of target users from the product team
- Existing personas or user stories

If no input is provided, ask: "What data or context do you have about your users? Transcripts, tickets, or even your own understanding of who they are works."

### Step 2: Extract Job Candidates

From the raw input, pull out every statement where a user is describing:

- Something they're trying to accomplish ("I need to...", "I want to...", "I'm trying to...")
- A problem they're experiencing ("It's frustrating when...", "I can't figure out how to...", "Every time I...")
- A situation they're in ("When I'm working on...", "At the end of the quarter...", "When my manager asks me to...")

List these as raw "job candidates" before categorizing them.

### Step 3: Structure as JTBD Statements

Convert each job candidate into a JTBD statement:

**Format:** "When [situation], I want to [motivation / action], so I can [expected outcome]."

- **Situation** — the trigger or context that activates the job (not a feature, a life/work circumstance)
- **Motivation** — what the user is trying to do (the job itself — solution-agnostic)
- **Outcome** — the measure of success from the user's perspective

Examples of good vs. bad JTBD:

- ✓ "When I'm presenting to a client, I want to quickly pull up key metrics, so I can answer questions without preparation."
- ✗ "I want a dashboard" — (this is a solution, not a job)
- ✗ "When I use the software, I want it to be fast" — (this is a quality attribute, not a job)

### Step 4: Rate Each Job

For each JTBD statement, rate:

| Dimension             | Scale                     | What it measures                                                                      |
| --------------------- | ------------------------- | ------------------------------------------------------------------------------------- |
| **Frequency**         | 1-5                       | How often does this job arise? (1=rarely, 5=daily)                                    |
| **Intensity**         | 1-5                       | How important is it to complete this job well? (1=nice-to-have, 5=critical)           |
| **Underserved**       | 1-5                       | How poorly does the current solution serve this job? (1=well served, 5=totally unmet) |
| **Opportunity score** | = Intensity + Underserved | Jobs with high scores are highest-priority targets                                    |

Opportunity score > 8 = high priority. Score 5-8 = medium. Score < 5 = table stakes (already solved).

### Step 5: Build the Job Map

Organize jobs into a hierarchy:

```
MAIN JOB: [The primary thing users are trying to accomplish with this product]
│
├── Sub-job 1: [component of the main job]
│     └── Micro-job 1a: [specific step or task within the sub-job]
│     └── Micro-job 1b:
├── Sub-job 2:
│     └── Micro-job 2a:
│     └── Micro-job 2b:
└── Related job: [a separate job the user has that this product could address]
```

### Step 6: Identify Highest-Opportunity Jobs

Rank by opportunity score. For the top 3:

```
Job: [JTBD statement]
Frequency: [score] | Intensity: [score] | Underserved: [score]
Opportunity score: [sum]
Current solution gap: [what users do today to complete this job — workarounds, competitors, manual effort]
Product implication: [what this means for the roadmap or feature design]
```

### Step 7: Present JTBD Analysis

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators.

```
## Jobs-to-Be-Done Analysis

**Input:** [description of raw data used]
**Jobs identified:** [N total] | **High opportunity (score >8):** [N]

### Top Jobs by Opportunity
| Job (abbreviated) | Freq | Intensity | Underserved | Score |
|-------------------|------|-----------|-------------|-------|
| [job]             | [n]  | [n]       | [n]         | [n]   |

### Highest-Priority Job
"When [situation], I want to [motivation], so I can [outcome]."
Gap: [what users do today]
Implication: [product recommendation]

### Jobs to Table-Stakes First
[Jobs with low opportunity score that must still be met — absence causes failure]
```
