# FTP Sync Exclusion Rules (Brother C00/D00)

This document defines the file exclusion and filename validation policy used by Shatter FTP sync.

## Manual References

The sync rule set is derived from Brother manual constraints available in this repository:

1. C00 control format: [docs/scrape/section_5_6_4_c00.json](docs/scrape/section_5_6_4_c00.json)
2. D00 control format: [docs/scrape/section_3_6_5_d00.json](docs/scrape/section_3_6_5_d00.json)
3. Source PDFs:
1. [docs/brother-manuals/CNC-D00_Data bank & Alarm manual.pdf](docs/brother-manuals/CNC-D00_Data%20bank%20&%20Alarm%20manual.pdf)
2. [docs/brother-manuals/CNC-D00_Operation manual II.pdf](docs/brother-manuals/CNC-D00_Operation%20manual%20II.pdf)

## Constraints Applied

1. Extension restriction: only `.NC` files are eligible for sync upload.
2. ASCII restriction: non-ASCII filenames are excluded.
3. Uppercase restriction: filenames must be uppercase.
4. Reserved system file protection: names matching CNC system/data files are excluded (for example `ALARM*`, `MONTR*`, `POSN*`, `MEM*`, `TOLN*`, `ATCTL*`, `PRDC*`, `PRDD*`, `SYSC*`, `SYSD*`).
5. O-number enforcement (default): filename stem must match `O####`.
6. Character whitelist for non O-number names (when allowed): `A-Z`, `0-9`, `_` only.
7. Length limits for non O-number names:
1. C00 mode: max 8 characters (aligns with C00 half-width naming constraints).
2. D00 mode: max 32 characters.
8. Nested directory limits under strict naming mode:
1. C00 mode: subfolders are excluded (root files only).
2. D00 mode: up to two folder levels are allowed; deeper nesting is excluded.
9. Pattern-based exclusions: configurable glob list defaults to `.*,~*,*.tmp,*.temp,*.bak,*.swp,*.DS_Store`.

## Config Fields (ftp_sync_configs)

1. `sync_direction` (`upload` or `download`)
1. `include_pattern`
2. `exclude_patterns` (comma-separated globs)
3. `control_type` (`C00` or `D00`)
4. `strict_brother_naming` (bool)
5. `require_onumber_filename` (bool)

`upload` means local folder -> CNC folder.
`download` means CNC folder -> local folder.

## Exclusion Reason Codes

Run items excluded by rules are recorded as `status=skipped` with one of:

1. `filename_matches_exclude_pattern`
2. `unsupported_extension`
3. `non_ascii_filename`
4. `filename_must_be_uppercase`
5. `reserved_system_filename`
6. `requires_onumber_filename`
7. `invalid_characters`
8. `filename_too_long_for_C00`
9. `filename_too_long_for_D00`
10. `nested_directories_not_supported`
