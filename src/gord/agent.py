
from gord.utils.logger import Logger


class Agent:
    def __init__(self, max_steps: int = 20, max_steps_per_task: int = 5):
        self.logger = Logger()
        self.max_steps = max_steps           
        self.max_steps_per_task = max_steps_per_task