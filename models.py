from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

class Attachment(BaseModel):
    """
    Represents an attachment provided in the task payload.
    The 'url' is expected to be a data URI (e.g., base64 encoded file).
    """
    name: str = Field(..., description="Name of the attached file (e.g., 'sample.png')")
    url: str = Field(..., description="The content encoded as a data URI")

class TaskRequest(BaseModel):
    """
    The main model representing the task request sent by the evaluation server.
    """
    email: EmailStr = Field(..., description="Student email ID")
    secret: str = Field(..., description="Student-provided secret")
    task: str = Field(..., description="A unique task ID")
    round: int = Field(..., description="The round index (e.g., 1)")
    nonce: str = Field(..., description="A unique token to pass back")
    brief: str = Field(..., description="Brief description of what the app needs to do")
    checks: Optional[List[str]] = Field([], description="Evaluation checks")
    evaluation_url: str = Field(..., description="URL to send repo & commit details")
    attachments: Optional[List[Attachment]] = Field([], description="Attachments encoded as data URIs")