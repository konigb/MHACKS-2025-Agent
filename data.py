import asyncio
from uagents import Agent, Context
from models import ViolationMessage, Violation, MissingItem

REQUEST_AGENT_ADDRESS = "agent1qtzku6e8zjf2a8dtwdc39slkj6gztrx2e2gu0fnf8aqnqaeptqa5vmc60sj"

sample_batches = [
    {
        "frame_start": 1,
        "frame_end": 14,
        "state": "Michigan",
        "persons": 1,
        "violations": [
            {"person_id": 1, "missing": [{"item": "hardhat"}, {"item": "mask"}, {"item": "safety vest"}]}
        ]
    },
    {
        "frame_start": 28,
        "frame_end": 57,
        "state": "Michigan",
        "persons": 2,
        "violations": [
            {"person_id": 1, "missing": [{"item": "hardhat"}]},
            {"person_id": 2, "missing": [{"item": "mask"}, {"item": "safety vest"}]}
        ]
    }
]

client_agent = Agent(
    name="ClientSimulator",
    seed="client simulator seed phrase",
    port=8003
)

async def send_batches(ctx: Context):
    while True:
        for batch in sample_batches:
            violations = [
                Violation(
                    person_id=v["person_id"],
                    missing=[MissingItem(item=i["item"]) for i in v["missing"]]
                )
                for v in batch["violations"]
            ]
            msg = ViolationMessage(
                frame_start=batch["frame_start"],
                frame_end=batch["frame_end"],
                state=batch["state"],
                persons=batch.get("persons", len(violations)),
                violations=violations
            )
            ctx.logger.info(f"[ClientSimulator] Sending batch: {batch}")
            await ctx.send(REQUEST_AGENT_ADDRESS, msg)
            await asyncio.sleep(2)

@client_agent.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info(f"[ClientSimulator] Running at {client_agent.address}")
    asyncio.create_task(send_batches(ctx))

if __name__ == "__main__":
    client_agent.run()
