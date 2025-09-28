import asyncio
from typing import List, Dict
from pydantic import BaseModel
from uagents import Agent, Context

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

request_agent = Agent(
    name="RequestAgent",
    seed="request agent seed",
    port=8001,
    endpoint=["http://127.0.0.1:8001/submit"]
)

# ------------------------
# Helper: convert YOLOX detections to ViolationMessage
# ------------------------

def build_violation_message(frame_id: int, state: str, detections: Dict[int, List[str]]) -> ViolationMessage:
    """
    detections: {person_id: ["safety_goggles", "hardhat"]}
    """
    violations = [
        Violation(person_id=pid, missing=[ViolationItem(item=i) for i in items])
        for pid, items in detections.items()
    ]
    return ViolationMessage(frame_id=frame_id, state=state, violations=violations)

# ------------------------
# Simulate continuous YOLOX feed
# ------------------------

async def simulate_camera_feed(ctx: Context):
    """
    Replace this function with your real YOLOX frame detection loop.
    """
    compliance_address = "agent1qww3ju3h6kfcuqf54gkghvt2pqe8qp97a7nzm2vp8plfxflc0epzcjsv79t"  # Replace with your Compliance agent address
    frame_id = 0

    while True:
        frame_id += 1

        # Simulated YOLOX detections for this frame
        # {person_id: [list of missing items]}
        detections = {
            1: ["safety_goggles"],
            2: ["hardhat", "gloves"]
        }

        message = build_violation_message(frame_id=frame_id, state="Michigan", detections=detections)

        ctx.logger.info(f"Sending violation message for frame {frame_id}: {message.dict()}")
        await ctx.send(compliance_address, message)

        await asyncio.sleep(10)  # simulate 1 FPS; adjust to your video frame rate

# ------------------------
# Startup: begin continuous feed
# ------------------------

@request_agent.on_event("startup")
async def start_feed(ctx: Context):
    ctx.logger.info(f"Request agent started with address {request_agent.address}")
    asyncio.create_task(simulate_camera_feed(ctx))

# ------------------------
# Handle enriched response
# ------------------------

@request_agent.on_message(model=EnrichedMessage)
async def handle_response(ctx: Context, sender: str, msg: EnrichedMessage):
    ctx.logger.info(f"Received enriched data from {sender}: {msg.dict()}")

# ------------------------
# Run agent
# ------------------------

if __name__ == "__main__":
    request_agent.run()
