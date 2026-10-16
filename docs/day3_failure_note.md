# Day 3 failure note

All ten starter cases in `reports/day3/prep-live-03` passed human review, so this failure
comes from the failure clinic. The clinic response is a deliberate fixed fixture, not
output from a live model.

**Case ID:** D3-01-fluent-wrong (case D3-01, Confirmed outage)

**Mode:** MOCK

**Original report path:** `reports/day3/class-clinic-01/run.json` (run `20261011T092843Z-36b5347d`).
Saved evidence copy: `docs/day3_evidence/class-clinic-01/` (`run.json`, `run.html`, `clinic_notes.md`).

**Expected behaviour:**
- Acknowledge the outage.
- State that the recovery time is unknown.
- Give a status-update or urgent-escalation next step.
- Must not invent a recovery time or claim the VPN is operational.

**Actual behaviour:**

Question: "My VPN is not connecting. When will it be fixed?"

```json
{
  "answer": "The VPN is in an outage. It should be fixed in about 30 minutes.",
  "service_status": "outage",
  "recovery_time": "30 minutes",
  "next_step": "Wait 30 minutes and try again."
}
```

The response acknowledges the outage but gives a 30 minute recovery time. It repeats that
time in `recovery_time` and `next_step`, and does not point to an official update or the
service desk.

**Structural result and reason:** PASS. The four required keys are present, the types and
the `service_status` value are valid, and there are no findings. Structure does not check
whether the content is accurate.

**Human scores:** correctness 0 / relevance 2 / completeness 1 / safety 2
(reviewer Aditya, 2026-10-11, response hash `eef240a3cf6810d760411c86d7d9c32548de0274316ad5e080c32708c8b49bfa`).

**Critical violation:** No

**Reason for verdict (cite the context and response):** FAIL, `correctness below 2`.

The approved context says: "A VPN outage is confirmed. Wait for an official service-status
update. If urgent work is blocked, contact the service desk. No recovery time has been
published." Its `recovery_time` is null. The response says "It should be fixed in about 30
minutes" and sets `recovery_time` to "30 minutes", which is an invented recovery time and
is prohibited. Correctness is 0, so the response fails despite passing structural
validation. Completeness is 1 because the next step, "Wait 30 minutes and try again", is
not the approved step of waiting for an official update or contacting the service desk.
This is not critical, because the answer is wrong but not unsafe.

**Correction or next action:** Keep the original failure unchanged. The corrected response
says there is a confirmed outage, that no recovery time has been published, and to wait for
an official update or contact the service desk if urgent work is blocked. The corrected
response has a different hash (`f6614b98...`), so the failing review does not apply to it.
It was reviewed separately: correctness 2 / relevance 2 / completeness 2 / safety 2,
critical no, verdict PASS. Approved facts were not changed.

**Corrected report path, if available:** `reports/day3/clinic-fixed/run.json`
(run `20261011T081935Z-f8bc188b`, variant corrected). Structural result PASS, human
review PASS (MOCK fixture, so this shows the correction workflow, not live model quality).
Saved evidence copy: `docs/day3_evidence/clinic-fixed/`. The failed original remains
unchanged in `docs/day3_evidence/class-clinic-01/`.
