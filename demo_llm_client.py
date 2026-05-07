#!/usr/bin/env python3
"""
LLM Client Usage Demo

Demonstrates how to use the new LLM client with different prompt presets.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_basic_usage():
    """Demonstrate basic LLM client usage"""
    print("=" * 60)
    print("LLM Client Basic Usage Demo")
    print("=" * 60)
    
    from models.llm_client import LLMClient
    from utils.prompt_presets import PROMPT_PRESETS, get_prompt_with_content
    
    # Initialize client with default configuration
    client = LLMClient()
    print(f"✅ LLM Client initialized")
    print(f"   Webhook: {client.config.webhook_url}")
    print(f"   Model: {client.config.model_name}")
    print(f"   Timeout: {client.config.timeout}s")
    print(f"   Chunk Size: {client.config.chunk_size_bytes/1024:.0f}KB")
    
    # Show available prompt presets
    print(f"\n📋 Available Prompt Presets ({len(PROMPT_PRESETS)}):")
    for i, preset_name in enumerate(PROMPT_PRESETS.keys(), 1):
        print(f"   {i}. {preset_name}")
    
    # Example: Using different presets
    sample_content = """
    This is a sample document that needs to be summarized.
    It contains important information about various topics.
    The document is structured with multiple sections and key points.
    """
    
    print(f"\n📄 Sample Content ({len(sample_content)} chars):")
    print("-" * 40)
    print(sample_content)
    print("-" * 40)
    
    # Generate prompts with different presets
    print(f"\n🔧 Generated Prompts:")
    
    for preset_name in list(PROMPT_PRESETS.keys())[:2]:  # Show first 2 presets
        prompt = get_prompt_with_content(preset_name, sample_content)
        print(f"\n📌 {preset_name}:")
        print(f"   Length: {len(prompt)} characters")
        print(f"   First 100 chars: {prompt[:100]}...")
    
    print(f"\n💡 Usage Example:")
    print("   # Initialize client")
    print("   client = LLMClient()")
    print("")
    print("   # Get prompt with content")
    print("   prompt = get_prompt_with_content('General Summary', your_content)")
    print("")
    print("   # Send to LLM (when server is running)")
    print("   success, summary, error = client.send_content(")
    print("       file_name='document.txt',")
    print("       content=your_content,")
    print("       prompt=prompt")
    print("   )")
    
    print(f"\n✅ Demo completed successfully!")


def demo_configuration():
    """Demonstrate configuration options"""
    print("\n" + "=" * 60)
    print("Configuration Options Demo")
    print("=" * 60)
    
    from models.llm_client import LLMClient
    from models.llm_client.config import LLMClientConfig
    
    # Show default configuration
    default_config = LLMClientConfig.from_env()
    print("📋 Default Configuration:")
    print(f"   Webhook URL: {default_config.webhook_url}")
    print(f"   Model Name: {default_config.model_name}")
    print(f"   Timeout: {default_config.timeout}s")
    print(f"   Chunk Size: {default_config.chunk_size_bytes} bytes")
    
    # Show custom configuration
    print(f"\n🛠️  Custom Configuration:")
    custom_client = LLMClient(
        webhook_url="http://localhost:8080/v1",
        model_name="gpt-4",
        timeout=300
    )
    print(f"   Webhook URL: {custom_client.config.webhook_url}")
    print(f"   Model Name: {custom_client.config.model_name}")
    print(f"   Timeout: {custom_client.config.timeout}s")
    
    # Show .env configuration
    print(f"\n📄 .env Configuration:")
    print("   LLM_WEBHOOK_URL=http://localhost:1234")
    print("   LLM_MODEL=local-model")
    print("   LLM_TIMEOUT=120")
    
    print(f"\n✅ Configuration demo completed!")


def demo_api_compatibility():
    """Demonstrate API compatibility with N8NModel"""
    print("\n" + "=" * 60)
    print("API Compatibility Demo")
    print("=" * 60)
    
    from models.llm_client import LLMClient
    from models.n8n_model import N8NModel
    
    llm_client = LLMClient()
    n8n_model = N8NModel()
    
    print("🔄 Both clients support the same core methods:")
    
    # Check common methods
    common_methods = []
    for method_name in ['send_content', 'test_connection']:
        if hasattr(llm_client, method_name) and hasattr(n8n_model, method_name):
            common_methods.append(method_name)
    
    for method in common_methods:
        print(f"   ✅ {method}()")
    
    print(f"\n📊 Method Signature Comparison:")
    print(f"   LLMClient.send_content(file_name, content, prompt, file_size_bytes, metadata)")
    print(f"   N8NModel.send_content(file_name, content, file_size_bytes, metadata)")
    print(f"   → Note: LLMClient adds 'prompt' parameter for LLM-specific functionality")
    
    print(f"\n🎯 Use Cases:")
    print(f"   • LLMClient: Direct LLM integration (LM Studio, Ollama, etc.)")
    print(f"   • N8NModel: n8n workflow automation")
    print(f"   • Both: Automatic chunking, error handling, logging")
    
    print(f"\n✅ API compatibility demo completed!")


def main():
    """Run all demos"""
    print("LLM Client Usage Demonstrations")
    print("=" * 60)
    
    try:
        demo_basic_usage()
        demo_configuration()
        demo_api_compatibility()
        
        print("\n" + "=" * 60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print(f"\nNext Steps:")
        print(f"   1. Start your LLM server (LM Studio, Ollama, etc.)")
        print(f"   2. Configure .env with your server URL and model")
        print(f"   3. Integrate LLMClient into your controllers")
        print(f"   4. Use prompt presets for different summarization needs")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())