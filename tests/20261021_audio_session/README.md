# Receiver audio-session regression

Observed hardware feedback: language switching works, then both video and audio remain frozen after about 30 seconds. The relationship to server session reporting is not yet established.

The published 4097 restart used its own Playing/Progress POST worker. That worker did not update the announcement registry used by periodic Progress. A local regression test reproduces a second Playing announcement at the first periodic Progress. The new path uses the existing serialized session reporter for both startup and periodic updates. It commits the requested server audio index and session identity before reporting. Backend 4097, server resume position, copy codecs and old-session cleanup are retained.

Six tests execute the actual extracted restart/report functions with simulated HTTP and worker boundaries. The old baseline reproduces two Playing announcements; the fixed path sends one through simulated 10, 20, 30, 40 and 60-second Progress ticks. Other checks cover selected audio/session identity, Playing-before-Progress ordering, rejected registration, backend, resume URL and cleanup of only the old session. This does not establish audible output, moving video, successful server remux, or a fix for the 30-second hardware freeze.

Run python tests/20261021_audio_session/test_session_fix.py and python tests/20261021_audio_session/build_session_fix.py. The complete generated plugin parses as Python 3.8 and compiles. Build 2026102104 retains HD detail layout and LCD fixes. Receiver and UT tests remain pending; distribute only via EmbyFlow -> Updates.
