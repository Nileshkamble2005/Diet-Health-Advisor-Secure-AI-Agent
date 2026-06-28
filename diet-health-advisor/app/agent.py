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

import re
import json
import logging
from pydantic import BaseModel, Field

from google.adk.agents import LlmAgent, Context
from google.adk.tools import AgentTool, request_input, McpToolset
from google.adk.workflow import node, START, Edge, Workflow
from google.adk.apps import App
from google.adk.events import RequestInput
from mcp import StdioServerParameters

from app.config import config

logger = logging.getLogger("diet_health_advisor")

# Define Workflow State Schema
class DietAdvisorState(BaseModel):
    user_goal: str = Field(default="")
    dietary_restrictions: str = Field(default="")
    meal_plan: str = Field(default="")
    nutritional_analysis: str = Field(default="")
    approved: bool = Field(default=False)
    feedback: str = Field(default="")
    security_approved: bool = Field(default=False)


# --- 1. Security Checkpoint Node ---
@node
async def security_checkpoint(ctx: Context, node_input: str):
    """
    Checks the user query for prompt injection, PII, and medical safety.
    """
    if not ctx.state:
        ctx.state['approved'] = False
        ctx.state['feedback'] = ""
        ctx.state['security_approved'] = False
        ctx.state['meal_plan'] = ""
        ctx.state['nutritional_analysis'] = ""
        ctx.state['user_goal'] = ""
        ctx.state['dietary_restrictions'] = ""

    user_query = node_input or ""
    
    # PII Scrubbing (redact emails and phone numbers)
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    scrubbed_query = re.sub(email_pattern, "[REDACTED_EMAIL]", user_query)
    scrubbed_query = re.sub(phone_pattern, "[REDACTED_PHONE]", scrubbed_query)
    
    # Prompt Injection Detection
    injection_keywords = ["ignore previous instructions", "system prompt", "translate this into", "you are now a hacker"]
    has_injection = any(kw in scrubbed_query.lower() for kw in injection_keywords)
    
    # Domain-specific Rule: Medical Safety / Out of Scope Check
    medical_keywords = ["prescribe", "cure cancer", "cure diabetes", "treat infection", "medication"]
    is_medical_request = any(kw in scrubbed_query.lower() for kw in medical_keywords)
    
    # Structured JSON Audit Log
    audit_log = {
        "timestamp": ctx.run_id,
        "pii_scrubbed": scrubbed_query != user_query,
        "injection_detected": has_injection,
        "medical_request_detected": is_medical_request,
        "input_length": len(user_query)
    }
    
    if has_injection or is_medical_request:
        audit_log["severity"] = "CRITICAL" if has_injection else "WARNING"
        audit_log["action"] = "BLOCKED"
        logger.warning(json.dumps(audit_log))
        ctx.route = "SECURITY_EVENT"
        ctx.state['feedback'] = "Prompt injection detected" if has_injection else "Out of scope medical request"
        return "Security Check Failed"
    else:
        audit_log["severity"] = "INFO"
        audit_log["action"] = "ALLOWED"
        logger.info(json.dumps(audit_log))
        ctx.route = "clean"
        ctx.state['user_goal'] = scrubbed_query
        ctx.state['security_approved'] = True
        return scrubbed_query


# --- 2. Security Violation Handler Node ---
@node
async def security_violation_handler(ctx: Context, node_input: str):
    """
    Returns a safe disclaimer message in case of security rules violation.
    """
    reason = ctx.state.get('feedback', 'Security Check Violation')
    if "Prompt injection" in reason:
        return "Access Denied: Safety violation detected. Request blocked."
    else:
        return "Access Denied: I am a Diet & Health Advisor. I cannot prescribe medication or provide medical treatment. Please consult a medical professional."


# --- 3. Sub-Agents and Orchestrator Agent ---

# Define the MCP toolset to connect to our local MCP server
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "app.mcp_server"],
    )
)

