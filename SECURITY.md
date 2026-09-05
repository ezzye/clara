# Security

Do not include personal data, access tokens, cloud account identifiers, bank information, screenshots or live deployment links in public issues or pull requests. For a suspected credential leak, revoke the affected credential before sharing a sanitized reproduction.

The only public deployment content is the generic app shell. Private data requires the owner's identity or a narrowly scoped device token. Root/administrator access to the hosting account remains a trusted boundary; this is not protection against the account administrator.

Deployment preserves the owner subject and disables self-signup. Private state, logs, exported data and credentials are ignored by Git. The packaging script includes only explicit application directories and built assets. Every release needs a tracked-file secret scan and authentication checks. Never include `.private`, a SQLite database or `.env` in an artifact.

Pause and revoke are immediate server controls. Live evidence deletion is available; backup copies follow AWS retention and require separate handling. Deleting the AWS stack does not remove retained DynamoDB/Cognito data or the artifact bucket. To retire the service: disable the EventBridge rule, remove the companions, revoke device credentials, export desired records, then deliberately delete retained resources and backup copies. Complete account-data deletion is an administrator procedure in this version.

Untrusted source material and model output cannot authorize sending email, writing work systems, making payments, posting publicly or changing permissions. Such capabilities are not implemented in the planner. Do not add arbitrary tool execution to a summarizer.
