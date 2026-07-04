# SUBMISSION WRITEUP — Smart Travel Concierge

## Problem Statement

Planning international travel is time-consuming and error-prone. Travelers must
juggle visa requirements, budgets, itineraries, flight searches, and local tips
— often across multiple websites. Mistakes (wrong visa type, underestimated budget,
wrong travel season) can ruin a trip or cause significant financial loss.

The Smart Travel Concierge solves this by providing an end-to-end, AI-powered
planning pipeline: one input, one structured travel plan — secure and audited.

---

## Solution Architecture

```
User Request
     │
     ▼
┌─────────────────────────────────────┐
│       Security Checkpoint           │  ◄── PII scrub | Injection detect
│     (security_checkpoint node)      │      Audit log | Illegal content filter
└────────────┬────────────────────────┘
             │ ok                     │ SECURITY_EVENT
             ▼                        ▼
┌────────────────────┐   ┌──────────────────────┐
│ Travel Orchestrator│   │  Security Rejection   │
│  (root_agent)      │   │  (declines request)   │
└────────────────────┘   └──────────────────────┘
     │         │         │
     ▼         ▼         ▼
┌──────────┐ ┌──────────────┐ ┌──────────────────┐
│Destination│ │  Itinerary   │ │    Response      │
│Researcher │ │   Builder    │ │    Assembler     │
└─────┬─────┘ └──────┬───────┘ └────────┬─────────┘
      │               │                  │
      └───────────────┴──────────────────┘
                      │
             ┌────────▼────────┐
             │   MCP Server    │
             │  5 travel tools │
             └─────────────────┘
```

---

## Concepts Used

| Concept | Implementation | File |
|---|---|---|
| ADK Workflow | LlmAgent orchestrator + sub-agents | `app/agent.py` |
| LlmAgent | destination_researcher, itinerary_builder, response_assembler, security_rejection | `app/agent.py` |
| AgentTool | Orchestrator delegates to sub-agents via AgentTool | `app/agent.py` |
| MCP Server | 5 travel tools via stdio transport | `app/mcp_server.py` |
| Security Checkpoint | security_checkpoint() function node | `app/agent.py` |
| Agents CLI | Scaffold + playground + manifest | `agents-cli-manifest.yaml`, `Makefile` |

---

## Security Design

| Control | Details |
|---|---|
| **PII Scrubbing** | Regex patterns for passport numbers, credit cards, emails, phone numbers, national IDs. Replaced with `[REDACTED_TYPE]` before any LLM sees the input. |
| **Prompt Injection Detection** | Keyword list (10 patterns) catches "ignore previous instructions", "jailbreak", "act as", etc. Routes to rejection agent immediately. |
| **Domain-Specific Filter** | Blocks illegal travel requests: fake passports, smuggling, forged visas, black market keywords. |
| **Structured Audit Log** | Every request produces a JSON log entry with timestamp, severity (INFO/WARNING/CRITICAL), PII found, injection detected. |

Why it matters: Travel concierges handle sensitive PII (passport numbers, payment info) and face adversarial inputs from users trying to extract illegal travel advice.

---

## MCP Server Design

File: `app/mcp_server.py`

| Tool | Purpose | Used By |
|---|---|---|
| `get_destination_info` | Highlights, cuisine, currency, travel tips | destination_researcher |
| `check_visa_requirements` | Visa type, processing time, max stay | destination_researcher |
| `estimate_flight_cost` | Round-trip cost range by class | itinerary_builder |
| `get_best_travel_season` | Best months, months to avoid, weather | destination_researcher |
| `estimate_trip_budget` | Full budget breakdown by category | itinerary_builder |

Transport: stdio (spawned as subprocess by ADK via StdioConnectionParams).

---

## HITL Flow

This project does not currently implement a RequestInput HITL pause, as the
travel planning flow is fully automated. However, the security checkpoint acts
as a human-equivalent gate: any SECURITY_EVENT terminates the flow and returns
a rejection — preventing any automated action from occurring on flagged inputs.

Future enhancement: add a RequestInput node for human approval of high-budget
trips (e.g., > $5,000 total estimate) before finalizing the itinerary.

---

## Demo Walkthrough

Refer to the three sample test cases in README.md:

1. **Tokyo 7-day mid-range** — demonstrates full orchestrator → researcher → builder → assembler pipeline.
2. **Bali 5-day budget** — demonstrates cross-nationality visa logic and budget-level selection.
3. **Security injection block** — demonstrates the security checkpoint catching a dual-threat input.

---

## Impact / Value Statement

**Who benefits:** Solo travelers, families, and travel agencies who want to reduce
planning time from hours to seconds.

**How:** One natural-language request triggers a full multi-agent pipeline that
researches destinations, checks visa rules, estimates costs, and builds a
day-by-day itinerary — all in a single interaction, with security built in.

**Why ADK:** The multi-agent architecture means each specialist (researcher,
builder, assembler) can be swapped, upgraded, or extended independently —
making the system production-ready and maintainable.
