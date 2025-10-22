# Commit Message Convention

This repository uses a simple, descriptive commit message style based on the following principles:

## Format

- Each commit message should be a short, imperative summary of the change.
- The message may be a single line or include a free-form detail section after a blank line.
- There is no enforced prefix, type, or scope, but common verbs include: `Update`, `Create`, `Add`, `Fix`, `Remove`, `Merge`, etc.

## Examples

```txt
Create .gitignore

Update README.md

Create requirements.txt

Fix docker compose

Add sample environement file

Update and rename Website Status Checker.py to DiscordWebsiteMonitor.py

Merge branch 'main' into docker-patch
```

## Guidelines

- Use a clear, concise summary that describes what changed.
- Use the imperative mood (e.g., “Update”, “Create”, “Fix”).
- For merges, use “Merge branch …” or “Merge pull request …”.
- If more detail is needed, add it after a blank line.
- No strict rules on punctuation, casing, or structure except for the first line where it is the action and then the affected file.

---

This convention is designed for clarity and ease of use, matching the actual history of this repository (although the repository did not always follow it).
