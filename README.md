# n8nsummarizer v6.0

Small desktop helper for n8n-based summarization, transcription, and (upcoming) translation workflows.

## Purpose

- Provide a local GUI to trigger n8n workflows (via webhooks or HTTP APIs)
- Handle file selection, basic pre‑validation and progress display
- Keep logic cleanly separated into **models**, **views**, and **controllers**

This README is intentionally concise so humans, AIs, and agents can quickly understand the structure and intent.

## High‑Level Architecture (MVC)

- **models/** – Data and integration layer
  - File metadata and scanning
  - HTTP client for talking to n8n / webhooks
  - n8n‑specific model helpers
- **views/** – Tkinter GUI layer
  - Main window and all tabs
  - Pure presentation and user input controls
- **controllers/** – Orchestrate workflows
  - Glue between views, models, and n8n
  - No direct UI widgets, no low‑level HTTP here

Main entry point: `main.py` (creates the main window, wires controllers and views).

## Tabs (v6.0)

1. **YouTube Summarizer** – Summarize YouTube videos via n8n
2. **File Summarizer** – Summarize local files
3. **Scanner** – Scan folders and prepare batches
4. **Transcriber** – Single‑file transcription
5. **Bulk Transcriber** – Bulk folder transcription
6. **Translation (NEW, basic)** – Placeholder tab for upcoming translation workflows

The translation tab currently only offers basic UI (file picker + two text boxes) and does **not** call any backend yet.

## Conventions

- Prefer small, focused modules over monoliths
- Keep business logic in **controllers** and **models**, not in views
- Use `.env` for configuration and preferences (BULK_* and n8n settings)
- Keep documentation short and task‑oriented

## For Agents / Tools

When extending this project:

- Put GUI changes in `views/`
- Put HTTP/n8n logic in `models/` (or `models/n8n/`)
- Put coordination logic in `controllers/`
- Update the relevant folder‑level README with any new concepts or invariants
