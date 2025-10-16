from dotenv import load_dotenv

# Load environment variables BEFORE importing any dexter modules
load_dotenv()

from gord.agent import Agent
from gord.utils.intro import print_intro
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from gord.doc_ingest import extract_dropped_file, summarize_pdf
from gord.sovfixer import start_and_poll
from gord.model import call_llm
from gord.schemas import Answer, SOVIntake
from gord.prompts import SOV_PARSE_SYSTEM_PROMPT
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
            # Drag-and-drop file handling (PDF or Excel)
            drop_path = extract_dropped_file(query)
            if drop_path:
                try:
                    fname, size, sha = summarize_pdf(drop_path)
                    metrics.increment('doc_dropped', 1)
                    print(f"File received: {fname} ({size} bytes)\nSHA256: {sha}")
                except Exception as e:
                    print(f"Error reading file: {e}")
                # Kick off SOVFixer async flow and download outputs
                try:
                    ok, final_resp, outputs = start_and_poll(drop_path, env="staging", interval=2.5, timeout=900, outdir=".")
                except Exception as e:
                    print(f"SOVFixer error: {e}")
                    continue
                # If failed, tell the user and continue
                result_status = ((final_resp.get('result') or {}).get('status') if isinstance(final_resp, dict) else None)
                if not ok or (result_status and str(result_status).upper() not in ("SUCCESS",)):
                    print("SOV processing failed. See above logs for details.")
                    continue
                # If success, look for JSON output and summarize it via LLM
                json_paths = [p for p in outputs if str(p).lower().endswith('.json')]
                if not json_paths:
                    print("No JSON output found to summarize.")
                    continue
                try:
                    with open(json_paths[0], 'r', encoding='utf-8') as fh:
                        json_text = fh.read()
                    prompt = (
                        "You are an assistant analyzing a Statement of Values (SOV) JSON output from a document processing pipeline.\n"
                        "Summarize key points succinctly for underwriting:\n"
                        "- Document type identified\n"
                        "- Number of locations/records\n"
                        "- Notable data quality issues or missing fields\n"
                        "- Any clear red flags or follow-ups\n"
                        "Keep it brief and clear."
                    )
                    full_prompt = f"{prompt}\n\nJSON:\n{json_text[:200000]}"
                    answer = call_llm(full_prompt, output_schema=Answer)
                    print("\nSOV SUMMARY:\n" + answer.answer)

                    # Extract locations for routing decision
                    intake = call_llm(f"Extract locations from this SOV JSON:\n\n{json_text[:200000]}", system_prompt=SOV_PARSE_SYSTEM_PROMPT, output_schema=SOVIntake)
                    found = int(getattr(intake, 'num_locations', 0) or 0)
                    if found > 0:
                        # Show sample addresses
                        addrs = getattr(intake, 'addresses', []) or []
                        if addrs:
                            print("\nFound addresses:")
                            for i, a in enumerate(addrs[:5], 1):
                                print(f"  {i}. {a}")
                        # Ask whether to route to agent
                        cont = session.prompt("\nRoute to agent now? [y/N]: ").strip().lower()
                        if cont in ("y", "yes"):
                            chosen = None
                            if addrs:
                                sel = session.prompt("Address to analyze [1]: ").strip()
                                if not sel:
                                    chosen = addrs[0]
                                else:
                                    try:
                                        idx = max(1, min(len(addrs), int(sel)))
                                        chosen = addrs[idx-1]
                                    except Exception:
                                        chosen = sel  # treat as custom address
                            else:
                                chosen = session.prompt("Enter an address to analyze: ").strip()
                            if chosen:
                                q = f"Deep Underwriting Report for: {chosen}"
                                agent.run(q)
                except Exception as e:
                    print(f"Failed to summarize or route: {e}")
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
