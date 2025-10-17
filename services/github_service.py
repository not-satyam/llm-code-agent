import httpx
import asyncio
import logging
import git # Using GitPython library
from config import get_settings

log = logging.getLogger("uvicorn")
settings = get_settings()

GITHUB_API_BASE = "https://api.github.com"
GITHUB_USER = settings.GITHUB_USER
GITHUB_TOKEN = settings.GITHUB_TOKEN

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

async def setup_repository(local_path: str, repo_name: str, round_index: int) -> git.Repo:
    """
    Manages the repository:
    - Round 1: Creates a new public repo on GitHub and inits locally.
    - Round 2+: Clones the existing repo to the local path.
    """
    repo_url_auth = f"https://{GITHUB_USER}:{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{repo_name}.git"

    async with httpx.AsyncClient(timeout=45.0) as client:
        if round_index == 1:
            log.info(f"[Git] Round 1: Creating new remote repo '{repo_name}'")
            try:
                # 1. Create remote repo
                payload = {"name": repo_name, "private": False, "auto_init": False}
                response = await client.post(f"{GITHUB_API_BASE}/user/repos", json=payload, headers=HEADERS)
                response.raise_for_status()

                # 2. Init local repo
                repo = git.Repo.init(local_path)
                repo.create_remote('origin', repo_url_auth)
                log.info("[Git] Local repo initialized and remote added.")
                return repo

            except httpx.HTTPStatusError as e:
                # Handle "name already exists" error
                if e.response.status_code == 422:
                    log.warning(f"[Git] Repo '{repo_name}' already exists. Attempting to clone.")
                    # Fall through to clone logic
                else:
                    log.error(f"[Git] API error creating repo: {e.response.text}")
                    raise
            except Exception as e:
                log.error(f"[Git] Error initializing repo: {e}")
                raise

        # Round 2+ (or R1 fallback if repo exists)
        log.info(f"[Git] Round {round_index}: Cloning existing repo '{repo_name}'")
        try:
            repo = git.Repo.clone_from(repo_url_auth, local_path)
            log.info("[Git] Repo cloned successfully.")
            return repo
        except git.GitCommandError as e:
            log.error(f"[Git] Failed to clone repo: {e}")
            raise

def publish_changes(repo: git.Repo, task_id: str, round_index: int) -> str:
    """
    Commits all changes in the local repo and pushes to 'main'.
    Returns the commit SHA.
    """
    try:
        log.info("[Git] Configuring git user...")
        repo.config_writer().set_value("user", "name", "LLM Agent Bot").release()
        repo.config_writer().set_value("user", "email", "bot@example.com").release()

        log.info("[Git] Adding all files...")
        repo.git.add(A=True)

        # Check if there are changes staged for commit.
        needs_commit = False
        if not repo.head.is_valid(): # Check if repo has any commits yet (is HEAD valid?)
            # First commit: Check if anything was staged at all compared to an empty repo
             if repo.index.diff(None):
                 needs_commit = True
             else:
                 # This should not happen if the LLM generated files, but good to check
                 log.error("[Git] Initial commit attempted but no files were staged.")
                 raise Exception("Initial commit failed: No files staged.")
        elif repo.is_dirty(index=True): # Subsequent commits: Check if index differs from the last commit (HEAD)
            needs_commit = True

        if not needs_commit:
            log.warning("[Git] No changes staged to commit.")
            # If HEAD exists (not the first commit) return its SHA, otherwise something is wrong
            if repo.head.is_valid():
                 return repo.head.object.hexsha
            else:
                 # Should be unreachable due to the check above, but as a safeguard:
                 log.error("[Git] Inconsistent state: HEAD invalid but no staged files for initial commit.")
                 raise Exception("Commit failed due to inconsistent Git state.")

        # --- The rest of the function (commit, push) ---
        log.info("[Git] Committing changes...")
        commit_message = f"Task: {task_id} | Round: {round_index}"
        repo.index.commit(commit_message)

        commit_sha = repo.head.object.hexsha
        log.info(f"[Git] Commit created: {commit_sha}")

        log.info("[Git] Pushing to origin/main...")
        # Ensure branch is 'main' and push
        repo.git.branch('-M', 'main')
        repo.git.push('--set-upstream', 'origin', 'main', force=True)

        log.info("[Git] Push successful.")
        return commit_sha

    # --- This except block MUST be aligned with the 'try' block above ---
    except git.GitCommandError as e:
        log.error(f"[Git] Failed to publish changes: {e}")
        raise

async def activate_github_pages(repo_name: str) -> str:
    """
    Activates or updates GitHub Pages for the repo.
    Retries on "branch not found" errors.
    """
    pages_api_url = f"{GITHUB_API_BASE}/repos/{GITHUB_USER}/{repo_name}/pages"
    pages_payload = {"source": {"branch": "main", "path": "/"}}

    max_retries = 5
    delay = 3

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                log.info(f"[Pages] Attempt {attempt+1}: Enabling GitHub Pages...")

                # First, try to CREATE pages
                response = await client.post(pages_api_url, json=pages_payload, headers=HEADERS)

                if response.status_code == 409: # 409 Conflict (Pages already exist)
                    log.info("[Pages] Pages already exist. Attempting to update...")
                    # If they exist, UPDATE them
                    response = await client.put(pages_api_url, json=pages_payload, headers=HEADERS)

                response.raise_for_status() # Check for errors on POST or PUT

                pages_url = f"https://{GITHUB_USER}.github.io/{repo_name}/"
                log.info(f"[Pages] GitHub Pages enabled successfully: {pages_url}")
                return pages_url

            except httpx.HTTPStatusError as e:
                # This is the "branch not found" error from the reference
                if e.response.status_code == 422 and "main branch must exist" in e.response.text:
                    log.warning(f"[Pages] GitHub API reports 'main' branch not found. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2 # Exponential backoff
                else:
                    log.error(f"[Pages] API error: {e.response.status_code} - {e.response.text}")
                    raise
            except Exception as e:
                log.error(f"[Pages] Unexpected error: {e}")
                raise

    raise Exception("Failed to activate GitHub Pages after all retries.")