# Inventory and planning coverage

Backlog opens on Inventory, with separate Home and Work views. Projects/sessions, actionable tasks and fixed events are distinct records. The owner can search, filter, prioritize, reclassify, park and review completion. New project discoveries wait for a concrete next action and finish line before creating a schedulable task.

Source snapshots report their scope, time, count and checked/partial/unavailable/not-connected status. Checked means an enumeration succeeded within that scope, not that every external account was connected or outcomes were verified. Missing records are never silently marked complete. Source/device identities are stable; same-title projects are not automatically merged. Within one device, an exact path can join a saved-project catalogue entry and a Codex database working directory.

The companion opts into `inventoryAllCodex`, `inventoryContext` and `coworkSessionsFolder` in its private configuration. Both collections read metadata, not conversation contents. Browser ticket and calendar collection is separate. Device uploads cannot change the owner's sorting or mark work finished.

All open task envelopes are supplied to background ranking without a first-30 cutoff. Project records awaiting review are visible in Inventory but are not actionable task envelopes. Ranking remains subject to the existing model budget and may be unavailable; an old ranking is not proof of current model review. The rule scheduler considers open tasks, uses deadlines and priority, and respects work/personal windows. An interactive draft remains a separate explicit plan operation.

Parking a task releases its unstarted reservations. Parking a project also parks its unfinished linked tasks. Reclassifying a project moves its unfinished tasks and releases reservations in the old context; completed and active history is preserved. Unparking a project returns it to review; choose its next actionable task explicitly.
