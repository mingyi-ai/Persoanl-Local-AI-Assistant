import streamlit as st
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

class StreamingDisplay:
    """UI component for displaying streaming LLM responses."""
    
    def __init__(self, container_key: str):
        self.container_key = container_key
        self.container = None
        self.chunk_counter = 0
    
    def initialize_container(self, label: str = "AI Response"):
        """Initialize the streaming display container."""
        self.container = st.empty()
        return self.container
    
    def get_update_callback(self) -> Callable[[str, bool], None]:
        """Get the callback function for updating the UI during streaming."""
        def update_display(content: str, is_complete: bool = False):
            if not self.container:
                return
            
            try:
                # Create unique key for each update
                self.chunk_counter += 1
                key_suffix = f"{self.container_key}_{self.chunk_counter}"
                
                if is_complete:
                    # Final display without cursor
                    self.container.text_area(
                        "✅ AI Analysis Complete:",
                        value=content,
                        height=200,
                        disabled=True,
                        key=f"final_{key_suffix}"
                    )
                else:
                    # Streaming display with cursor
                    self.container.text_area(
                        "🔄 AI Analysis Stream:",
                        value=content + "▌",
                        height=200,
                        disabled=True,
                        key=f"stream_{key_suffix}"
                    )
            except Exception as e:
                logger.error(f"Error updating streaming display: {e}")
                # Fallback to simple text display
                if is_complete:
                    self.container.success("✅ Analysis completed")
                else:
                    self.container.info("🔄 Processing...")
        
        return update_display
    
    def show_error(self, message: str):
        """Display an error message."""
        if self.container:
            self.container.error(f"❌ {message}")
    
    def show_cancelled(self):
        """Display cancellation message."""
        if self.container:
            self.container.warning("⏹️ Generation stopped by user")
    
    def show_processing(self, message: str = "Processing..."):
        """Display a processing message."""
        if self.container:
            self.container.info(f"⏳ {message}")
    
    def clear(self):
        """Clear the display."""
        if self.container:
            self.container.empty()

def create_streaming_display(container_key: str) -> StreamingDisplay:
    """Factory function to create a streaming display."""
    return StreamingDisplay(container_key)
