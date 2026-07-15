import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config import load_config, save_config
from logger import SessionLogger
from audio_pipeline import AudioPipelineThread
from ui.overlay import SubtitleOverlay
from ui.control_menu import ControlMenu
from ui.settings import SettingsDialog

# Global variables for clean reference
app = None
config = None
logger = None
overlay = None
control_menu = None
pipeline_thread = None

def clean_exit():
    """Properly stops background threads and exits the application."""
    global pipeline_thread, app
    print("Initiating clean exit...")
    if pipeline_thread is not None and pipeline_thread.isRunning():
        # Signal stop and wait for thread loop to close
        pipeline_thread.stop()
    print("Background thread closed. Exiting.")
    if app:
        app.quit()
    sys.exit(0)

def main():
    global app, config, logger, overlay, control_menu, pipeline_thread
    
    app = QApplication(sys.argv)
    
    # Load configuration
    config = load_config()
    
    # Instantiate logger
    logger = SessionLogger()
    
    # Create windows
    overlay = SubtitleOverlay(position_name=config.get("position", "bottom-center"))
    overlay.set_style_config(config)
    control_menu = ControlMenu(position_name=config.get("position", "bottom-center"))
    
    # Initialize background audio processing thread
    pipeline_thread = AudioPipelineThread(config=config, logger=logger)
    
    # ------------------
    # Signal Connections
    # ------------------
    
    # 1. Update subtitles on overlay when transcription occurs
    pipeline_thread.transcription_updated.connect(overlay.update_text)
    
    # 2. Update Control Menu title bar with thread status (e.g. Listening, Transcribing, Paused)
    def update_menu_status(status_text):
        control_menu.label_title.setText(f"Overlay Captioner ({status_text})")
        
    pipeline_thread.status_updated.connect(update_menu_status)
    
    # 3. Dynamic overlay state updates during speech
    def handle_speech_state(is_speaking):
        # Speech capturing placeholder fix: do not replace transcription boxes with "..."
        pass
            
    pipeline_thread.speech_state_changed.connect(handle_speech_state)
    
    # ------------------
    # UI Interaction Logic
    # ------------------
    
    # Pause / Play Toggle Logic
    def handle_pause_toggle():
        # Check current state
        is_paused = not pipeline_thread.is_paused
        
        # Set pause state in audio thread and logger
        pipeline_thread.set_paused(is_paused)
        logger.set_paused(is_paused)
        
        # Toggle styling of the button in control menu
        control_menu.toggle_pause_style(is_paused)
        
        # Reset overlay visual state if paused
        if is_paused:
            overlay.update_text("Session Paused", ["Logging and audio paused", "Click Resume to continue"])
        else:
            overlay.update_text("Session Resumed", ["Listening...", ""])
            
    control_menu.btn_pause.clicked.connect(handle_pause_toggle)
    
    # Settings Dialog Logic
    def handle_open_settings():
        global config
        
        # Save current overlay text state to restore after closing settings UI
        orig_text, orig_translations = overlay.get_current_text()
        
        # Open modal settings dialog, passing overlay so it can update previews
        dialog = SettingsDialog(current_config=config, overlay=overlay, parent=control_menu)
        
        def apply_changes(updated_config):
            global config
            old_device = config.get("device_index")
            
            # Save configuration locally
            save_config(updated_config)
            
            # If input device index or language changed, update pipeline thread
            pipeline_thread.update_config(updated_config)
            
            # Update overlay style and position from settings
            overlay.set_style_config(updated_config)
            
            # Update menu positioning relative to overlay
            control_menu.position_near_overlay(overlay.geometry())
            
            # Update local global reference
            config = updated_config
            
            # Restart pipeline thread if device index has changed to apply configuration
            if updated_config["device_index"] != old_device:
                print("Audio device changed. Restarting audio stream...")
                pipeline_thread.stop()
                pipeline_thread.start()
                
        dialog.config_applied.connect(apply_changes)
        
        if dialog.exec():
            apply_changes(dialog.get_updated_config())
            
        # Settings UI closed - restore the original overlay text
        overlay.update_text(orig_text, orig_translations)
                
    control_menu.btn_settings.clicked.connect(handle_open_settings)
    
    # Exit Actions
    control_menu.btn_exit.clicked.connect(clean_exit)
    # Catch window close events (e.g. Alt + F4) on control menu to perform clean exit
    control_menu.closeEvent = lambda event: clean_exit()
    
    # ------------------
    # Show and Position
    # ------------------
    
    overlay.show()
    
    # Align control menu relative to overlay geometry
    control_menu.position_near_overlay(overlay.geometry())
    control_menu.show()
    
    # Start background processing thread
    pipeline_thread.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
