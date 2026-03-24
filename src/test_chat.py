"""Level 0 teszt: szöveges beszélgetés az agenttel a terminálban.

Használat:
    python src/test_chat.py

Csak ANTHROPIC_API_KEY kell hozzá. Nincs hang, nincs telefon.
"""

import asyncio
from agent import ConversationAgent, CallContext


async def main():
    agent = ConversationAgent()
    ctx = CallContext(
        customer_name="Kovács János",
        company_name="WebBuilder Kft.",
        purpose="Megkérdezni megkapta-e a levelet a weboldaláról",
        website_url="https://kovacs-janos.hu",
    )

    # Agent greeting
    greeting = await agent.get_greeting(ctx)
    print(f"\nAgent: {greeting}")

    # Conversation loop
    while True:
        try:
            user_input = input("\nTe: ")
        except (EOFError, KeyboardInterrupt):
            print("\n[MEGSZAKÍTVA]")
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            break

        response = await agent.respond(ctx, user_input)
        print(f"Agent: {response}")

        if agent.should_hangup(response):
            print("\n[HÍVÁS VÉGE]")
            break

    # Show transcript
    print("\n--- Transcript ---")
    for msg in ctx.history:
        role = "Agent" if msg["role"] == "assistant" else "Ügyfél"
        print(f"  {role}: {msg['content']}")


if __name__ == "__main__":
    asyncio.run(main())
