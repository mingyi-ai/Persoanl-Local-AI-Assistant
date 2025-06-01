"""LLM Setup UI components for managing AI backend configuration."""
from typing import Dict, Any, Optional, List
import streamlit as st
from pathlib import Path

from ..services.llm_service import LLMService, LlamaCppBackend, OllamaBackend
from ..services.prompt_service import PromptService

# Constants
MODELS_DIR = Path("core/models")


def _initialize_session_state():
    """Initialize session state variables for LLM management."""
    if "llm_backend" not in st.session_state:
        st.session_state.llm_backend = None
    if "llm_initialized" not in st.session_state:
        st.session_state.llm_initialized = False
    if "selected_backend_type" not in st.session_state:
        st.session_state.selected_backend_type = "LlamaCpp"
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = None
    if "prompt_service" not in st.session_state:
        st.session_state.prompt_service = None


def _get_local_models() -> List[str]:
    """Get list of available local .gguf model files."""
    if not MODELS_DIR.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        return []
    
    models = []
    for file_path in MODELS_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.gguf':
            models.append(file_path.name)
    
    return sorted(models)


def _reinitialize_model() -> bool:
    """Reinitialize the selected model."""
    try:
        with st.spinner("Initializing model..."):
            backend_type = st.session_state.selected_backend_type
            selected_model = st.session_state.selected_model
            
            if not selected_model:
                st.sidebar.error("Please select a model first")
                return False
            
            # Create new backend instance
            if backend_type == "Ollama":
                backend = OllamaBackend(selected_model)
            else:  # LlamaCpp
                model_path = MODELS_DIR / selected_model
                backend = LlamaCppBackend(str(model_path))
            
            # Initialize the backend
            if backend.initialize_model():
                st.session_state.llm_backend = backend
                st.session_state.llm_initialized = True
                st.session_state.prompt_service = PromptService(backend)
                st.sidebar.success("Model initialized successfully!")
                return True
            else:
                st.sidebar.error("Failed to initialize model")
                return False
    except Exception as e:
        st.sidebar.error(f"Error initializing model: {str(e)}")
        return False


def _auto_select_and_initialize_model(backend_type: str) -> bool:
    """Automatically select the first available model and initialize it."""
    if backend_type == "Ollama":
        available_models = LLMService.get_ollama_models()
        if available_models:
            st.session_state.selected_model = available_models[0]
            return _reinitialize_model()
    else:  # LlamaCpp
        available_models = _get_local_models()
        if available_models:
            st.session_state.selected_model = available_models[0]
            return _reinitialize_model()
    
    return False


def render_status_window() -> None:
    """Render the current LLM model status window."""
    st.sidebar.markdown("### 🤖 AI Model Status")
    
    if st.session_state.llm_backend:
        model_info = st.session_state.llm_backend.get_model_info()
        
        # Status indicator with color coding
        status = model_info.get("status", "unknown")
        if status in ["loaded", "connected"]:
            st.sidebar.success(f"✅ **Status:** {status.title()}")
        else:
            st.sidebar.error(f"❌ **Status:** {status.title()}")
        
        # Model information
        backend = model_info.get("backend", "unknown")
        st.sidebar.info(f"**Backend:** {backend.title()}")
        
        if backend == "ollama":
            model_name = model_info.get("model", "unknown")
            st.sidebar.info(f"**Model:** {model_name}")
        elif backend == "llama.cpp":
            model_path = model_info.get("model_path", "unknown")
            model_name = Path(model_path).name if model_path != "unknown" else "unknown"
            st.sidebar.info(f"**Model:** {model_name}")
    else:
        st.sidebar.warning("⚠️ **Status:** No model loaded")
        st.sidebar.info("**Backend:** None")
        st.sidebar.info("**Model:** None")


def render_reinitialize_button() -> bool:
    """Render reinitialize button and handle reinitialization."""
    if not st.session_state.llm_initialized or not st.session_state.llm_backend:
        button_text = "🔄 Initialize Model"
        button_type = "primary"
    else:
        button_text = "🔄 Reinitialize Model"
        button_type = "secondary"
    
    if st.sidebar.button(button_text, type=button_type, use_container_width=True):
        return _reinitialize_model()
    return False


def render_backend_selector() -> bool:
    """Render backend selection switch. Returns True if backend changed and auto-reinitialized."""
    st.sidebar.markdown("### ⚙️ Backend Selection")
    
    backend_options = ["Ollama", "LlamaCpp"]
    selected_backend = st.sidebar.radio(
        "Choose AI Backend:",
        options=backend_options,
        index=backend_options.index(st.session_state.selected_backend_type),
        key="backend_selector",
        help="Ollama: Remote server models | LlamaCpp: Local model files"
    )
    
    # Check if backend changed
    if selected_backend != st.session_state.selected_backend_type:
        st.session_state.selected_backend_type = selected_backend
        st.session_state.selected_model = None  # Reset model selection
        
        # Auto-select and initialize the first available model
        if _auto_select_and_initialize_model(selected_backend):
            st.sidebar.success(f"Switched to {selected_backend} and auto-initialized!")
            return True
        else:
            st.sidebar.warning(f"Switched to {selected_backend} but no models available")
        
        # Still trigger rerun even if no models available to update UI
        return True
    
    return False


