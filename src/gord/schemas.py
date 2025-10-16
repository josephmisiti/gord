from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Task(BaseModel):
    """Represents a single task in a task list."""
    id: int = Field(..., description="Unique identifier for the task.")
    description: str = Field(..., description="The description of the task.")
    done: bool = Field(False, description="Whether the task is completed.")

class TaskList(BaseModel):
    """Represents a list of tasks."""
    tasks: List[Task] = Field(..., description="The list of tasks.")

class IsDone(BaseModel):
    """Represents the boolean status of a task."""
    done: bool = Field(..., description="Whether the task is done or not.")

class Answer(BaseModel):
    """Represents an answer to the user's query."""
    answer: str = Field(..., description="A comprehensive answer to the user's query, including relevant numbers, data, reasoning, and insights.")


class Intent(str, Enum):
    """Supported high-level intents for routing."""
    UNDERWRITING_REPORT = "UNDERWRITING_REPORT"
    BUSINESS_PROFILE = "BUSINESS_PROFILE"
    GENERAL_QA = "GENERAL_QA"
    PING_PROPERTY_SUMMARY = "PING_PROPERTY_SUMMARY"
    DEEP_UNDERWRITING_REPORT = "DEEP_UNDERWRITING_REPORT"
    DEEP_COMPANY_PROFILE = "DEEP_COMPANY_PROFILE"


class RouteDecision(BaseModel):
    """Router output indicating which mode to use and any extracted entities."""
    intent: Intent = Field(..., description="Which path to take for answering the query.")
    address: Optional[str] = Field(None, description="Normalized address if present/required for the intent.")
    rationale: Optional[str] = Field(None, description="Brief reasoning for the routing decision.")


class SOVIntake(BaseModel):
    """Structured extraction from an SOV JSON output for routing decisions."""
    num_locations: int = Field(0, description="Estimated number of distinct locations/records in the SOV.")
    addresses: List[str] = Field(default_factory=list, description="A list of up to 10 address strings found.")
