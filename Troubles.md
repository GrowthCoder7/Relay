## [Day 0] Known risks going in (not yet encountered, flagged proactively)

**Risk: WebSocket broadcast + mid-task steering race conditions**
The agent loop needs to check for pending steering messages BETWEEN steps 
without blocking on them if none exist, while also not missing a message 
that arrives mid-step. This is the highest-risk piece of Day 2's work — 
likely needs a simple message queue per session (e.g. an asyncio.Queue 
checked at each step boundary) rather than anything fancier. Watch for 
this specifically when opencode implements the agent runner — a common 
failure mode is either blocking the whole loop waiting for a steering 
message, or dropping messages that arrive during a long-running step.

**Risk: Session reconnect / backfill correctness**
When a client joins a room mid-task (Day 3), they need full history 
(from Supabase) PLUS to seamlessly pick up the live tail (from the 
WebSocket) with no gap and no duplicate messages. This is a classic 
off-by-one/race bug source — the backfill query and the "start receiving 
live broadcasts" subscription need to be sequenced carefully (e.g. 
subscribe to live broadcasts first, buffer them, THEN fetch backfill, 
THEN replay buffered live messages that arrived after the backfill 
snapshot). Flagging this now so it's not a surprise on Day 3.

**Risk: Competitive landscape claim in existing pitch deck is stale**
Relay-Pitch.pptx slide 7 claims "no incumbent owns multiplayer AI" — this 
was true when the deck was written but is no longer accurate as of 
Sept 2026 research (see Decisions.md). Must update before presenting to 
the board — using the stale claim in front of a technical board member 
who may know the space is a credibility risk.