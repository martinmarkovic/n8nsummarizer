# controllers/ – Workflow Orchestration

Controllers connect **views** with **models** and external services (n8n, webhooks).

## What Lives Here

- **file_controller.py** – File summarization workflow
- **bulk_summarizer_controller.py** – Bulk summarization
- **transcriber_controller.py** – Single‑file transcription
- **bulk_transcriber_controller.py** – Bulk transcription
- **scanner_controller.py** – Folder scanning flows
- **youtube_summarizer_controller.py** – YouTube summarization

## Responsibilities

- Read user input from views
- Call appropriate model functions (file, HTTP, n8n, transcription)
- Update views with progress, results and errors
- Contain workflow logic, not low‑level details

## Guidelines for New Code

- Dont import Tkinter directly; work against view interfaces
- Dont perform raw HTTP here; call model helpers instead
- Keep methods short and focused on workflow steps
- Log important events via `utils.logger`

## For Agents / AIs

When wiring a new feature (e.g. translation tab):

- Create a new controller (e.g. `translation_controller.py`)
- Accept dependencies (models, view/tab instance) via constructor
- Expose clear methods that the view can bind to buttons (e.g. `on_translate_clicked()`)
