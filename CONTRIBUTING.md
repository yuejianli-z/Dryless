# Contributing

Thanks for your interest in improving Dryless.

## Principles

- Keep camera processing local.
- Do not add telemetry, analytics, or network upload behavior without clear discussion.
- Do not save camera frames or videos.
- Keep the Windows desktop experience simple and reliable.
- Update README documentation when behavior changes.

## Development

```bash
pip install -r requirements.txt
python main.py
```

## Pull Requests

Before opening a pull request:

- Make sure the app still starts successfully.
- Check that no generated files, caches, virtual environments, or build outputs are committed.
- Explain user-facing behavior changes clearly.
- Mention any privacy or security implications.
