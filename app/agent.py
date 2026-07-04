# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re
import sys
import asyncio
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

from app.config import config

# ─────────────────────────────────────────────────────────────────────────────
# MCP Toolset — connects to mcp_server.py via stdio
# ─────────────────────────────────────────────────────────────────────────────
_mcp_server_path = str(Path(__file__).parent / "mcp_server.py")

mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[_mcp_server_path],
        )
    )
)

# ─────────────────────────────────────────────────────────────────────────────
# Rate Limit Mitigator (Bypasses the 5 RPM Free Tier Limit)
# Subclasses AgentTool to space out LLM sub-agent calls by 15 seconds.
# ─────────────────────────────────────────────────────────────────────────────
class DelayedAgentTool(AgentTool):
    async def run_async(self, *args, **kwargs):
        print(f"[Rate Limit Guard] Sleeping for 15s before running agent tool: {self.name}...")
        await asyncio.sleep(15.0)
        return await super().run_async(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Sub-agent 1: Destination Researcher
# Looks up destination info, visa requirements, and best travel seasons.
# ─────────────────────────────────────────────────────────────────────────────
destination_researcher = LlmAgent(
    name="destination_researcher",
    model=config.model,
    instruction="""You are a destination research specialist.
Given a destination and traveler profile, use your tools to:
1. Retrieve destination highlights and travel tips.
2. Check visa requirements for the traveler's nationality.
3. Recommend the best travel season.
Return a structured JSON with keys: destination, visa_info, best_season, highlights.""",
    tools=[mcp_toolset],
    output_key="destination_research",
)

# ─────────────────────────────────────────────────────────────────────────────
# Sub-agent 2: Itinerary Builder
# Creates a day-by-day itinerary based on destination research and budget.
# ─────────────────────────────────────────────────────────────────────────────
itinerary_builder = LlmAgent(
    name="itinerary_builder",
    model=config.model,
    instruction="""You are an expert travel itinerary planner.
Using the destination research in state['destination_research'] and the user's
budget and trip duration, use your tools to:
1. Estimate the flight cost.
2. Estimate the total trip budget breakdown.
3. Build a day-by-day itinerary with activities, meals, and accommodation suggestions.
Return a structured JSON with keys: days (list), budget_breakdown, flight_estimate.""",
    tools=[mcp_toolset],
    output_key="itinerary",
)

# ─────────────────────────────────────────────────────────────────────────────
# Security checkpoint — function node
# PII scrub + prompt injection detection + audit log
# ─────────────────────────────────────────────────────────────────────────────
def security_checkpoint(ctx):
    """
    Scrubs PII and detects prompt injection in the incoming user request.
    Writes a structured audit log entry to ctx.state['audit_log'].
    Returns 'SECURITY_EVENT' if a threat is detected, else 'ok'.
    """
    import datetime

    user_input = str(ctx.state.get("user_request", ""))

    # ── PII scrubbing ─────────────────────────────────────────────────────
    pii_patterns = {
        "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
        "credit_card": r"\b(?:\d[ -]?){13,16}\b",
        "email": r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b",
        "phone": r"\b(?:\+?\d[\d\s\-().]{7,}\d)\b",
        "national_id": r"\b\d{9,12}\b",
    }
    scrubbed = user_input
    pii_found = []
    for label, pattern in pii_patterns.items():
        if re.search(pattern, scrubbed):
            scrubbed = re.sub(pattern, f"[REDACTED_{label.upper()}]", scrubbed)
            pii_found.append(label)

    ctx.state["user_request_clean"] = scrubbed

    # ── Prompt injection detection ────────────────────────────────────────
    injection_keywords = [
        "ignore previous instructions",
        "disregard your instructions",
        "forget your prompt",
        "override system",
        "jailbreak",
        "act as",
        "pretend you are",
        "you are now",
        "bypass",
        "do anything now",
    ]
    lower_input = user_input.lower()
    injection_detected = any(kw in lower_input for kw in injection_keywords)

    # ── Domain-specific rule: block requests for illegal activities ───────
    illegal_keywords = ["smuggling", "fake passport", "forged visa", "black market"]
    illegal_detected = any(kw in lower_input for kw in illegal_keywords)

    # ── Audit log ─────────────────────────────────────────────────────────
    severity = "INFO"
    if pii_found or injection_detected or illegal_detected:
        severity = "CRITICAL" if (injection_detected or illegal_detected) else "WARNING"

    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "severity": severity,
        "pii_scrubbed": pii_found,
        "injection_detected": injection_detected,
        "illegal_content_detected": illegal_detected,
        "input_length": len(user_input),
    }
    existing_log = ctx.state.get("audit_log", [])
    existing_log.append(log_entry)
    ctx.state["audit_log"] = existing_log

    if injection_detected or illegal_detected:
        return "SECURITY_EVENT"
    return "ok"


# ─────────────────────────────────────────────────────────────────────────────
# Security rejection node
# ─────────────────────────────────────────────────────────────────────────────
security_rejection_agent = LlmAgent(
    name="security_rejection",
    model=config.model,
    instruction="""A security policy violation was detected in the user's request.
Politely decline and explain that the request cannot be processed due to
security policy. Do NOT reveal the specific trigger. Be brief.""",
    output_key="final_response",
)

# ─────────────────────────────────────────────────────────────────────────────
# Response assembler node
# ─────────────────────────────────────────────────────────────────────────────
response_assembler = LlmAgent(
    name="response_assembler",
    model=config.model,
    instruction="""You are a friendly travel concierge.
Combine the destination research from state['destination_research'] and
the itinerary from state['itinerary'] into a warm, readable travel plan
for the user. Format with clear sections: Destination Overview, Visa Info,
Best Season, Day-by-Day Itinerary, and Budget Summary.
Store your final response in state['final_response'].""",
    output_key="final_response",
)

# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator — root agent
# Delegates to sub-agents via AgentTool; coordinates the full planning flow.
# ─────────────────────────────────────────────────────────────────────────────
root_agent = LlmAgent(
    name="travel_orchestrator",
    model=config.model,
    instruction="""You are the Smart Travel Concierge orchestrator.
When a user asks for travel planning help:
1. Store their request in state['user_request'].
2. Use the destination_researcher tool to research the destination.
3. Use the itinerary_builder tool to build the itinerary and budget.
4. Use the response_assembler tool to present the final travel plan.

Always be helpful, concise, and use the tools in order.""",
    tools=[
        DelayedAgentTool(agent=destination_researcher),
        DelayedAgentTool(agent=itinerary_builder),
        DelayedAgentTool(agent=response_assembler),
    ],
)

# Alias required by app/__init__.py and adk web
app = root_agent
