# What Clara considers

Backlog shows every known task that has not been marked finished. Views separate work needing more reserved time, fully scheduled work, parked work and all unfinished work. A task with only part of its estimated time reserved stays visible in Needs time. Expired or skipped blocks do not count as future reservations.

Completeness means coverage of Clara's current task store, not proof that every commitment in the owner's life has been captured. Unconnected accounts, uncaptured conversations and ambiguous messages can leave gaps. Draft suggestions remain separate until accepted. Source references and timestamps support review of accuracy; explicit owner decisions and scheduling constraints support validity.

## Priority as one input

The scheduler uses an additive score, exposed per task:

| Factor | Points |
| --- | --- |
| Owner priority | Low 10, medium 20, high 30 |
| Due date | Overdue 45; within two days 40; within seven days 25 |
| Preparation task | 20 |
| Project finishing step | 5 |
| Latest Codex recommendation | 15 for the first ranked task, decreasing to a minimum of 1 |

Higher score is considered first. Ties use earlier due date, then creation time. These are adjustable product defaults, not psychological measurements. Available time, fixed appointments, preparation blocks, task length, energy and the daily priority limit determine what fits. A smaller lower-scored task may fit where a larger one cannot.

Changing a priority does not silently move protected blocks. It affects the next planning pass. Use Plan my day to request one, or let the quiet scheduler fill a gap when no upcoming work block remains. Parked tasks remain visible but are excluded until reopened.

## Recorded consideration

Each planning pass stores its time window and a decision for every known unfinished task. The scheduler considers every open task; the model receives at most 30 task briefs per ranking. Backlog explicitly distinguishes those two forms of coverage. A model shortlist omission does not remove a task from the scheduler's candidates.

The latest recorded decision is historical. The factors shown beside it are current and may reflect edits made after that pass. The UI labels both. It does not reconstruct or pretend to know earlier model coverage from deployments that did not record it.

Tasks may be excluded because they are parked, already have reserved time elsewhere, had a finished session in the planning window, or did not receive a slot under the time and daily-priority limits. A finished session remains separate from a confirmed finished task.
