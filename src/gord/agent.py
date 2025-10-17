
from typing import List, Optional

from langchain_core.messages import AIMessage

from gord.prompts import (
    ACTION_SYSTEM_PROMPT,
    ACTION_SYSTEM_PROMPT_PING_ONLY,
    ANSWER_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT_BUSINESS,
    PLANNING_SYSTEM_PROMPT_UNDERWRITING,
    PLANNING_SYSTEM_PROMPT_PING_ONLY,
    PLANNING_SYSTEM_PROMPT_UNDERWRITING_DEEP,
    PLANNING_SYSTEM_PROMPT_BUSINESS_DEEP,
    BUSINESS_ANSWER_SYSTEM_PROMPT,
    UNDERWRITING_REPORT_PROMPT,
    PING_ONLY_ANSWER_SYSTEM_PROMPT,
)

from gord.model import call_llm
from gord.utils.logger import Logger
from gord.utils.ui import show_progress
from gord.schemas import Answer, IsDone, Task, TaskList, RouteDecision, Intent
from gord.tools import TOOLS
from gord.settings import SEARCH_ENGINE
from gord import metrics



class Agent:
    def __init__(self, max_steps: int = 30, max_steps_per_task: int = 5):
        self.logger = Logger()
        self.max_steps = max_steps       
        self.max_steps_per_task = max_steps_per_task
        self.route_decision: Optional[RouteDecision] = None
        import threading
        self._cancel_event = threading.Event()

    def request_cancel(self):
        self._cancel_event.set()

    def reset_cancel(self):
        self._cancel_event.clear()

    def _check_cancel(self):
        if self._cancel_event.is_set():
            raise KeyboardInterrupt()

    @show_progress("Routing...", "Routed")
    def route(self, query: str) -> RouteDecision:
        self._check_cancel()
        prompt = f"Classify this query and extract address if applicable: {query}"
        try:
            decision = call_llm(prompt, system_prompt=ROUTER_SYSTEM_PROMPT, output_schema=RouteDecision)
            return decision
        except Exception as e:
            self.logger._log(f"Routing failed: {e}")
            return RouteDecision(intent=Intent.GENERAL_QA, address=None, rationale="Fallback after error.")

    @show_progress("Planning tasks...", "Tasks planned")
    def plan_tasks(self, query: str) -> List[Task]:
        self._check_cancel()
        selected_tools = self._select_tools_for_intent()
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in selected_tools])
        # Incorporate routing decision context
        intent = self.route_decision.intent if self.route_decision else Intent.GENERAL_QA
        addr = self.route_decision.address if self.route_decision else None
        prompt = f"""
        User query: "{query}"
        Intent: {intent}
        Address: {addr or 'N/A'}
        
        Tools available:
        {tool_descriptions}

        Create a list of tasks to be completed.
        Example: {{"tasks": [{{"id": 1, "description": "some task", "done": false}}]}}
        """
        # Choose planning system prompt by intent
        if intent == Intent.UNDERWRITING_REPORT:
            system_prompt = PLANNING_SYSTEM_PROMPT_UNDERWRITING
        elif intent == Intent.BUSINESS_PROFILE:
            system_prompt = PLANNING_SYSTEM_PROMPT_BUSINESS
        elif intent == Intent.PING_PROPERTY_SUMMARY:
            system_prompt = PLANNING_SYSTEM_PROMPT_PING_ONLY
        elif intent == Intent.DEEP_UNDERWRITING_REPORT:
            system_prompt = PLANNING_SYSTEM_PROMPT_UNDERWRITING_DEEP
        elif intent == Intent.DEEP_COMPANY_PROFILE:
            system_prompt = PLANNING_SYSTEM_PROMPT_BUSINESS_DEEP
        else:
            system_prompt = PLANNING_SYSTEM_PROMPT
        try:
            response = call_llm(prompt, system_prompt=system_prompt, output_schema=TaskList)
            tasks = response.tasks
        except Exception as e:
            self.logger._log(f"Planning failed: {e}")
            tasks = [Task(id=1, description=query, done=False)]
        
        task_dicts = [task.dict() for task in tasks]
        self.logger.log_task_list(task_dicts)
        return tasks

    @show_progress("Thinking...", "")
    def ask_for_actions(self, task_desc: str, last_outputs: str = "") -> AIMessage:
        """ ask LLM what to do  """
        self._check_cancel()
        # last_outputs = textual feedback of what we just tried
        intent = self.route_decision.intent if self.route_decision else Intent.GENERAL_QA
        address = self.route_decision.address if self.route_decision else None
        prompt = f"""
        We are working on: "{task_desc}".
        Intent: {intent}
        Address: {address or 'N/A'}
        Here is a history of tool outputs from the session so far: {last_outputs}

        Based on the task and the outputs, what should be the next step?
        """
        try:
            if intent == Intent.PING_PROPERTY_SUMMARY:
                return call_llm(prompt, system_prompt=ACTION_SYSTEM_PROMPT_PING_ONLY, tools=self._select_tools_for_intent())
            return call_llm(prompt, system_prompt=ACTION_SYSTEM_PROMPT, tools=self._select_tools_for_intent())
        except Exception as e:
            self.logger._log(f"ask_for_actions failed: {e}")
            return AIMessage(content="Failed to get actions.")

    @show_progress("Validating...", "")
    def ask_if_done(self, task_desc: str, recent_results: str) -> bool:
        """ ask LLM if task is done """
        self._check_cancel()
        prompt = f"""
        We were trying to complete the task: "{task_desc}".
        Here is a history of tool outputs from the session so far: {recent_results}

        Is the task done?
        """
        try:
            resp = call_llm(prompt, system_prompt=VALIDATION_SYSTEM_PROMPT, output_schema=IsDone)
            return resp.done
        except:
            return False

    def _execute_tool(self, tool, tool_name: str, inp_args):
        """Execute a tool with progress indication."""
        # Create a dynamic decorator with the tool name
        @show_progress(f"Executing {tool_name}...", "")
        def run_tool():
            self._check_cancel()
            return tool.run(inp_args)
        return run_tool()
    
    def confirm_action(self, tool: str, input_str: str) -> bool:
        # In production you'd ask the user; here we just log and auto-confirm
        # Risky tools are not implemented in this version.
        return True

    def run(self, query: str):
        """Main agent loop."""
        metrics.reset() # Reset state
        self.reset_cancel()
        step_count = 0
        last_actions = []
        session_outputs = []  # accumulate outputs for the whole session

        # Route first
        self.route_decision = self.route(query)
        self.logger._log(f"Routed intent: {self.route_decision.intent} | address: {self.route_decision.address or 'N/A'}")

        # Plan tasks
        tasks = self.plan_tasks(query)


        # If no tasks were created, query is out of scope - answer directly
        if not tasks:
            answer = self._generate_answer(query, session_outputs)
            self.logger.log_summary(answer)
            return answer

        # Main agent loop
        while any(not t.done for t in tasks):
            if step_count >= self.max_steps:
                self.logger._log("Global max steps reached — aborting to avoid runaway loop.")
                break

            task = next(t for t in tasks if not t.done)
            self.logger.log_task_start(task.description)

            per_task_steps = 0
            while per_task_steps < self.max_steps_per_task:
                if step_count >= self.max_steps:
                    self.logger._log("Global max steps reached — stopping.")
                    return

                ai_message = self.ask_for_actions(task.description, last_outputs="\n".join(session_outputs))
                
                if not ai_message.tool_calls:
                    # No tool calls means either the task is done or cannot be done with tools
                    # Always mark as done to avoid infinite loops
                    # The final answer generation will provide an appropriate response
                    task.done = True
                    self.logger.log_task_done(task.description)
                    break

                for tool_call in ai_message.tool_calls:
                    self._check_cancel()
                    if step_count >= self.max_steps:
                        break

                    tool_name = tool_call["name"]
                    inp_args = tool_call["args"]
                    action_sig = f"{tool_name}:{inp_args}"

                    # stuck detection
                    last_actions.append(action_sig)
                    if len(last_actions) > 4:
                        last_actions = last_actions[-4:]
                    if len(set(last_actions)) == 1 and len(last_actions) == 4:
                        self.logger._log("Detected repeating action — aborting to avoid loop.")
                        return
                    
                    tool_to_run = next((t for t in TOOLS if t.name == tool_name), None)
                    if tool_to_run and self.confirm_action(tool_name, str(inp_args)):
                        try:
                            result = self._execute_tool(tool_to_run, tool_name, inp_args)
                            self.logger.log_tool_run(tool_name, f"{result}")
                            session_outputs.append(f"Output of {tool_name} with args {inp_args}: {result}")
                        except Exception as e:
                            self.logger._log(f"Tool execution failed: {e}")
                            session_outputs.append(f"Error from {tool_name} with args {inp_args}: {e}")
                    else:
                        self.logger._log(f"Invalid tool: {tool_name}")

                    step_count += 1
                    per_task_steps += 1

                # check after this batch if task seems done
                if self.ask_if_done(task.description, "\n".join(session_outputs)):
                    task.done = True
                    self.logger.log_task_done(task.description)
                    break

        # Generate answer based on all collected data
        self._check_cancel()
        answer = self._generate_answer(query, session_outputs)
        self.logger.log_summary(answer)
        # Print API usage metrics at end
        self.logger.log_metrics(metrics.snapshot())
        return answer
    
    @show_progress("Generating answer...", "Answer ready")
    def _generate_answer(self, query: str, session_outputs: list) -> str:
        """Generate the final answer based on collected data."""
        all_results = "\n\n".join(session_outputs) if session_outputs else "No data was collected."
        intent = self.route_decision.intent if self.route_decision else Intent.GENERAL_QA
        address = self.route_decision.address if self.route_decision else None
        answer_prompt = f"""
        Original user query: "{query}"
        Intent: {intent}
        Address: {address or 'N/A'}

        Data and results collected from tools:
        {all_results}
        """
        # Choose answer system prompt by intent
        if intent == Intent.UNDERWRITING_REPORT:
            system_prompt = UNDERWRITING_REPORT_PROMPT
        elif intent == Intent.BUSINESS_PROFILE:
            system_prompt = BUSINESS_ANSWER_SYSTEM_PROMPT
        elif intent in (Intent.DEEP_UNDERWRITING_REPORT, Intent.DEEP_COMPANY_PROFILE):
            # Deep modes share the same answer formats as their standard counterparts
            system_prompt = UNDERWRITING_REPORT_PROMPT if intent == Intent.DEEP_UNDERWRITING_REPORT else BUSINESS_ANSWER_SYSTEM_PROMPT
        elif intent == Intent.PING_PROPERTY_SUMMARY:
            system_prompt = PING_ONLY_ANSWER_SYSTEM_PROMPT
        else:
            system_prompt = ANSWER_SYSTEM_PROMPT

        answer_obj = call_llm(answer_prompt, system_prompt=system_prompt, output_schema=Answer)
        return answer_obj.answer

    def _select_tools_for_intent(self):
        "tool selection by intent/settings"
        intent = self.route_decision.intent if self.route_decision else Intent.GENERAL_QA
        # Always start with Ping AOA
        selected = []
        ping_tool = next((t for t in TOOLS if t.name == 'ping_aoa_search'), None)
        if ping_tool:
            selected.append(ping_tool)

        # "Deep search" includes both Google and Brave and Google Images
        if intent in (Intent.DEEP_UNDERWRITING_REPORT, Intent.DEEP_COMPANY_PROFILE):
            g_web = next((t for t in TOOLS if t.name == 'google_web_search'), None)
            g_img = next((t for t in TOOLS if t.name == 'google_image_search'), None)
            brave = next((t for t in TOOLS if t.name == 'brave_search'), None)
            for t in (g_web, g_img, brave):
                if t:
                    selected.append(t)
            return selected

        if intent == Intent.PING_PROPERTY_SUMMARY:
            return selected

        if SEARCH_ENGINE == 'google':
            g_web = next((t for t in TOOLS if t.name == 'google_web_search'), None)
            g_img = next((t for t in TOOLS if t.name == 'google_image_search'), None)
            for t in (g_web, g_img):
                if t:
                    selected.append(t)
        else:  # brave
            brave = next((t for t in TOOLS if t.name == 'brave_search'), None)
            if brave:
                selected.append(brave)

        return selected
