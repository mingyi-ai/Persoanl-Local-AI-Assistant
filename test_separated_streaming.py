import streamlit as st
import sys
import os

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.services.llm_service import LlamaCppBackend
from core.services.prompt_service import PromptService
from core.ui.streaming_ui import create_streaming_display

def main():
    st.set_page_config(page_title="Test Separated Streaming", layout="wide")
    
    st.title("🧪 Test Separated Streaming Architecture")
    st.markdown("This test verifies that UI logic is properly separated from service logic.")
    
    # Initialize services (without UI dependencies in service layer)
    if "llm_backend" not in st.session_state:
        st.session_state.llm_backend = LlamaCppBackend()
        if st.session_state.llm_backend.initialize_model():
            st.session_state.prompt_service = PromptService(st.session_state.llm_backend)
        else:
            st.session_state.prompt_service = None
    
    if not st.session_state.prompt_service:
        st.error("❌ Failed to initialize LLM model. Please check if the model file exists.")
        return
    
    st.success("✅ LLM Backend initialized successfully")
    st.info("📋 **Architecture Test**: Service layer has no UI dependencies, UI layer uses callback pattern")
    
    # Test the separated streaming
    st.subheader("🔄 Test Streaming with Separated Architecture")
    
    test_prompt = st.text_area(
        "Enter test prompt:",
        value="What is artificial intelligence? Explain briefly.",
        height=100
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Test Streaming", key="test_streaming"):
            if test_prompt.strip():
                
                # Create separated UI component
                streaming_display = create_streaming_display("test_streaming")
                container = streaming_display.initialize_container()
                
                # Get callback function from UI component
                update_callback = streaming_display.get_update_callback()
                
                # Call service with callback (no UI dependencies in service!)
                with st.spinner("Generating response..."):
                    result = st.session_state.llm_backend.generate_response_streaming(
                        messages=[{"role": "user", "content": test_prompt}],
                        update_callback=update_callback,
                        max_tokens=200,
                        temperature=0.7
                    )
                
                if result:
                    st.success("✅ **Architecture Success**: Service completed without UI dependencies!")
                    st.markdown("**Final Result:**")
                    st.code(result[:200] + "..." if len(result) > 200 else result)
                else:
                    st.warning("⚠️ Generation was cancelled or failed")
            else:
                st.warning("Please enter a test prompt")
    
    with col2:
        if st.button("⏹️ Stop", key="stop_generation"):
            st.session_state.llm_backend.stop_generation()
            st.warning("🛑 Generation stopped")
    
    # Show architecture benefits
    st.divider()
    st.subheader("🏗️ Architecture Benefits")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔧 Service Layer**")
        st.markdown("""
        - Pure business logic
        - No UI dependencies
        - Callback pattern for updates
        - Testable in isolation
        - Reusable across UIs
        """)
    
    with col2:
        st.markdown("**🎨 UI Layer**")
        st.markdown("""
        - Handles user interactions
        - Manages display updates
        - Provides callbacks to services
        - Streamlit-specific code
        - Easy to modify/replace
        """)
    
    with col3:
        st.markdown("**🔄 Benefits**")
        st.markdown("""
        - Clear separation of concerns
        - Easier testing and debugging
        - UI can be changed independently
        - Services can be reused
        - Better maintainability
        """)

if __name__ == "__main__":
    main()
