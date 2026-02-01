# models/ – Data, HTTP and Workflow Helpers

This folder contains **non‑GUI logic**: data structures, file handling and HTTP helpers used by controllers.

## What Lives Here

- **file_model.py** – Represents files and their metadata
- **file_scanner.py** – File system scanning helpers (single and bulk)
- **http_client.py** – HTTP requests to n8n / webhooks / APIs
- **n8n_model.py** & `models/n8n/` – n8n‑specific helpers
- **transcribe_model.py** & `models/transcription/` – audio/video transcription model helpers

## Responsibilities

- Encapsulate IO and integration logic
- Provide simple, high‑level methods for controllers
- Never import Tkinter or view classes

## Guidelines for New Code

- One responsibility per module when possible
- Expose small, composable functions / classes
- Keep functions side‑effect aware (log, dont print)
- Validate inputs early and return clear error information

## For Agents / AIs

When adding a new workflow integration (e.g. translation):

- Add a new model module here (e.g. `translation_model.py`)
- Keep all HTTP and payload construction here
- Expose clear methods like `send_to_webhook(file_path, config)`
- Let controllers decide **when** to call these methods, views just collect inputs
