---
name: plan-validator
description: Reads Plan.md or PRD and verifies that implementation matches documented requirements
triggers:
  - baca plan
  - cocokkan dengan plan
  - validasi implementasi
  - cek kesesuaian plan
  - sudah sesuai plan
license: MIT
---

## What I do

Reads your Plan.md (or other specification files) and cross-checks every requirement against the actual implementation. I identify gaps, deviations, and unimplemented features so nothing gets missed.

## How to invoke

```
/skill plan-validator
```

Or trigger with: "baca plan.md", "apakah sudah sesuai plan?", "cocokkan dengan plan".

## Validation protocol

### Phase 1: Parse the Plan
1. Locate Plan.md or specified document in the project root
2. Extract all requirements, features, and acceptance criteria
3. Organize into checklist: `[ ] unimplemented`, `[~] partial`, `[x] done`
4. Identify priority markers (Must-have, Should-have, Nice-to-have)

### Phase 2: Scan Implementation
1. Search the codebase for each feature's implementation
2. Check routes, handlers, models, and tests
3. For each requirement, determine status:
   - `✅ Complete` — fully implemented and tested
   - `⚠️ Partial` — partially implemented or has bugs
   - `❌ Missing` — not implemented at all
   - `📝 Not in Plan` — found in code but not in spec

### Phase 3: Report Gaps
1. List all missing features with severity
2. List all partial implementations with specifics
3. List extra features not in plan
4. Provide estimated effort to complete each gap

## Output format

```
📋 Plan Validation Report
━━━━━━━━━━━━━━━━━━━━━━━━
📄 Source: Plan.md (12 requirements found)

✅ Complete (6/12)
  [x] Student registration
  [x] Payment recording
  [x] Data display
  [x] Search by name
  [x] Delete student
  [x] Google Sheets sync

⚠️ Partial (2/12)
  [~] Payment receipt (no PDF generation)
  [~] Auto-backup (runs but no notification)

❌ Missing (4/12)
  [ ] Monthly report
  [ ] Export to Excel
  [ ] Multi-user login
  [ ] Audit log

📝 Extra (1 found)
  [+] Dark mode display — not in original spec

Recommendation: focus on ❌ Missing items first (Must-have)
```

## Key rules
- **ALWAYS** read the actual Plan.md file, not memory
- **NEVER** mark as done if only partially implemented
- **ALWAYS** show exact line references for each finding
- If no Plan.md exists, ask user to point to the spec file
- Present findings in priority order (Must-have first)
