import logging
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, status
from models import TaskRequest
from config import get_settings
import orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uvicorn")

# Load settings once
try:
    settings = get_settings()
except ValueError as e:
    log.critical(f"!!! CONFIGURATION ERROR: {e}")
    log.critical("Please create a .env file (see .env.example) and restart.")
    # Exit if config is missing
    exit(1)


app = FastAPI(
    title="LLM Code Deployment Agent",
    description="Receives tasks, generates code, and deploys to GitHub Pages."
)

@app.post("/api/process-task", status_code=status.HTTP_200_OK)
async def process_task(task: TaskRequest, bg_tasks: BackgroundTasks):
    """
    Main endpoint to receive tasks.
    1. Verifies the secret.
    2. Schedules the main workflow as a background task.
    3. Responds 200 OK immediately.
    """
    
    # 1. Verify Secret
    if task.secret != settings.STUDENT_SECRET:
        log.warning(f"Failed auth attempt for task: {task.task}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid secret"
        )
        
    log.info(f"Task received: {task.task} (Round {task.round}). Queuing for processing.")
    
    # 2. Schedule Background Task
    bg_tasks.add_task(orchestrator.run_task_workflow, task)
    
    # 3. Respond Immediately
    return {"message": "Task received and is being processed."}

@app.get("/", status_code=status.HTTP_200_OK)
def read_root():
    return {"status": "ok", "message": "LLM Agent is running."}

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "ok"}