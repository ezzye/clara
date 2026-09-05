# Clara

A private personal assistant for preparing, focusing and finishing. Clara turns a small set of priorities into an editable plan, keeps appointments protected and compares plans with observed activity without pretending that activity proves completion.

**Open-source code, private deployment.** Your identity, tasks, email, calendar, activity and credentials belong in your own private data store, never this repository.

## Working in this release

- Now, Hour, Day and Week plans; Month and Year outcome views.
- A Life view for sleep routines, health follow-up, inbox distractions, social time and exploring a business, within the same daily capacity.
- Editable tasks, clear first steps and stopping points, priorities, parking and completion.
- Meeting appointments, protected times, preparation blocks and editable briefings.
- Focus timer, adjustable session lengths, buffers and lower-energy planning.
- Plan-versus-recorded-session review, evidence provenance and explicit confirmation.
- Persistent state with conflict detection across devices.
- Single-owner AWS authentication with Cognito, PKCE, TOTP MFA and disabled self-registration.
- Encrypted DynamoDB state, private deployment artifacts and a 15-minute cloud scheduler.
- Revocable macOS/Windows companion credentials, read-only Codex and folder metadata collectors.
- Codex proposes task order; tested scheduling rules constrain the result. Models cannot mark work complete or take external actions.
- Optional, manual Chrome work-page briefs, selected WhatsApp Web messages and a public-data-only DeepSeek adapter.

## Not connected automatically

Gmail OAuth, bank feeds, the second MacBook and Windows PC require their own setup. The Chrome extension requires exact work origins and manual review; it does not yet autonomously scrape Jira, Confluence, Outlook or Slack. Meeting briefs currently support structured manual preparation, not fully automatic research. Cowork support is limited to selected exported-file metadata. The DeepSeek adapter is not active by default. This is an initial working foundation, not a claim that every integration is complete.

## Run locally

The Life view holds chosen next actions, not medical records. NHS and watch data have no background connection; manually reviewed appointment snapshots and links to NHS services are supported. It does not diagnose, prescribe sleep times, or make bookings.

Requires Node.js 22+ and Python 3.12.

```sh
npm ci
npm run build
python3 -m apps.api.local
```

Open the single-use launch link saved under `.private/launch-url`. The server binds to `127.0.0.1:8766`. It starts empty; there is no real-person seed in source. State is kept in `.private/clara.sqlite`, excluded from Git. Protect the laptop with disk encryption.

For companion setup:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-agent.txt
```

See [Connections](docs/CONNECTIONS.md) for per-device setup and its current limits.

## Deploy on AWS

```sh
npm run build
python3 scripts/package.py
python3 scripts/deploy.py --region eu-west-1
# Wait for CREATE_COMPLETE, then invite exactly one owner:
python3 scripts/create_owner.py --email YOUR_EMAIL --region eu-west-1
```

The default AWS credential profile is used. Deployment creates pay-per-use resources in a dedicated stack and private artifact bucket; these are not free by definition. Check the AWS bill and set an account budget appropriate to your usage. The generic sign-in page is reachable; every private data route is gated. Do not treat possession of the URL as authorization.

**On every later deployment, pass the existing immutable owner subject using `--owner-sub`.** Read it from your private deployment record. The deployment script preserves an existing subject when omitted and refuses a different owner. Never put the private deployment record in Git.

## Verify

```sh
npm test
npm run build
```

Tests cover authorization boundaries, conflicting edits, revocation, pause, evidence deduplication, secret exclusion, scheduling capacity, fixed meetings, preparation retention and timezone-aware observation timestamps. Live endpoint checks should additionally verify signed-out denial and an owner sign-in. Completing first-login MFA is a human action and is not replaced by mocked tests.

## Design principles

Small starts. Visible finish lines. Breathing room. Useful preparation. No shame, streak penalties, hidden behavioural profiling or diagnosis. Support strategies are adjustable product features, not claims to treat a medical condition. A plan is an invitation, and the owner can change it.

Read the [architecture and data boundaries](docs/ARCHITECTURE.md), [connection guide](docs/CONNECTIONS.md), [security policy](SECURITY.md), and [development roadmap](docs/ROADMAP.md).

MIT licensed.
