# Status Matrix

Governance authority for component and work-package state. It owns only the two exact state sets and their transition semantics.

No state labels or transitions exist beyond those defined below.

## Component State Machine

Components track implementation health through a staged lifecycle. Each component carries exactly one state at all times.

### States

| State | Meaning |
|---|---|
| UNKNOWN | Not yet audited; no evidence collected |
| AUDITED | Evidence collected; state and risks are documented |
| BROKEN | Known defects prevent basic function |
| PARTIAL | Subset of responsibilities is functional; known gaps remain |
| FUNCTIONAL | All responsibilities verified as working |
| TESTED | Automated test coverage exists for all responsibilities |
| STABLE | No regressions across multiple release cycles |
| FROZEN | Design closed; no further changes permitted without approved reopening exception |

### Normal Progression

```
UNKNOWN → AUDITED → FUNCTIONAL → TESTED → STABLE → FROZEN
```

### Exceptional States

- **BROKEN**: component has known defects that prevent basic function. Recovery path is `BROKEN → FUNCTIONAL` only — a BROKEN component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.
- **PARTIAL**: subset of responsibilities is functional; known gaps remain. Recovery path is `PARTIAL → FUNCTIONAL` only — a PARTIAL component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.

Recovery from BROKEN or PARTIAL requires: (a) remediation passes all functional criteria, (b) evidence is recorded, and (c) the transition is explicitly reviewed.

### Evidence Required per Transition

| Transition | Evidence |
|---|---|
| UNKNOWN → AUDITED | Audit report: current state, known risks, dependencies |
| AUDITED → FUNCTIONAL | Functional criteria met; manual or automated verification |
| FUNCTIONAL → TESTED | Automated test suite passes; coverage meets phase threshold |
| TESTED → STABLE | No regressions across ≥2 release cycles |
| STABLE → FROZEN | Approved freeze decision; no open P0/P1 |
| BROKEN → FUNCTIONAL | Remediation passes; all functional criteria re-verified |
| PARTIAL → FUNCTIONAL | Remaining gaps closed; all responsibilities verified |

## Work-Package State Machine

Work packages (WPs) track deliverable progress through the SDD pipeline. Each WP carries exactly one state and, when BLOCKED, records its prior state for correct resumption.

### States

| State | Meaning |
|---|---|
| BACKLOG | Captured but not yet ready for execution |
| READY | Admitted for execution by the readiness authority |
| IN_PROGRESS | Active development |
| REVIEW | Under review (code, design, or architecture) |
| VERIFY | Acceptance criteria being verified |
| BLOCKED | Cannot proceed; prior state recorded |
| DONE | Accepted by the completion authority and delivered |
| DEFERRED | Intentionally postponed with rationale |

### Normal Flow

```
BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
```

### Blocking Rules

READY, IN_PROGRESS, REVIEW, and VERIFY MAY enter BLOCKED when a dependency or obstacle prevents progress. BLOCKED MUST record the immediately prior active state; no other state may enter BLOCKED.

Resumption restores the recorded prior state:

Each route below is a suspension and restoration path, not a fresh progression:

- `READY → BLOCKED` resumes as `READY`
- `IN_PROGRESS → BLOCKED` resumes as `IN_PROGRESS`
- `REVIEW → BLOCKED` resumes as `REVIEW`
- `VERIFY → BLOCKED` resumes as `VERIFY`

### Deferral Rules

Only these states MAY enter DEFERRED, each with a recorded rationale:

- `BACKLOG → DEFERRED`
- `READY → DEFERRED`
- `BLOCKED → DEFERRED`

`DEFERRED → BACKLOG` SHALL occur only after an approved scope change. Otherwise the item remains DEFERRED or is permanently retired.
These rules are exhaustive for work-package interruption and deferral.
