# Known Limitations

- **Interview-status detection is unvalidated.** No real interview-invite email was available during development to confirm the matching patterns work.
- **The 14-day response benchmark is a fixed default**, not learned from your own logged history. A future version could compute this from your actual data once enough applications have been logged.
- **Company-name extraction covers the phrasings seen in testing**, not every possible way an email might introduce a company name. Expect real misses on differently-worded emails; `patterns.yaml` is the place to extend coverage.
- **No message-ID tracking.** `sync` re-fetches and re-parses the same recent messages on every run. Duplicate detection prevents re-logging them as new records, but this is not the same as skipping already-seen messages efficiently.
- **OAuth2 / Gmail REST API is not implemented.** AppVault uses IMAP with an app-specific password, which is sufficient for personal use but requires the manual setup steps in the README. A REST API + OAuth2 version was considered as an optional future addition and was not built yet.