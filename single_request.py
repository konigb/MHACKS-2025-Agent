import asyncio
from typing import List
from pydantic import BaseModel
from uagents import Agent, Context

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

# Initialize agent
request_agent = Agent(
    name="RequestAgent",
    seed="request agent seed",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"]
)

# Startup event: send a test message to the compliance agent
@request_agent.on_event("startup")
async def send_violation(ctx: Context):
    compliance_address = "agent1qww3ju3h6kfcuqf54gkghvt2pqe8qp97a7nzm2vp8plfxflc0epzcjsv79t"  # Replace with your Compliance agent address

    message = ViolationMessage(
        frame_id=123,
        state="Michigan",
        violations=[Violation(person_id=1, missing=[ViolationItem(item="safety_goggles")])]
    )

    ctx.logger.info(f"Sending violation message to Compliance agent: {message.dict()}")
    await ctx.send(compliance_address, message)

# Handle enriched response
@request_agent.on_message(model=EnrichedMessage)
async def handle_response(ctx: Context, sender: str, msg: EnrichedMessage):
    ctx.logger.info(f"Received enriched data from {sender}: {msg.dict()}")

if __name__ == "__main__":
    request_agent.run()