meal_planner_agent = LlmAgent(
    name="meal_planner_agent",
    model=config.model,
    instruction=(
        "You are a specialized meal planner sub-agent. Your goal is to design "
        "personalized daily or weekly meal plans based on user preferences and restrictions. "
        "Use the get_recipe_details and get_diet_rules tools from the MCP server to search "
        "for healthy recipes and guidelines. Provide direct, clear meal descriptions including "
        "recipes, ingredients, and schedule. Be concise."
    ),
    tools=[mcp_toolset],
)

nutrition_analyst_agent = LlmAgent(
    name="nutrition_analyst_agent",
    model=config.model,
    instruction=(
        "You are a specialized nutrition analyst sub-agent. Your goal is to analyze the "
        "draft meal plan and estimate total calories, protein, carbs, and fats. "
        "Use the search_food_calories tool from the MCP server to find exact values "
        "for specific food items. Provide a breakdown and verify if it matches basic health guidelines. Be concise."
    ),
    tools=[mcp_toolset],
)

orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=config.model,
    instruction=(
        "You are the central Diet & Health Advisor orchestrator. "
        "You receive the user's health goal and dietary requests. "
        "Your task is to coordinate the creation of a healthy meal plan. "
        "First, call the meal_planner_agent to design the meal plan. "
        "Next, call the nutrition_analyst_agent to analyze the plan's calories and macros. "
        "If there is feedback from the user, incorporate their changes and revise the plan. "
        "Summarize the final plan and nutritional breakdown clearly."
    ),
    tools=[
        AgentTool(meal_planner_agent),
        AgentTool(nutrition_analyst_agent),
    ],
)


# --- 4. Human Approval Node (RequestInput) ---
@node
async def request_approval(ctx: Context, node_input: str):
    """
    Pauses execution to ask the user to approve or revise the generated meal plan.
    """
    # Capture current meal plan generated by orchestrator
    if node_input and "Do you approve" not in node_input:
        ctx.state['meal_plan'] = node_input

    # Check if we are resuming from human feedback
    if ctx.resume_inputs:
        user_response = ctx.resume_inputs.get("meal_approval")
        if user_response:
            ur_lower = user_response.lower()
            if "yes" in ur_lower or "approve" in ur_lower or "ok" in ur_lower:
                ctx.state['approved'] = True
                ctx.route = "approved"
                return ctx.state['meal_plan']
            else:
                ctx.state['approved'] = False
                ctx.state['feedback'] = user_response
                ctx.route = "revise"
                return f"Revise plan based on user feedback: {user_response}"

    # Return RequestInput to pause the workflow and display prompt to the user
    return RequestInput(
        interrupt_id="meal_approval",
        message=(
            f"Here is your proposed meal plan:\n\n{ctx.state['meal_plan']}\n\n"
            "Do you approve this plan? Say 'yes' to confirm or tell me what revisions you want."
        ),
        response_schema={"type": "string"}
    )


# --- 5. Final Output Node ---
@node
async def final_node(ctx: Context, node_input: str):
    """
    Returns the final approved meal plan.
    """
    return f"🎉 Meal Plan Approved and Finalized!\n\n{ctx.state['meal_plan']}"


# --- Compile Workflow ---
workflow = Workflow(
    name="diet_advisor_workflow",
    description="Diet & Health Advisor Workflow",
    state_schema=DietAdvisorState,
    edges=[
        Edge(from_node=START, to_node=security_checkpoint),
        Edge(from_node=security_checkpoint, to_node=orchestrator_agent, route="clean"),
        Edge(from_node=security_checkpoint, to_node=security_violation_handler, route="SECURITY_EVENT"),
        Edge(from_node=orchestrator_agent, to_node=request_approval),
        Edge(from_node=request_approval, to_node=final_node, route="approved"),
        Edge(from_node=request_approval, to_node=orchestrator_agent, route="revise"),
    ]
)

# Export the app wrapping the root workflow
app = App(
    root_agent=workflow,
    name="app",
)
