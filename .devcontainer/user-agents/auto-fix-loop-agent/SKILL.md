---
name: auto-fix-loop-agent
description: Automatically detects errors, fixes them in a loop without waiting for manual commands, and confirms when done
triggers:
  - loop perbaiki otomatis
  - auto fix loop
  - perbaiki tanpa menunggu perintah
  - error recovery loop
license: MIT
---

## What I do

When an error occurs during execution, I automatically enter a recovery loop:
1. Detect the error and capture full context
2. Diagnose root cause
3. Apply the fix
4. Re-run the failed operation
5. Loop until success or fatal termination

No manual "lakukan" or "lanjutkan" needed — I keep going until the task is done or I hit a blocker I cannot resolve.

## How to invoke

```
/skill auto-fix-loop-agent
```

Or the loop activates automatically when a task fails and the prompt implies persistence (e.g., "loop perbaiki", "otomatis perbaiki", "jangan berhenti sampai selesai").

## Loop protocol

### Step 1: Capture Error
- Read the full error message, stack trace, and surrounding context
- Snapshot the state before any changes
- Log: `🔄 Error detected: <error message>`

### Step 2: Diagnose
- Classify the error type:
  - `syntax` → code mistake
  - `runtime` → logic/environment issue
  - `data` → integrity or schema violation
  - `network` → timeout, connection refused
  - `permission` → access denied, missing auth
- Identify the exact file, line, and operation
- Log: `🔍 Diagnosis: <root cause>`

### Step 3: Fix & Retry
- Apply the minimal fix needed
- Re-run the exact same operation that failed
- If success: log `✅ Fixed: <what was done>` and continue
- If fail again: log `❌ Attempt N failed: <reason>` and retry up to 3x

### Step 4: Escalation
- If 3 attempts all fail, escalate:
  - Summarize all attempts and results
  - Ask user for guidance
  - Do NOT infinite loop without user input

## Output format

```
🔄 Auto-Fix Loop Active
━━━━━━━━━━━━━━━━━━━━
❌ [1/3] Error: duplicate key violation
🔍 Diagnosis: Siswa "Budi" already exists
✅ [1/3] Fixed: renamed to "Budi Santoso", retrying...
✅ Operation completed successfully

Summary: 1 error found, 1 fixed, 0 escalated
```

## Key rules
- **MAX 3 retries** per error — no infinite loops
- **ALWAYS** log every attempt with clear status
- **NEVER** fix without understanding root cause
- **ALWAYS** show summary when loop ends
- If stuck, present options: retry with different approach, skip, or abort
