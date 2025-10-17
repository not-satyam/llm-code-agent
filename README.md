---
title: LLM Code Agent
sdk: docker
app_port: 7860
---

# llm-code-agent
My Python agent for the LLM code project.

# LLM Code Deployment Agent

This project is a FastAPI application designed to automatically receive tasks, generate code using a Large Language Model (Gemini), and deploy the resulting static site to GitHub Pages.

It handles multi-round tasks, allowing for initial creation (Round 1) and subsequent revisions (Round 2+).

## Features

- **FastAPI Endpoint**: A single endpoint (`/api/process-task`) to receive JSON task payloads.
- **Background Processing**: Immediately responds `200 OK` and performs all work in the background.
- **LLM Code Generation**: Uses the Gemini API to generate `index.html`, `README.md`, and `LICENSE` files.
- **Multimodal Input**: Can process image attachments as context for the LLM.
- **GitHub Integration**:
  - Automatically creates a new public repository (Round 1).
  - Clones and updates existing repositories (Round 2+).
  - Uses `GitPython` for local git operations.
  - Uses `httpx` for direct GitHub API calls (repo creation, Pages activation).
- **GitHub Pages**: Automatically enables or updates the GitHub Pages deployment.
- **Robust Error Handling**: Includes retries with exponential backoff for all external API calls (LLM, GitHub, Notification).

## Deployment (Hugging Face)

This app is designed to be deployed on **Hugging Face Spaces**.

1.  Create a new Space on Hugging Face, selecting "Docker" as the SDK.
2.  Push this code to the Hugging Face git repository.
3.  Go to the Space's **Settings** page.
4.  Add your secrets (`GOOGLE_API_KEY`, `GITHUB_TOKEN`, `GITHUB_USER`, `STUDENT_SECRET`) under **"Space secrets"**.
5.  The Space will build the `Dockerfile` and start the app automatically.
6.  Your public URL will be `https://[your-space-name].hf.space/api/process-task`.

## How to Run (For Local Testing)

1.  **Create `.env` file**:
    -   Copy `.env.example` to `.env`.
    -   Fill in your `GOOGLE_API_KEY`, `GITHUB_TOKEN`, `GITHUB_USER`, and `STUDENT_SECRET`.

2.  **Build the Docker Container**:
    ```sh
    docker build -t llm-agent .
    ```

3.  **Run the Docker Container**:
    ```sh
    # This maps port 8000 on your laptop to port 7860 inside the container
    docker run -p 8000:7860 --env-file .env llm-agent
    ```

4.  **Test**:
    -   Your server is now running at `http://localhost:8000`.