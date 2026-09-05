# Connecting the rest of your world

## Personal MacBook

The companion reads metadata from explicitly selected Codex project roots and optionally recent direct-child Downloads filenames. It never reads full transcripts or downloaded document bodies. Each machine has a different key in macOS Keychain or Windows Credential Manager. Revoke a key from Connections, or pause all collection from the sidebar.

Install dependencies in an isolated environment, copy `clara_agent/config.example.json` to a private directory, edit the endpoint/device ID and allowlisted paths, then run:

```sh
python -m clara_agent.daemon --config /private/path/device.json --pair
python -m clara_agent.daemon --config /private/path/device.json
python scripts/install_companion.py --config /private/path/device.json
```

Run these with the same Python environment that has `keyring` installed. Supply an absolute `codexExecutable` on macOS because launchd has a minimal PATH. Install only one planning-enabled companion at first. Collection runs every five minutes while the user session is available; it cannot observe an asleep or powered-off laptop. Source files remain in place.

Remove the scheduler with the same install script plus `--remove`, revoke the device key in Clara, and remove its credential-manager entry. Revocation blocks network writes even if a local timer remains installed.

## Work MacBook: Chrome

This version supplies a manual browser-brief extension. In Chrome's extensions page, enable developer mode and load `apps/chrome` as an unpacked extension. Use Connections in its popup to enter the private endpoint, a dedicated upload-only key, and exact work origins. No hosts are preselected. The user reviews a short extract before uploading. It does not follow links, send messages or mark work done.

Jira, Confluence, Outlook email, Outlook Calendar and Slack may have different origins and authentication rules. Validate each real work route and employer permission on that MacBook before any unattended capture implementation. Imported evidence currently appears in Review; it does not automatically become a correct calendar event or meeting briefing. Automatic extraction must preserve source links, real dates, timezone, uncertainty, cancelled-event handling and recurrences, and be tested against the actual interfaces.

## Claude Cowork

There is no verified universal, cross-device Cowork history API in this implementation. Select dedicated exported work folders using `coworkExportFolders`. The current adapter observes filenames and modification times only. Do not point it at browser profiles, credentials, or all of Application Support. A fuller Cowork adapter needs an explicit supported export format and local validation on both Macs.

## Gmail

The connected Gmail tool used during app construction is not a reusable OAuth credential for a separate website. `clara_agent/gmail.py` is a bounded metadata reader, but is not enabled by the daemon or connected to an account by default. Complete an installed-app OAuth flow with `gmail.readonly`, save its refresh credentials in the OS credential manager under service `clara-gmail`, then integrate that source into the daemon. Never copy cookies, Codex plugin tokens, passwords or one-time codes. OAuth consent UI and automatic event extraction remain to be built.

## WhatsApp

The browser companion supports explicitly selected text on `https://web.whatsapp.com`. Add that exact origin in its settings, highlight the relevant messages, preview and edit the extract, then submit. On WhatsApp it refuses a whole-page capture. Include the conversation name and message date in the reviewed brief where useful. A message is evidence of a discussion, not automatically an agreed commitment or proof of completion.

The native WhatsApp app can be reviewed interactively through the owner's authorized computer session. That access is not an installed daemon integration. No continuous WhatsApp monitoring, historical backfill, sending or contact-management capability is enabled here. A future local adapter needs allowlisted conversations, source timestamps, correction/deletion handling and reliable deduplication. Keep private chats out of public source and the public-only DeepSeek route.

## smile and Co-operative Bank

Use a regulated Account Information Service provider that currently supports both accounts. Verify provider coverage and FCA registration, then choose read-only account/transaction consent, with no payment-initiation scope. The owner is redirected to the genuine bank service to authorize. Clara must not receive bank passwords, PINs or passcodes. Tokens remain in a private server secret store, with revocation and expiry visible.

The banks describe this route at [smile Open Banking](https://www.smile.co.uk/digital-banking/open-banking/). Provider eligibility, production onboarding, account coverage and costs have not been established here. A direct personal app cannot simply assume it qualifies as a regulated provider. Until provider onboarding is complete, a private statement-file importer is a possible next module; it is not implemented in this release. Financial records must be excluded from general-purpose model context by default. Transactions can suggest admin tasks but cannot prove attendance, location or intent.

## Agent providers

The local Codex adapter follows the [official Codex SDK and automation guidance](https://learn.chatgpt.com/docs/codex-sdk), using the installed CLI interface verified during development. The Python implementation uses the CLI's structured response support. It preserves the installed model default unless configured. A production cloud Codex worker needs a separate deployment and authentication decision; copying a laptop's entire credentials folder into AWS is not part of this setup.

DeepSeek is an optional adapter, accepts public-labelled inputs only and needs a server-side `DEEPSEEK_API_KEY`. No private source has been submitted to DeepSeek in this release. The adapter is not scheduled until a bounded job and budget are configured.
