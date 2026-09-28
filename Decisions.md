## [Day 0] Project pivot: DriftGuard → Relay

**Context:** Hackathon (First Commit, AWS Build It track) concluded with a 
working DriftGuard prototype. Returning to original DysrupIT pitch track. 
Chose to build Relay (Multiplayer AI) over continuing DriftGuard, per 
`Relay-Pitch.pptx`. Timeline: 3-4 days, solo architecture + opencode-driven 
implementation (Qwen/Nvidia models via opencode, Gemini Pro, OpenRouter 
available as backup model providers).

## [Day 0] Competitive landscape re-assessment

**Decision:** Revised the original pitch's "no incumbent owns multiplayer 
AI" claim (Relay-Pitch.pptx, slide 7) — this is no longer accurate as of 
Sept 2026.

**Why:** Research found real competitors:
- Zed (multiplayer agent editing, live, in-buffer, but locked to Zed's own 
  editor — not portable to Claude Code/Cursor/other tools teams already use)
- Stardock Clairvoyance (live multi-person agent sessions, but local-first/
  single-host-machine, not a team/enterprise deployment model)
- Devin Handoff / `handoff` skill (agent-to-agent or human-to-cloud handoff, 
  but async and one-directional — no live shared view, no mid-task steering)
- SoftworkerAI (explicitly pitching "multiplayer AI workspace" as its 
  product, appears to be its own closed platform)

**Revised differentiator:** Nobody has a lightweight layer that makes an 
*existing* agent tool/session live-joinable and steerable by a team, without 
forcing adoption of a new editor or platform. Narrower than the original 
claim, but real and defensible — "bring multiplayer to the tool you already 
use" rather than "own the multiplayer category."

**Implication for the pitch:** Update Relay-Pitch.pptx slide 6/7 before the 
board meeting to reflect this — do not present the original "no incumbent" 
claim as still true.

## [Day 0] MVP scope decision — simulate the agent, build the multiplayer layer for real

**Decision:** For the 3-4 day prototype, we are NOT integrating with real 
Claude Code sessions (no stable public hook for live session interception 
in this timeframe). Instead, we build our own controllable agent loop 
(Strands + Gemini) that we fully own, and invest the build time in making 
the MULTIPLAYER mechanics (live view, steering, handoff, shared history) 
genuinely real — since that's the actual product differentiator, not the 
underlying agent.

**Rationale:** Same judgment call as DriftGuard's scanner-vs-agent split — 
keep the unprovable/high-integration-risk part simple, make the actual 
differentiator real and demo-able.

## [Day 0] Tech stack

- **Backend language:** Python (not Go) — team fluency from DriftGuard, 
  FastAPI's native async+WebSocket support fits this app's concurrency 
  shape (many clients, one session, live pushes), every needed SDK 
  (Strands, Gemini, Supabase) has first-class Python support.
- **Backend framework:** FastAPI — native WebSocket support, async-first, 
  minimal boilerplate, free OpenAPI docs.
- **Real-time transport:** FastAPI's native WebSocket support (raw, no 
  Socket.IO/PartyKit). One WS endpoint per session ID; server-side 
  ConnectionManager holds active sockets per room, broadcasts on state 
  change.
- **Database:** Supabase (Postgres) — already available, generous free 
  tier, used for persistence (sessions, steps, participants) — 
  **explicitly NOT used as the live-broadcast mechanism** (see next 
  decision).
- **Auth:** Supabase Auth (magic link/email) — not the differentiator, 
  minimal time investment here.
- **Agent/LLM layer:** Strands Agents SDK + Gemini — carried over from 
  DriftGuard, already proven working, zero new integration risk. Strands' 
  step-by-step tool-call structure maps naturally onto "stream each step 
  as a broadcast event."
- **Frontend:** Plain HTML/JS + Tailwind CDN, no build step — same pattern 
  as DriftGuard, fast iteration, this is fundamentally one page with a 
  live event stream, not a component-heavy multi-page app.

## [Day 0] WebSockets (own layer) vs. Supabase Realtime — chose own layer

**Decision:** Build our own FastAPI WebSocket broadcast layer rather than 
using Supabase Realtime (Postgres change-data-capture push).

**Why:** Supabase Realtime would be less code (write to a table, Supabase 
pushes changes automatically) but weakens the pitch's core claim — "we 
built real-time multi-user session infrastructure" is central to Relay's 
credibility with the board. Outsourcing the live-broadcast mechanism to a 
managed service undercuts that claim. Supabase is used purely as the 
persistence layer (Postgres tables for sessions/steps/participants), not 
as the live-push mechanism.

## [Day 0] Build phase plan (3-4 days)

- Day 1: FastAPI skeleton, Supabase schema, single-client live agent step 
  streaming (no multiplayer yet — prove the live-view spine)
- Day 2: Multiplayer — multiple WS clients per room, broadcast, steering 
  (mid-task message injection visible to all clients). Highest-risk day.
- Day 3: Handoff (ownership transfer), full history persistence, 
  reconnect-to-existing-session (join mid-task, backfill + live tail)
- Day 4: Polish, demo task selection, pitch deck update, buffer

## [Day 2] Multi-client broadcast — confirmed working

**Result:** Tab 2 (the non-sending client) received the same steering 
message broadcast live via WebSocket, confirmed via ws2.onmessage 
logging it in Tab 2's console. This proves genuine multi-client sync — 
both browsers watching the same session saw the same steering event and 
the same subsequent agent steps in real time, not just the sender seeing 
their own action reflected back.

**Day 2 status: COMPLETE.** All three tested mechanics work together: 
(1) multi-step pacing gives a real window for steering, (2) a steering 
message from any connected client redirects the agent's actual output, 
(3) all connected clients see the same live broadcast simultaneously. 
This is the core "multiplayer" claim of Relay, genuinely demonstrated, 
not simulated.