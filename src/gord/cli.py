from dotenv import load_dotenv

# Load environment variables BEFORE importing any dexter modules
load_dotenv()

from gord.agent import Agent
from gord.utils.intro import print_intro
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from gord.doc_ingest import extract_pdf_path, summarize_pdf
from gord import metrics

COOL_ADDRESSES = [
    "416 Main Street, Medina NY 14103",
    "1 Rocket Rd, Hawthorne, CA 90250, US",
    "54298 Boca Chica Blvd, Starbase, Texas,"
    # Add more addresses as needed
]

def generate_help_text():
    examples = {
        "Business profile": "Tell me everything about the business at {address}",
        "Underwriting": "Generate an underwriting report for {address}",
        "Ping-only": "What does Ping know about {address}",
        "Deep Underwriting": "Deep Underwriting Report for {address}",
        "Deep Company": "Deep Company Profile for {address}",
    }
    
    example_lines = []
    for example_type, template in examples.items():
        example_lines.append(f"{example_type}:")
        for address in COOL_ADDRESSES:
            example_lines.append(f"  - {template.format(address=address)}")
        example_lines.append("")  # Blank line for readability
    
    examples_section = "\n".join(example_lines)
    
    help_text = (
        "Commands:\n"
        "- help: show examples and commands\n"
        "- exit/quit: leave\n"
        "- cancel/stop: request to stop current run (takes effect between steps)\n"
        "Shortcuts:\n"
        "- ESC: request cancel (same as 'cancel')\n"
        "Examples:\n"
        f"{examples_section}"
    )
    
    return help_text

HELP_TEXT = generate_help_text()

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
            # Drag-and-drop PDF handling
            pdf_path = extract_pdf_path(query)
            if pdf_path:
                try:
                    fname, size, sha = summarize_pdf(pdf_path)
                    metrics.increment('pdf_dropped', 1)
                    print(f"PDF received: {fname} ({size} bytes)\nSHA256: {sha}")
                    print("(Webhook/API call not yet configured — coming next.)")
                except Exception as e:
                    print(f"Error processing PDF: {e}")
                continue
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