def render_model_selector() -> None:
    """Render model selection dropdown based on selected backend."""
    st.sidebar.markdown("### 📋 Model Selection")
    
    backend_type = st.session_state.selected_backend_type
    
    if backend_type == "Ollama":
        _render_ollama_models()
    else:  # LlamaCpp
        _render_llamacpp_models()


def _render_ollama_models() -> None:
    """Render Ollama model selection."""
    available_models = LLMService.get_ollama_models()
    
    if not available_models:
        st.sidebar.warning("⚠️ No Ollama models found")
        st.sidebar.caption("Make sure Ollama is running and models are installed")
        if st.sidebar.button("🔄 Refresh Models", use_container_width=True):
            st.rerun()
        return
    
    # Model selection
    current_model = st.session_state.selected_model
    if current_model not in available_models:
        current_model = None
    
    selected_model = st.sidebar.selectbox(
        "Select Ollama Model:",
        options=available_models,
        index=available_models.index(current_model) if current_model else 0,
        key="ollama_model_selector"
    )
    
    st.session_state.selected_model = selected_model
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Models", use_container_width=True):
        st.rerun()


def _render_llamacpp_models() -> None:
    """Render LlamaCpp model selection."""
    # Find available .gguf files
    available_models = _get_local_models()
    
    if not available_models:
        st.sidebar.warning("⚠️ No .gguf models found")
        st.sidebar.caption(f"Place model files in: {MODELS_DIR}")
        return
    
    # Model selection
    current_model = st.session_state.selected_model
    if current_model not in available_models:
        current_model = None
    
    selected_model = st.sidebar.selectbox(
        "Select Local Model:",
        options=available_models,
        index=available_models.index(current_model) if current_model else 0,
        key="llamacpp_model_selector"
    )
    
    st.session_state.selected_model = selected_model
    
    # Show model file info
    if selected_model:
        model_path = MODELS_DIR / selected_model
        if model_path.exists():
            size_mb = model_path.stat().st_size / (1024 * 1024)
            st.sidebar.caption(f"📁 Size: {size_mb:.1f} MB")


def render_setup_window() -> None:
    """Render the LLM backend setup window (reserved for future use)."""
    st.sidebar.markdown("### 🔧 Backend Configuration")
    
    with st.sidebar.expander("Advanced Settings", expanded=False):
        st.markdown("**Coming Soon:**")
        st.caption("• Temperature control")
        st.caption("• Context length settings")
        st.caption("• Custom model paths")
        st.caption("• Performance tuning")
        st.caption("• API endpoint configuration")


def render_complete_sidebar() -> bool:
    """Render the complete LLM setup sidebar. Returns True if model was reinitialized."""
    # Initialize session state
    _initialize_session_state()
    
    # Status window
    render_status_window()
    st.sidebar.divider()
    
    # Reinitialize button
    reinitialized = render_reinitialize_button()
    st.sidebar.divider()
    
    # Backend selector (returns True if backend changed and auto-reinitialized)
    backend_changed = render_backend_selector()
    st.sidebar.divider()
    
    # Model selector
    render_model_selector()
    st.sidebar.divider()
    
    # Setup window
    render_setup_window()
    
    return reinitialized or backend_changed


def get_current_prompt_service() -> Optional[PromptService]:
    """Get the current initialized prompt service."""
    return st.session_state.get("prompt_service")


def is_model_ready() -> bool:
    """Check if a model is ready for use."""
    return (st.session_state.get("llm_initialized", False) and 
            st.session_state.get("llm_backend") is not None and
            st.session_state.get("prompt_service") is not None)


def initialize_llm_on_startup() -> Optional[PromptService]:
    """Initialize LLM automatically on app startup."""
    if "startup_llm_initialized" not in st.session_state:
        st.session_state.startup_llm_initialized = False
    
    if not st.session_state.startup_llm_initialized:
        try:
            # Initialize session state first
            _initialize_session_state()
            
            # Try LlamaCpp first
            if MODELS_DIR.exists():
                gguf_files = [f for f in MODELS_DIR.iterdir() 
                             if f.is_file() and f.suffix.lower() == '.gguf']
                if gguf_files:
                    backend = LlamaCppBackend(str(gguf_files[0]))
                    if backend.initialize_model():
                        st.session_state.llm_backend = backend
                        st.session_state.llm_initialized = True
                        st.session_state.selected_backend_type = "LlamaCpp"
                        st.session_state.selected_model = gguf_files[0].name
                        st.session_state.prompt_service = PromptService(backend)
                        st.session_state.startup_llm_initialized = True
                        return st.session_state.prompt_service
            
            # Fallback to Ollama
            available_ollama_models = LLMService.get_ollama_models()
            if available_ollama_models:
                backend = OllamaBackend(available_ollama_models[0])
                if backend.initialize_model():
                    st.session_state.llm_backend = backend
                    st.session_state.llm_initialized = True
                    st.session_state.selected_backend_type = "Ollama"
                    st.session_state.selected_model = available_ollama_models[0]
                    st.session_state.prompt_service = PromptService(backend)
                    st.session_state.startup_llm_initialized = True
                    return st.session_state.prompt_service
        
        except Exception as e:
            # Silently fail and let user manually initialize
            pass
        
        st.session_state.startup_llm_initialized = True
    
    return st.session_state.get("prompt_service")
