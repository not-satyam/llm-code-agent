import logging
import asyncio

from models import TaskRequest
from config import get_settings
from services import file_service, llm_service, github_service, notification_service

log = logging.getLogger("uvicorn")
settings = get_settings()

async def run_task_workflow(task: TaskRequest):
    """
    The main orchestration function that runs in the background.
    """
    log.info(f"--- [START] Task: {task.task}, Round: {task.round} ---")
    
    repo_name = task.task.replace(' ', '-').lower()
    
    try:
        # 1. Prepare local directory
        local_path = file_service.prepare_task_directory(task.task)

        # 2. Setup GitHub Repo (Clone or Create)
        repo = await github_service.setup_repository(
            local_path=local_path,
            repo_name=repo_name,
            round_index=task.round
        )

        # 3. Prepare LLM inputs
        image_parts, attachment_names = file_service.process_attachments_for_llm(task.attachments)
        
        prompt_text = llm_service.create_llm_prompt(
            brief=task.brief,
            round_index=task.round,
            attachment_names=attachment_names
        )

        # 4. Call LLM for code
        generated_data = await llm_service.generate_code(prompt_text, image_parts)
        
        # 5. Save LLM files (index.html, etc.)
        file_service.save_llm_files(local_path, generated_data.get("files", []))
        
        # 6. Save Attachments (data.csv, etc.)
        file_service.save_attachment_files(local_path, task.attachments)
        
        # 7. Publish to GitHub
        commit_sha = github_service.publish_changes(repo, task.task, task.round)
        
        # 8. Activate GitHub Pages
        # Give GitHub a moment to process the push before activating pages
        await asyncio.sleep(5) 
        pages_url = await github_service.activate_github_pages(repo_name)
        
        # 9. Notify Evaluation Server
        repo_url = f"https://github.com/{settings.GITHUB_USER}/{repo_name}"
        
        payload = {
            "email": task.email,
            "task": task.task,
            "round": task.round,
            "nonce": task.nonce,
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        await notification_service.notify_evaluator(task.evaluation_url, payload)

        log.info(f"--- [SUCCESS] Task: {task.task}, Round: {task.round} ---")

    except Exception as e:
        log.critical(f"--- [FAILED] Task: {task.task}, Round: {task.round} ---")
        log.critical(f"Error: {e}", exc_info=True)
        # Optionally, you could try to notify the server of the failure here.