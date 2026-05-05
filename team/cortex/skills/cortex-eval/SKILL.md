---
name: cortex-eval
description: Evaluate model performance — check for accuracy drops, data drift, and error patterns. Use when asked about "model accuracy dropped", "evaluate the model", "check for drift", or "model performance".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task, TodoWrite, AskUserQuestion
version: 0.9.8
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# Evaluate Model Performance

You are Cortex — the ML/AI engineer on the Engineering Team.

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

## Steps

### Step 0: Run Static Analysis

Before any LLM-based evaluation, run the static analysis scanner to find LLM usage anti-patterns and prompt quality issues:

```bash
# From the project root (or team/cortex/scripts/)
python team/cortex/scripts/cortex_agent/eval_scan.py . --out .reports/cortex-eval-latest.json
```

Or with selective scans:
```bash
# LLM usage only (finds missing error handling, unbounded costs, hardcoded models)
python team/cortex/scripts/cortex_agent/eval_scan.py . --skip-prompts

# Prompt evaluation only (finds injection risks, length issues, missing format instructions)
python team/cortex/scripts/cortex_agent/eval_scan.py . --skip-usage
```

Review the JSON report at `.reports/cortex-eval-<ts>.json`. Exit code 2 means HIGH or CRITICAL findings exist — these should be addressed before continuing.

### Step 1: Detect ML Environment

Scan the project to understand the ML stack and current model:

```bash
# Check for model artifacts, training scripts, metrics logs
ls -la model* *.pkl *.joblib *.onnx *.pt *.h5 2>/dev/null
ls -la train* evaluate* metrics* 2>/dev/null
cat requirements.txt 2>/dev/null | grep -iE "sklearn|torch|tensorflow|xgboost|lightgbm|mlflow|wandb"
cat pyproject.toml 2>/dev/null | grep -iE "sklearn|torch|tensorflow|xgboost|lightgbm|mlflow|wandb"

# Check for experiment tracking
ls -la mlruns/ wandb/ .neptune/ 2>/dev/null
grep -rl "mlflow\|wandb\|neptune" --include="*.py" . 2>/dev/null | head -10

# Check for monitoring/metrics
ls -la metrics/ logs/ monitoring/ 2>/dev/null
```

Note the ML framework, model type, experiment tracking system, and any existing metrics. If nothing is detected, ask the user.

### Step 2: Current Model Metrics vs Baseline

Establish where things stand:

- **Find the baseline metrics** — check experiment tracking (MLflow, W&B), saved metrics files, or training logs
- **Compute current metrics** — run evaluation on the latest data with the deployed model
- **Compare:** is the model performing worse than baseline? By how much?
- **Segment the comparison** — overall metrics can hide problems (model is fine on segment A, broken on segment B)

Report:

```
| Metric    | Baseline | Current | Delta  |
|-----------|----------|---------|--------|
| [metric]  | [value]  | [value] | [+/-]  |
```

### Step 3: Data Distribution Shift (Feature Drift)

Check if the input data has changed:

- **Feature distributions:** compare training data distributions vs recent production data
- **Statistical tests:** KS test, PSI (Population Stability Index), or simple histogram comparison
- **New categories:** are there categorical values in production that weren't in training?
- **Missing data patterns:** has the rate of nulls/missing values changed?
- **Volume changes:** is the prediction volume significantly different?

Flag any feature where the distribution has shifted significantly.

### Step 4: Prediction Distribution Changes

Check if the model's outputs have changed:

- **Prediction distribution:** compare historical prediction distribution vs recent
- **Confidence distribution:** is the model becoming less confident? More confident on wrong answers?
- **Class balance shift:** for classification, has the predicted class balance changed?
- **Output range shift:** for regression, has the output range moved?

If predictions shifted but features didn't, the problem is likely in the model or feature pipeline, not the data.

### Step 5: Error Analysis

Dig into what the model is getting wrong:

- **Worst predictions:** find the examples with the largest errors or highest-confidence wrong answers
- **Error patterns:** group errors by feature segments — is the model failing on a specific cohort?
- **New error patterns:** what is the model getting wrong now that it wasn't before?
- **Confusion matrix diff:** for classification, compare current vs baseline confusion matrix
- **Feature importance shift:** have the most important features changed?

### Step 6: Identify Root Cause

Based on the evidence from Steps 1-4, determine the root cause:

- **Bad data:** new data source, schema change, data pipeline bug, missing values
- **Concept drift:** the real-world relationship between features and target has changed
- **Feature pipeline change:** a feature is being computed differently in serving vs training
- **Training/serving skew:** features look different at training time vs inference time
- **Upstream dependency change:** a service or data source the model depends on changed
- **Volume/distribution shift:** the model is seeing a population it wasn't trained on

### Step 7: Recommend Fix

Based on root cause, recommend the appropriate fix:

- **Bad data:** fix the data pipeline, backfill, retrain on clean data
- **Concept drift:** retrain on recent data, consider online learning or more frequent retraining
- **Feature pipeline bug:** fix the pipeline, verify training/serving parity, retrain if contaminated
- **Training/serving skew:** align pipelines, add integration tests between train and serve
- **Model rollback:** if the current model is worse and the previous version was fine, rollback while investigating

Present a summary:

```
## Model Evaluation Report

**Model:** [name/version] | **Status:** [healthy/degraded/broken]

### Metrics Comparison
| Metric | Baseline | Current | Delta |
|--------|----------|---------|-------|
| [metric] | [value] | [value] | [+/-] |

### Root Cause
[One-line root cause]

### Evidence
- [Finding 1]
- [Finding 2]
- [Finding 3]

### Recommended Fix
1. [Immediate action]
2. [Follow-up action]
3. [Prevention measure]

### Drift Summary
- Feature drift: [none/low/moderate/severe]
- Prediction drift: [none/low/moderate/severe]
- Error pattern: [description]
```

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, top 3 findings, and the report path. Never dump analysis to CLI.
