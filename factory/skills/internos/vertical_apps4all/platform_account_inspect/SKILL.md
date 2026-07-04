# Apps4All account inspection

## Context required

Use:

- `schema=platform`
- `company_id=EMP_APPS4ALL`

## Notes

- For reading lists of `companies`, `users`, and `access_grants`.
- Read only. No writes.
- Use the `platform` schema via `Accept-Profile: platform` when reading.

## Use case

- Provide admins a read-only view into platform metadata without touching legacy routes or data.
