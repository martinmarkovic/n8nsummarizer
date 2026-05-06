#!/usr/bin/env python3
"""
SummarizerController Demo

Demonstrates the complete v9.3 summarization workflow with the new
unified SummarizerController.
"""

import sys
import os
import tkinter as tk
from tkinter import ttk

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_basic_workflow():
    """Demonstrate basic SummarizerController workflow."""
    print("=" * 60)
    print("SummarizerController Demo - Basic Workflow")
    print("=" * 60)
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        from utils.prompt_presets import PROMPT_PRESETS, get_prompt_with_content
        
        # Create main window and tab
        root = tk.Tk()
        root.withdraw()  # Hide main window for demo
        notebook = tk.ttk.Notebook(root)
        
        # Create SummarizerTab
        tab = SummarizerTab(notebook)
        notebook.add(tab, text="📝 Summarizer")
        
        # Create controller
        controller = SummarizerController(tab)
        
        print(f"✅ SummarizerController created")
        print(f"✅ Connected to SummarizerTab")
        print(f"✅ Models initialized:")
        print(f"   - FileModel: {controller.file_model}")
        print(f"   - LLMClient: {controller.llm_client}")
        print(f"   - TranscribeModel: {controller.transcribe_model}")
        
        # Show available prompt presets
        print(f"\n📋 Available Prompt Presets ({len(PROMPT_PRESETS)}):")
        for i, preset_name in enumerate(PROMPT_PRESETS.keys(), 1):
            print(f"   {i}. {preset_name}")
        
        # Demonstrate configuration
        print(f"\n📝 Current Configuration:")
        print(f"   Webhook URL: {tab.get_webhook_url()}")
        print(f"   Model: {tab.get_model_name()}")
        print(f"   Input Mode: {tab.get_input_mode()}")
        print(f"   Current Prompt: {tab.prompt_preset_var.get()}")
        
        # Show how to use the controller
        print(f"\n💡 Usage Example:")
        print(f"   1. User selects file or enters YouTube URL")
        print(f"   2. Controller handles file loading or transcription")
        print(f"   3. Content is sent to LLM with selected prompt")
        print(f"   4. Summary is displayed and can be exported")
        
        print(f"\n🎯 Key Features:")
        print(f"   ✅ Unified interface for file and YouTube")
        print(f"   ✅ Direct LLM integration (no n8n dependency)")
        print(f"   ✅ Automatic content chunking")
        print(f"   ✅ Prompt preset support")
        print(f"   ✅ Full export functionality")
        print(f"   ✅ Thread-based background processing")
        print(f"   ✅ Comprehensive error handling")
        
        # Clean up
        root.destroy()
        
        print(f"\n✅ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def demo_configuration_options():
    """Demonstrate configuration options."""
    print("\n" + "=" * 60)
    print("Configuration Options Demo")
    print("=" * 60)
    
    try:
        from controllers.summarizer_controller import SummarizerController
        from views.summarizer_tab import SummarizerTab
        
        root = tk.Tk()
        root.withdraw()
        notebook = tk.ttk.Notebook(root)
        tab = SummarizerTab(notebook)
        controller = SummarizerController(tab)
        
        print("📋 Default Configuration:")
        print(f"   Webhook: {controller.llm_client.config.webhook_url}")
        print(f"   Model: {controller.llm_client.config.model_name}")
        print(f"   Timeout: {controller.llm_client.config.timeout}s")
        print(f"   Chunk Size: {controller.llm_client.config.chunk_size_bytes/1024:.0f}KB")
        
        print(f"\n🛠️  Configuration Methods:")
        print(f"   - _update_llm_client(): Update from view settings")
        print(f"   - save_settings_to_env(): Persist to .env file")
        print(f"   - get_webhook_url(): Get current webhook URL")
        print(f"   - get_model_name(): Get current model name")
        
        print(f"\n📄 .env Configuration:")
        print("   LLM_WEBHOOK_URL=http://localhost:1234")
        print("   LLM_MODEL=local-model")
        print("   LLM_TIMEOUT=120")
        
        # Clean up
        root.destroy()
        
        print(f"\n✅ Configuration demo completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration demo failed: {e}")
        return False


def demo_workflow_comparison():
    """Compare old vs new workflow."""
    print("\n" + "=" * 60)
    print("Workflow Comparison: Old vs New")
    print("=" * 60)
    
    print("🔄 OLD Workflow (n8n-based):")
    print("   FileTab → FileController → N8NModel → n8n webhook → Summary")
    print("   YouTubeTab → YouTubeController → TranscribeModel → N8NModel → n8n webhook → Summary")
    print("   ❌ Requires n8n server")
    print("   ❌ Slower (extra webhook hop)")
    print("   ❌ Less flexible")
    
    print("\n🆕 NEW Workflow (LLM-based):")
    print("   SummarizerTab → SummarizerController → LLMClient → LLM webhook → Summary")
    print("   ✅ Direct LLM integration")
    print("   ✅ Faster (no n8n middleman)")
    print("   ✅ More flexible (any OpenAI-compatible server)")
    print("   ✅ Unified interface")
    print("   ✅ Prompt preset support")
    
    print(f"\n✅ Comparison demo completed!")
    return True


def main():
    """Run all demos."""
    print("SummarizerController v9.3 Demo")
    print("=" * 60)
    
    try:
        demo_basic_workflow()
        demo_configuration_options()
        demo_workflow_comparison()
        
        print("\n" + "=" * 60)
        print("🎉 ALL DEMOS COMPLETED!")
        print("=" * 60)
        
        print(f"\n📚 Next Steps:")
        print(f"   1. Start your LLM server (LM Studio, Ollama, etc.)")
        print(f"   2. Configure .env with your server URL and model")
        print(f"   3. Use the SummarizerTab in the application")
        print(f"   4. Select file or YouTube mode and click Summarize")
        print(f"   5. Export results as needed")
        
        print(f"\n💡 Migration Plan:")
        print(f"   - Test SummarizerController alongside legacy controllers")
        print(f"   - Verify all workflows work correctly")
        print(f"   - Gradually phase out legacy controllers")
        print(f"   - Update documentation and user guides")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())