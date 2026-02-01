# views/ – Tkinter GUI Layer

This folder contains all user interface code: main window and individual tabs.

## What Lives Here

- **main_window.py** – Application shell and tab registration
- **base_tab.py** – Common base class for all tabs
- **file_tab.py** – File summarizer UI
- **transcriber_tab.py** – Single‑file transcriber UI
- **bulk_summarizer/** – Modular bulk summarizer UI
- **bulk_transcriber/** – Modular bulk transcriber UI
- **bulk_summarizer_tab.py** – Legacy/compat wrapper (still supported)
- **bulk_transcriber_tab.py** – Legacy/compat wrapper (still supported)
- **youtube_summarizer_tab.py** – YouTube summarizer UI
- **(NEW) translation_tab.py** – Placeholder for translation workflows

## Responsibilities

- Layout (frames, labels, buttons, textboxes, progress bars)
- User input collection (but not business logic)
- Delegation of actions to controllers

## Guidelines for New UI

- Use `BaseTab` as the base for new tabs
- Keep tabs focused on presentation and event wiring
- Avoid direct HTTP or filesystem access here
- Prefer composition (helper components) over giant tab classes

## For Agents / AIs

When adding a new tab:

- Create `views/translation_tab.py` (for example)
- Register it in `main_window.py`
- Ensure it exposes a small, clear public API that controllers can use
