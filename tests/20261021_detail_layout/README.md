# Receiver detail-layout test

At 720p, the old layout shifted the overview body up by 30 physical pixels but did not shift the heading: its x-coordinate test still expected unscaled 90. The new code scales both the predicate coordinates and the 30-pixel vertical shift. Metadata captions and values also share the same scaling; badge refresh uses scaled coordinates without cumulative drift.

Three local regression tests exercise the actual extracted layout functions at 1280x720, 1920x1080 and 3840x2160. They verify non-overlapping heading/body bounds, metadata bounds and font scaling, and repeated badge refresh without drift. The complete generated plugin parses as Python 3.8 and compiles. This is not native receiver rendering confirmation.

Build 2026102103 retains the 4097 audio candidate and LCD fix. Hardware and UT tests remain pending. Distribution exclusively through EmbyFlow -> Updates.
