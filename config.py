import os
import json

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "source_lang": "th",
    "target_lang1": "en",
    "target_lang2": "",
    "transcription_align": "middle",
    "device_index": None,
    "bottom_offset": 35,
    "left_offset": 35,
    "right_offset": 35,
    "bg_color": "rgba(255, 255, 255, 0.78)",
    "bg_opacity": 0.78,
    "text_color": "#000000",
    "font_family": "Segoe UI",
    "font_size": 19,
    "history_limit": 1,
    "asr_engine": "google",
    "src_font_family": "Segoe UI",
    "src_font_size": 15,
    "src_text_color": "#000000",
    "trg1_font_family": "Segoe UI",
    "trg1_font_size": 19,
    "trg1_text_color": "#000000",
    "trg2_font_family": "Segoe UI",
    "trg2_font_size": 19,
    "trg2_text_color": "#000000"
}

def load_config():
    """Load configuration from config.json. Creates default config if file doesn't exist."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"Error loading config, resetting to default: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
