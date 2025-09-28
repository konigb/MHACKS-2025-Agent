import json
from typing import List
from pydantic import BaseModel
from uagents import Agent, Context

# Load OSHA rules
with open("osha.json") as f:
    COMPLIANCE_FILE = json.load(f)

# Pydantic models for messages
class ViolationItem(BaseModel):
    item: str

class Violation(BaseModel):
    person_id: int
    missing: List[ViolationItem]

class ViolationMessage(BaseModel):
    frame_id: int
    state: str
    violations: List[Violation]

class MissingItem(BaseModel):
    item: str
    rule: str
    consequence: str

class EnrichedViolation(BaseModel):
    person_id: int
    missing: List[MissingItem]

class EnrichedMessage(BaseModel):
    frame_id: int
    state: str
    violations: List[EnrichedViolation]

# Helper function to enrich violations
def enrich_violations(incoming_data: dict) -> dict:
    state = incoming_data.get("state")
    violations = incoming_data.get("violations", [])
    frame_id = incoming_data.get("frame_id")

    enriched_list = []
    for v in violations:
        person_id = v["person_id"]
        missing_list = v["missing"]

        enriched_missing = []
        for hazard in missing_list:
            violation_info = {
                "item": hazard["item"],
                "rule": "no rule found",
                "consequence": "no consequence found"
            }
            if state in COMPLIANCE_FILE and hazard["item"] in COMPLIANCE_FILE[state]:
                rule_info = COMPLIANCE_FILE[state][hazard["item"]]
                violation_info = {
                    "item": hazard["item"],
                    "rule": rule_info["rule"],
                    "consequence": rule_info["consequence"]
                }
            enriched_missing.append(violation_info)

        enriched_list.append({
            "person_id": person_id,
            "missing": enriched_missing
        })

    return {
        "frame_id": frame_id,
        "state": state,
        "violations": enriched_list
    }

# Initialize agent
compliance_agent = Agent(
    name="Compliance",
    seed="alice recovery phrase",
    endpoint=["http://127.0.0.1:8000/submit"],
    port=8000
)

# Startup event
@compliance_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Compliance Agent started at {compliance_agent.address}")

# Message handler
@compliance_agent.on_message(model=ViolationMessage, replies=EnrichedMessage)
async def handle_violation(ctx: Context, sender: str, msg: ViolationMessage):
    enriched_json = enrich_violations(msg.dict())
    await ctx.send(sender, EnrichedMessage(**enriched_json))
    ctx.logger.info(f"Sent enriched data: {enriched_json}")

if __name__ == "__main__":
    compliance_agent.run()
