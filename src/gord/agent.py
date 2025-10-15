
from typing import List

from langchain_core.messages import AIMessage

# from gord.prompts import (
#     ACTION_SYSTEM_PROMPT,
#     ANSWER_SYSTEM_PROMPT,
#     PLANNING_SYSTEM_PROMPT,
#     VALIDATION_SYSTEM_PROMPT,
# )

from gord.model import call_llm
from gord.utils.logger import Logger
from gord.utils.ui import show_progress
from gord.schemas import Answer, IsDone, Task, TaskList
from gord.tools import TOOLS


class Agent:
    def __init__(self, max_steps: int = 20, max_steps_per_task: int = 5):
        self.logger = Logger()
        self.max_steps = max_steps           
        self.max_steps_per_task = max_steps_per_task

    @show_progress("Planning tasks...", "Tasks planned")
    def plan_tasks(self, query: str) -> List[Task]:
        tool_descriptions = "\n".join([f"- {t.name}: {t.description}" for t in TOOLS])
        prompt = f"""
        Given the user query: "{query}",
        Create a list of tasks to be completed.
        Example: {{"tasks": [{{"id": 1, "description": "some task", "done": false}}]}}
        """
        system_prompt = PLANNING_SYSTEM_PROMPT.format(tools=tool_descriptions)
        try:
            response = call_llm(prompt, system_prompt=system_prompt, output_schema=TaskList)
            tasks = response.tasks
        except Exception as e:
            self.logger._log(f"Planning failed: {e}")
            tasks = [Task(id=1, description=query, done=False)]
        
        task_dicts = [task.dict() for task in tasks]
        self.logger.log_task_list(task_dicts)
        return tasks

    # ---------- main loop ----------
    def run(self, query: str):
        # Reset state
        step_count = 0
        last_actions = []
        session_outputs = []  # accumulate outputs for the whole session

        breakpoint()
