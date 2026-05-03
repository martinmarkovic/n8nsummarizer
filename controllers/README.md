# Controllers Layer

Orchestrates workflows between views and models. Controllers sit between the UI layer (views) and the business logic layer (models), handling user interactions, coordinating workflows, and updating the UI through view methods.

## Purpose

Controllers are responsible for:
- Receiving user input from views
- Coordinating workflows between models
- Updating views with results
- Managing background threads for long-running operations
- Persisting user preferences via SettingsManager

Controllers **never** touch UI elements directly or import tkinter components.

## Contents

| File | Tab | Responsibility | Models Used |
|------|-----|----------------|-------------|
| `file_controller.py` | File Summarizer | File summarization workflow | FileModel, N8NModel |
| `youtube_summarizer_controller.py` | YouTube Summarizer | YouTube video download + summarization | TranscribeModel, N8NModel |
| `transcriber_controller.py` | Transcriber | Single file transcription | TranscribeModel, N8NModel |
| `bulk_summarizer_controller.py` | Bulk Summarizer | Bulk file summarization | N8NModel |
| `bulk_transcriber_controller.py` | Bulk Transcriber | Bulk media transcription | TranscribeModel |
| `translation_controller.py` | Translation | Text translation workflow | TranslationModel |
| `video_subtitler_controller.py` | Video Subtitler | Video download + transcription + translation + subtitle burning | VideoSubtitlerModel, TranscribeModel, TranslationModel |
| `downloader_controller.py` | Downloader | Video downloading from multiple platforms | VideoDownloader (router) |

## Architecture Pattern

All controllers follow a standard pattern:

1. **Initialization**: Receive view reference and bind callbacks
2. **Callback Handling**: Implement view callback methods
3. **Model Coordination**: Call appropriate model methods
4. **View Updates**: Update UI through view methods (never direct UI manipulation)

### Example Pattern

```python
class ExampleController:
    def __init__(self, view):
        self.view = view
        self.model = SomeModel()
        
        # Bind view callbacks
        self.view.on_action = self.handle_action
        
    def handle_action(self, data):
        # Call model
        result = self.model.process(data)
        
        # Update view
        self.view.show_result(result)
```

## Threading

Controllers using background threads for long-running operations:

| Controller | Thread Usage | Purpose |
|------------|--------------|---------|
| `BulkSummarizerController` | ✅ | Process multiple files without UI freezing |
| `BulkTranscriberController` | ✅ | Transcribe multiple media files in background |
| `VideoSubtitlerController` | ✅ | Handle complete video processing pipeline |

Threading pattern:
```python
thread = threading.Thread(target=self._long_running_task, daemon=True)
thread.start()
```

## SettingsManager Usage

Controllers that persist user preferences:

| Controller | Settings Used | Purpose |
|-------------|---------------|---------|
| `DownloaderController` | `DOWNLOADER_SAVE_PATH`, `DOWNLOADER_QUALITY` | Remember download locations and quality preferences |
| `TranscriberController` | `TRANSCRIBER_OUTPUT_LOCATION`, `TRANSCRIBER_CUSTOM_PATH` | Remember output preferences |

Usage pattern:
```python
# Get setting
save_path = settings.get("DOWNLOADER_SAVE_PATH", "/default/path")

# Set setting  
settings.set("DOWNLOADER_SAVE_PATH", "/new/path")
```

## Key Conventions

1. **Naming**: Controller names match their tab + "Controller" suffix
2. **Initialization**: Controllers receive view reference in constructor
3. **Callback Binding**: Views set controller as callback handler
4. **Model Access**: Controllers create/manage their own model instances
5. **Error Handling**: Controllers handle errors and update views appropriately

## Adding New Controllers

To add a new controller:

1. **Create Controller**: Implement the standard pattern in `controllers/`
2. **Create View**: Add corresponding tab in `views/`
3. **Wire in main.py**: Initialize controller and pass view reference
4. **Add to MainWindow**: Ensure tab is created in main window

Example from main.py:
```python
# Initialize controller
controller = NewController(window.new_tab)
logger.info("NewController initialized")
```

## Testing Controllers

Controllers can be tested by:
1. Mocking view callbacks
2. Testing workflow coordination
3. Verifying model method calls
4. Checking error handling

Example test structure:
```python
class TestNewController:
    def test_workflow(self):
        mock_view = MockView()
        controller = NewController(mock_view)
        
        # Trigger workflow
        controller.handle_action(test_data)
        
        # Verify view updates
        assert mock_view.show_result_called
```