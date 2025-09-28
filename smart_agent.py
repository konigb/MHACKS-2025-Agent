import asyncio
import json
from typing import List, Dict
from pydantic import BaseModel
from uagents import Agent, Context
import httpx  # still needed for Discord webhook

# ------------------------
# Pydantic models
# ------------------------

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

# ------------------------
# Initialize agent
# ------------------------

compliance_agent = Agent(
    name="Compliance",
    seed="alice recovery phrase",
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"]
)

# ------------------------
# Load compliance rules from JSON file
# ------------------------

RULES_FILE = "osha.json"  # path to your JSON file

def load_rules() -> Dict:
    try:
        with open(RULES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rules file: {e}")
        return {}

rules_data = load_rules()

def lookup_rule(state: str, hazard: str) -> Dict[str, str]:
    """
    Check the local JSON file for a compliance rule.
    Fallback: return "No rule found".
    """
    state_rules = rules_data.get(state, {})
    hazard_info = state_rules.get(hazard, {})

    return {
        "rule": hazard_info.get("rule", "No rule found"),
        "consequence": hazard_info.get("consequence", "No consequence found")
    }

# ------------------------
# Enrich violations
# ------------------------

async def enrich_violations(incoming_data: Dict) -> EnrichedMessage:
    state = incoming_data.get("state")
    violations = incoming_data.get("violations", [])
    frame_id = incoming_data.get("frame_id")

    enriched_violations = []

    for v in violations:
        person_id = v["person_id"]
        missing_list = v["missing"]

        person_missing = []
        for hazard_obj in missing_list:
            hazard_name = hazard_obj["item"] if isinstance(hazard_obj, dict) else getattr(hazard_obj, "item", str(hazard_obj))
            rule_info = lookup_rule(state, hazard_name)
            person_missing.append(MissingItem(item=hazard_name, **rule_info))

        enriched_violations.append(EnrichedViolation(person_id=person_id, missing=person_missing))

    return EnrichedMessage(frame_id=frame_id, state=state, violations=enriched_violations)

# ------------------------
# Send alert via Discord Webhook
# ------------------------

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1421689357005361256/F_k9-eYpr8pElRyCEIxDIouiwdq54VpQU7gIFvMbFegbyoqvVpLMP54IoWtQs5xVgNJf"  # <-- replace with your webhook

async def send_discord_alert(message: str):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(DISCORD_WEBHOOK_URL, json={"content": message})
        except Exception as e:
            print(f"Error sending Discord alert: {e}")

# ------------------------
# Handle incoming violation messages
# ------------------------


@compliance_agent.on_message(model=ViolationMessage)
async def handle_violation(ctx: Context, sender: str, msg: ViolationMessage):
    enriched = await enrich_violations(msg.dict())
    
    ctx.logger.info(f"Enriched violations: {enriched.dict()}")

    # Format alert for Discord
    alert_body = f"⚠️ Compliance Alert - Frame {enriched.frame_id}\n"
    for violation in enriched.violations:
        for item in violation.missing:
            alert_body += f"👤 Person {violation.person_id}: {item.item} → {item.rule}, Consequence: {item.consequence}\n"

    # Send alert to Discord webhook
    await send_discord_alert(alert_body)

    # No ctx.reply() here — ExternalContext doesn't support it

# ------------------------
# Startup log
# ------------------------

@compliance_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"Compliance agent running at {compliance_agent.address}")

# ------------------------
# Run agent
# ------------------------

if __name__ == "__main__":
    compliance_agent.run()
