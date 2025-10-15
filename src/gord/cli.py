from dotenv import load_dotenv

# Load environment variables BEFORE importing any dexter modules
load_dotenv()

from gord.agent import Agent
from gord.utils.intro import print_intro
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory


HELP_TEXT = (
    "Commands:\n"
    "- help: show examples and commands\n"
    "- exit/quit: leave\n"
    "- cancel/stop: request to stop current run (takes effect between steps)\n"
    "Shortcuts:\n"
    "- ESC: request cancel (same as 'cancel')\n"
    "Examples:\n"
    "- Business profile: Tell me everything about the business at 416 Main Street, Medina NY 14103\n"
    "- Underwriting: Generate an underwriting report for 416 Main Street, Medina NY 14103\n"
    "- Ping-only: What does Ping know about 416 Main Street, Medina NY 14103\n"
    "- Deep Underwriting: Deep Underwriting Report for 416 Main Street, Medina NY 14103\n"
    "- Deep Company: Deep Company Profile for 416 Main Street, Medina NY 14103\n"
)

def main():
    print_intro()
    agent = Agent()


    # query = "Tell me everything you can find about 1428 west ave miami FL 33139"

    # agent.run(query)

    # return

    # Create a prompt session with history support
    kb = KeyBindings()

    @kb.add('escape')
    def _(event):
        # Request cancel; will be picked up between steps
        agent.request_cancel()
        print("\nCancel requested (ESC). Will stop between steps.")

    session = PromptSession(history=InMemoryHistory(), key_bindings=kb)

    while True:
        try:
            query = session.prompt(">> ")
            lower = query.lower().strip()
            if lower in ["exit", "quit"]:
                print("Goodbye!")
                break
            if lower in ["help", "h", "?"]:
                print(HELP_TEXT)
                continue
            if lower in ["cancel", "stop"]:
                agent.request_cancel()
                print("Cancel requested. Will stop between steps.")
                continue
            if query:
                agent.run(query)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
