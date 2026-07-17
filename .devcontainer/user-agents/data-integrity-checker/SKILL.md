---
name: data-integrity-checker
description: Validates data integrity before any CRUD operation to ensure accuracy, consistency, and no duplication
triggers:
  - cek integritas data
  - validasi data sebelum simpan
  - check data integrity
  - filter data akurat
license: MIT
---

## What I do

Before any Create, Read, Update, or Delete operation, I scan the existing data and the incoming request to catch:
- Duplicate entries (same name, same ID, same unique key)
- Data type mismatches (string vs number, wrong format)
- Missing required fields
- Inconsistent references (e.g., student ID that doesn't exist)
- Boundary violations (negative amounts, unrealistic values)
- Cross-table integrity (payment > total owed, orphaned records)

## How to invoke

```
/skill data-integrity-checker
```

Or trigger automatically by including phrases like "cek integritas data", "validasi", or "filter data akurat" in your request.

## Integrity check protocol

### Phase 1: Schema Validation
1. Identify all required fields for the target entity
2. Check types: string, number, boolean, date
3. Validate format: phone numbers, emails, dates, currency
4. Reject empty/null required fields immediately

### Phase 2: Duplicate Detection
1. Search existing records for matching unique keys
2. Fuzzy match names (case-insensitive, typo-tolerant)
3. Flag near-duplicates for manual confirmation
4. Block exact duplicates automatically

### Phase 3: Referential Integrity
1. If linking to another entity, verify the target exists
2. Check for orphaned references before delete
3. Ensure cascade operations won't break relationships

### Phase 4: Business Rule Validation
1. Check monetary values: payment <= total bill, no negative
2. Check dates: end > start, not in far past/future
3. Apply domain-specific rules from context

## Output format

```
🔍 Integrity Check Report
━━━━━━━━━━━━━━━━━━━━━━━
✅ Schema: all fields valid
❌ Duplicate: "Budi Santoso" already exists (ID: #12)
❌ Referential: Siswa ID #99 not found
✅ Business rules: passed

Summary: 1 passed, 2 failed — blocking operation
```

## Key rules
- **ALWAYS** run before write operations (create, update, delete)
- **NEVER** skip validation even if confident
- **ALWAYS** show clear error messages with exact field names
- If data is clean, confirm "✅ Integrity check passed" and proceed
- If issues found, present them with suggested fixes and ask before proceeding
