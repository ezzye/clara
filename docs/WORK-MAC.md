# Set up the work Mac

Use Codex and Chrome on the work Mac. Keep browser sessions and work credentials on that machine. The public repository is the code; it contains no private deployment record, account session or pairing key. Use the owner's existing private Clara address and account, not a new AWS deployment.

## First steps for the owner

1. Open your existing Clara website on the work Mac and sign in with your password and authenticator.
2. Open Chrome and sign in to current cloud Jira, Confluence, Outlook and Slack. Leave the relevant tabs open.
3. Open Codex. Continue the existing Clara task if it is available on that machine, or start a task with the handoff below.
4. Old Jira is retired. Do not install or copy its developer certificate just to connect Clara. Historical links may be kept as references; they are a separate source from cloud Jira.

## Handoff to Codex

> Continue the Clara work-Mac setup using https://github.com/ezzye/clara. Use my existing private Clara website and account. Read docs/WORK-MAC.md and docs/CONNECTIONS.md. Inspect my signed-in Chrome tabs to identify current cloud Jira, Confluence, Outlook and Slack. Keep credentials out of chat, source and Git. Use a dedicated upload-only connection for this Mac and leave AI planning on the already paired personal Mac. Old Jira is retired. Validate one captured message and one real meeting before broadening collection. Do not create another AWS stack.

## Repository and connection

Clone the public repository into a normal local development folder. Check the available Python version and create an isolated environment as described in the README. Do not copy `.private` from another laptop: each device has its own connection.

In Clara, use **Connections → Pair a laptop**. Name it **Work MacBook**, choose macOS, and leave planning permission off. The pairing key is shown once. Enter it through the companion's masked pairing prompt, never in chat:

```sh
python -m clara_agent.daemon --config /private/path/work-device.json --pair
```

The private configuration contains only this device's ID, the existing HTTPS endpoint and selected source folders. Start with empty folder lists. The OS credential manager stores the token. Install the companion only after a successful bounded cycle; it must honor pause and revocation.

## Chrome capture

Load `apps/chrome` as an unpacked extension if the work browser permits it. Use a separate upload-only key for the browser extension. Enter the existing Clara HTTPS address, that key and the exact approved origins in extension settings. Do not request wildcard work-domain access. Chrome extension storage holds this revocable upload key; it must have no planning permission.

Preview a single non-sensitive work-page extract, edit it if necessary, and submit. Confirm the evidence appears in Clara Review with its source origin. Jira issue identity includes the site, not just a key such as ABC-12. A migrated key must never silently merge old and cloud issues.

For Outlook, first verify one real future meeting against its current calendar entry. Check date, time zone, recurrence exceptions, cancellations and whether attendance is expected. A cancelled recurring series and a live exception can both appear: do not import both as meetings. Source snapshots are not a live calendar subscription.

The current extension uses manual preview and submission. It does not continuously read your work accounts. If installation is blocked by the work browser, stop that installation and use the authorized interactive Chrome session to review a bounded source; do not bypass device controls.

## What runs where

- Work Mac: authenticated work browser and approved captures.
- Personal Mac: the existing Codex planning companion and its bounded model budget.
- Private AWS deployment: the shared plan, source-backed drafts and editable meeting/task records.
- Public GitHub: reusable code and generic instructions only.

An initial acceptance check should show the same captured source and accepted task in Clara on both Macs. Only after that should automatic browser-specific collection be designed and tested against the actual workplace interfaces.

## Full project inventory on an already paired Mac

Update the existing checkout and use its existing private configuration and Keychain entry. Do not pair again, copy keys, or install a scheduler when workplace controls require manual operation. Keep the existing **Run Clara.command** workflow.

Set `codexDb` in that machine's private configuration to its verified local Codex SQLite database. Enable inventory with the existing Python environment:

```sh
python -m clara_agent.inventory --config /private/path/work-device.json --context work --cowork-sessions "$HOME/Library/Application Support/Claude/local-agent-mode-sessions"
```

Then run the existing manual companion once. This enumerates all working directories in the local Codex task database, without the activity collector's seven-day limit, and the local Cowork session index when available. Only metadata is uploaded. Archived sessions remain completion-unknown. An absent source reports unavailable. Later snapshots preserve the owner's Work/Home classification, priority and completion review.

This is a project/session inventory, not an authenticated Jira or Outlook connector. Collect the actual cloud Jira board and next week's Outlook occurrences separately through approved Chrome access. Record scope, pagination completion, observed time and exceptions; do not claim full board/calendar coverage after a sample capture. Keep ticket identity scoped to the Jira site, distinguish assigned tickets from the rest of the board, and require real dates and timezones for meetings.
