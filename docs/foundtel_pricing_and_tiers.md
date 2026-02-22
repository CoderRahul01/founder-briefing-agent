# Foundtel Pricing & Tier Strategy

## Market Context & Positioning

At $8/month, Foundtel is positioned as a highly accessible, high-ROI tool for founders.
The goal of the Free Tier is to demonstrate undeniable value (the "Aha!" moment of waking up to a personalized brief) while creating natural friction points that make the $8/month upgrade an easy, impulse-driven decision.

---

## 1. Feature Breakdown: Free (Solo) vs. Pro (Founder)

### Free Tier (Solo)

**Goal:** Hook the user with the core value proposition (the morning brief).
**Limitations:** Restrict frequency, depth, and customization.

- **Daily Briefs:** 1x Automated Brief per day (Morning only).
- **Manual Triggers:** Limited (e.g., 1 manual trigger per week) to test the system.
- **Competitor Radar:** Basic tracking (Up to 3 competitors maximum). Deep-dive competitor analysis is disabled.
- **Email Analysis:** Scans the last 24 hours only. Limited to top 10 most important emails.
- **Delivery Methods:** Dashboard only (or single Email delivery). No WhatsApp.
- **A2A Integration:** Basic identity exposure. Cannot be triggered by other agents for advanced workflows.

### Pro Tier (Founder) - $8/Month

**Goal:** Unlock the full power of the Chief of Staff agent for continuous operation.
**Capabilities:** Unrestricted, deep insights, and multi-channel delivery.

- **Daily Briefs:** Unlimited automated briefs (Morning, Evening wrap-ups).
- **Manual Triggers:** Unlimited manual "Generate Brief Now" triggers.
- **Competitor Radar:** Unlimited competitors + Deep-dive strategic analysis (unlocks the full `competitor_agent` capabilities).
- **Email Analysis:** Deep historical scanning, infinite priority sorting.
- **Delivery Methods:** Dashboard, Email, AND WhatsApp integration.
- **A2A Integration:** Full API access. Foundtel can be triggered by your other internal agents for revenue or competitor data via the A2A protocol.

---

## 2. Technical Implementation: Guardrails

To enforce these tiers, we must implement robust guardrails at the API and Service layers.

### A. Database Model Updates (`founder_agent/db/models.py`)

We already added the `plan` field (`solo`, `founder`, `team`).

### B. Route-Level Guardrails (`app.py`)

1.  **Manual Triggers (`/trigger-briefs-now`):**
    - _Implementation:_ Check `user.plan`. If `solo`, query `AuditLog` for triggers in the last 7 days. If count > 0, return an error and prompt upgrade.
2.  **Settings Page (`/settings`):**
    - _Implementation:_ If `user.plan == 'solo'` and the user tries to save > 3 competitors, truncate the list and display a warning toast indicating the Pro requirement.
    - _Implementation:_ Disable the WhatsApp number input field for `solo` users entirely.

### C. Agent-Level Guardrails (`founder_agent/agent.py`)

1.  **Competitor Sub-Agent Logic:**
    - _Implementation:_ In `root_agent` instruction or context mapping, pass the `user.plan`.
    - If `solo`, instruct the model to provide a _surface-level_ summary of competitors.
    - If `founder`, instruct the model to run a deep strategic analysis.
2.  **A2A Exposure (`founder_agent/a2a_exposure.py`):**
    - _Implementation:_ As already implemented, block advanced skills (like `competitor_radar`) if the requesting user's context resolves to a `solo` plan.

### D. Audit Logging (`AuditLog`)

- Every guarded action (successful or blocked) must be logged to the `AuditLog`.
- _Event Types:_ `trigger_manual_brief`, `trigger_a2a_competitor`, `upgrade_prompt_shown`.

---

## Conclusion

This architecture ensures the Free tier remains operational and valuable, but explicitly caps system resources and advanced AI reasoning capabilities until the user pays the $8/month subscription.
