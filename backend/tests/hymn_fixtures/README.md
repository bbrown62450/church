# Hymn test data

`scripture_refs_sample.csv` (columns `hymnal,number,title,scripture_refs`) feeds
`test_scripture_refs_parse.py::test_sample_parses_at_least_98_percent_of_segments`
(slice 3 spec, "Data and migrations"; AC3).

Status: SYNTHETIC. Written by hand for the slice 3a plan in Hymnary.org's shape
(link texts joined by "; "), because the repository holds no real
`scripture_refs` data. Replace it with the owner's read-only export of
`hymn_catalog` (slice 3a plan, Task 4 Step 1) and change this line to say
"EXPORTED on <date>". It is public hymn metadata with no personal data.
