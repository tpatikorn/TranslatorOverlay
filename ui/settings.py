import sounddevice as sd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFormLayout, QSpinBox, QFontComboBox, QColorDialog, QSlider, QGroupBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from translator import get_languages

class SettingsDialog(QDialog):
    """
    Styled configuration dialog.
    Allows configuring input mic, source language, up to two target languages,
    and overlay screen position.
    """
    config_applied = pyqtSignal(dict)
    
    def __init__(self, current_config: dict, overlay=None, parent=None):
        super().__init__(parent)
        self.config = current_config.copy()
        self.overlay = overlay
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(720, 390)
        
        # Frameless hint removed to make it a standard clickable window, 
        # but styled dark to fit the theme.
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A22;
                color: #F8FAFC;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #CBD5E1;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox {
                background-color: #2D2D39;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2D39;
                color: #F8FAFC;
                selection-background-color: #06B6D4;
                selection-color: #FFFFFF;
                border: 1px solid #475569;
            }
            QPushButton {
                background-color: #2D2D39;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3B3B4C;
                border-color: #64748B;
            }
            QPushButton#btn_save {
                background-color: #06B6D4;
                color: #FFFFFF;
                border: 1px solid #0891B2;
            }
            QPushButton#btn_save:hover {
                background-color: #0891B2;
            }
        """)
        
        self.init_ui()
        self.load_values()

    def init_ui(self):
        # Master Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Horizontal layout for the two columns
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        # COLUMN 1: Audio & Translation Group Box
        group_audio = QGroupBox("Audio & Languages", self)
        group_audio.setStyleSheet("""
            QGroupBox {
                color: #06B6D4;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 700;
                border: 1.5px solid #475569;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                background-color: #1A1A22;
            }
        """)
        audio_layout = QFormLayout(group_audio)
        audio_layout.setSpacing(10)
        audio_layout.setContentsMargins(15, 15, 15, 15)
        
        # 1. Microphone Selection
        self.combo_device = QComboBox(self)
        self.populate_audio_devices()
        audio_layout.addRow("Input Device:", self.combo_device)
        
        # 2. Source Language
        self.combo_source = QComboBox(self)
        # 3. Target Language 1
        self.combo_trg1 = QComboBox(self)
        # 4. Target Language 2
        self.combo_trg2 = QComboBox(self)
        self.populate_languages()
        
        audio_layout.addRow("Source Lang:", self.combo_source)
        audio_layout.addRow("Target Lang 1:", self.combo_trg1)
        audio_layout.addRow("Target Lang 2:", self.combo_trg2)
        
        # COLUMN 2: Aesthetics & Layout Group Box
        group_aesthetics = QGroupBox("Layout & Aesthetics", self)
        group_aesthetics.setStyleSheet("""
            QGroupBox {
                color: #D946EF;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 700;
                border: 1.5px solid #475569;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                background-color: #1A1A22;
            }
        """)
        aes_layout = QFormLayout(group_aesthetics)
        aes_layout.setSpacing(8)
        aes_layout.setContentsMargins(15, 15, 15, 15)
        
        # 5. Show Last Transcriptions
        self.combo_history_limit = QComboBox(self)
        self.combo_history_limit.addItem("1 (Current Only)", 1)
        self.combo_history_limit.addItem("2 Transcriptions", 2)
        self.combo_history_limit.addItem("3 Transcriptions", 3)
        self.combo_history_limit.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        aes_layout.addRow("History Limit:", self.combo_history_limit)
        
        # 6. Transcription Alignment
        self.combo_align = QComboBox(self)
        self.combo_align.addItem("Left", "left")
        self.combo_align.addItem("Middle", "middle")
        self.combo_align.addItem("Right", "right")
        self.combo_align.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        aes_layout.addRow("Align Position:", self.combo_align)
        
        # 7. Bottom Screen Offset
        self.spin_offset = QSpinBox(self)
        self.spin_offset.setRange(0, 500)
        self.spin_offset.setSuffix(" px")
        self.spin_offset.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        aes_layout.addRow("Bottom Offset:", self.spin_offset)
        
        # 8. Font Family & Size horizontal flow row
        font_row = QHBoxLayout()
        self.combo_font = QFontComboBox(self)
        self.combo_font.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.spin_font_size = QSpinBox(self)
        self.spin_font_size.setRange(8, 72)
        self.spin_font_size.setSuffix(" pt")
        self.spin_font_size.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.spin_font_size.setFixedWidth(75)
        font_row.addWidget(self.combo_font)
        font_row.addWidget(self.spin_font_size)
        aes_layout.addRow("Font Profile:", font_row)
        
        # 9. Background Color & Text Color horizontal flow row
        color_row = QHBoxLayout()
        color_row.setSpacing(10)
        self.btn_bg_color = QPushButton("Choose BG", self)
        self.btn_bg_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bg_color.clicked.connect(self.choose_bg_color)
        self.btn_text_color = QPushButton("Choose Text", self)
        self.btn_text_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_text_color.clicked.connect(self.choose_text_color)
        color_row.addWidget(self.btn_bg_color)
        color_row.addWidget(self.btn_text_color)
        aes_layout.addRow("Theme Colors:", color_row)
        
        # 10. Background Opacity Slider
        opacity_layout = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #2D2D39;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #06B6D4;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        self.label_opacity_val = QLabel("78%", self)
        self.label_opacity_val.setFixedWidth(35)
        self.label_opacity_val.setStyleSheet("color: #CBD5E1; font-weight: bold; font-size: 11px;")
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.label_opacity_val)
        
        def update_opacity_label(val):
            self.label_opacity_val.setText(f"{val}%")
            self.config["bg_opacity"] = val / 100.0
            
        self.slider_opacity.valueChanged.connect(update_opacity_label)
        aes_layout.addRow("BG Opacity:", opacity_layout)
        
        # Add column group boxes to columns layout
        columns_layout.addWidget(group_audio)
        columns_layout.addWidget(group_aesthetics)
        
        main_layout.addLayout(columns_layout)
        
        # Connect change signals for live previews
        self.combo_source.currentIndexChanged.connect(self.update_overlay_preview)
        self.combo_trg1.currentIndexChanged.connect(self.update_overlay_preview)
        self.combo_trg2.currentIndexChanged.connect(self.update_overlay_preview)
        self.combo_history_limit.currentIndexChanged.connect(self.update_overlay_preview)
        self.combo_align.currentIndexChanged.connect(self.update_overlay_preview)
        
        # Spacer
        main_layout.addStretch()
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_apply = QPushButton("Apply", self)
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self.apply_values)
        
        btn_save = QPushButton("Save Settings", self)
        btn_save.setObjectName("btn_save")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_values)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)

    def populate_audio_devices(self):
        """Populate the microphone selection dropdown using sounddevice."""
        self.combo_device.clear()
        self.combo_device.addItem("Default Microphone", None)
        
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                # Filter only input devices
                if dev['max_input_channels'] > 0:
                    self.combo_device.addItem(f"{dev['name']} ({int(dev['max_input_channels'])} ch)", idx)
        except Exception as e:
            print(f"Error querying audio devices: {e}")

    def populate_languages(self):
        """Fetch languages list from translator and populate dropdowns."""
        langs_dict = get_languages()
        
        # Sort languages alphabetically by name
        sorted_langs = sorted(langs_dict.items(), key=lambda x: x[0].lower())
        
        # Source languages combo box (auto detection + individual codes)
        self.combo_source.clear()
        self.combo_source.addItem("Auto Detect Language", "auto")
        for name, code in sorted_langs:
            self.combo_source.addItem(name.capitalize(), code)
            
        # Target 1 language combo box (requires a selected language, no auto)
        self.combo_trg1.clear()
        for name, code in sorted_langs:
            self.combo_trg1.addItem(name.capitalize(), code)
            
        # Target 2 language combo box (can be None)
        self.combo_trg2.clear()
        self.combo_trg2.addItem("None", "")
        for name, code in sorted_langs:
            self.combo_trg2.addItem(name.capitalize(), code)

    def load_values(self):
        """Load current configuration values into the dropdown selections."""
        # 1. Device
        device_index = self.config.get("device_index")
        idx = self.combo_device.findData(device_index)
        if idx != -1:
            self.combo_device.setCurrentIndex(idx)
            
        # 2. Source Language
        source_lang = self.config.get("source_lang", "th")
        idx = self.combo_source.findData(source_lang)
        if idx != -1:
            self.combo_source.setCurrentIndex(idx)
            
        # 3. Target 1
        target_lang1 = self.config.get("target_lang1", "en")
        idx = self.combo_trg1.findData(target_lang1)
        if idx != -1:
            self.combo_trg1.setCurrentIndex(idx)
            
        # 4. Target 2
        target_lang2 = self.config.get("target_lang2", "")
        idx = self.combo_trg2.findData(target_lang2)
        if idx != -1:
            self.combo_trg2.setCurrentIndex(idx)
            
        # 5. Transcription Alignment
        align = self.config.get("transcription_align", "middle")
        idx = self.combo_align.findData(align)
        if idx != -1:
            self.combo_align.setCurrentIndex(idx)

        # 5.5. History Limit Selection
        history_limit = self.config.get("history_limit", 1)
        idx = self.combo_history_limit.findData(history_limit)
        if idx != -1:
            self.combo_history_limit.setCurrentIndex(idx)
            
        # 6. Bottom Screen Offset
        bottom_offset = self.config.get("bottom_offset", 35)
        self.spin_offset.setValue(bottom_offset)
        
        # 7. Font Family
        font_family = self.config.get("font_family", "Segoe UI")
        self.combo_font.setCurrentFont(QFont(font_family))
        
        # 8. Font Size
        font_size = self.config.get("font_size", 19)
        self.spin_font_size.setValue(font_size)
        
        # 9. Background Color
        bg_color = self.config.get("bg_color", "rgba(255, 255, 255, 0.78)")
        bg_qcolor = self.parse_rgba_string(bg_color)
        self.update_color_button_style(self.btn_bg_color, bg_qcolor, bg_color)
        
        # 10. Text Color
        text_color = self.config.get("text_color", "#000000")
        text_qcolor = QColor(text_color)
        self.update_color_button_style(self.btn_text_color, text_qcolor, text_color)

        # 11. Opacity Slider
        bg_opacity = self.config.get("bg_opacity", 0.78)
        self.slider_opacity.setValue(int(bg_opacity * 100))
        self.label_opacity_val.setText(f"{int(bg_opacity * 100)}%")
        
        # Update live preview on overlay
        self.update_overlay_preview()

    def save_values(self):
        """Save form options to config dict and accept the dialog."""
        self.config["device_index"] = self.combo_device.currentData()
        self.config["source_lang"] = self.combo_source.currentData()
        self.config["target_lang1"] = self.combo_trg1.currentData()
        self.config["target_lang2"] = self.combo_trg2.currentData()
        self.config["transcription_align"] = self.combo_align.currentData()
        self.config["history_limit"] = self.combo_history_limit.currentData()
        self.config["bottom_offset"] = self.spin_offset.value()
        self.config["font_family"] = self.combo_font.currentFont().family()
        self.config["font_size"] = self.spin_font_size.value()
        self.config["bg_opacity"] = self.slider_opacity.value() / 100.0
        
        self.accept()

    def apply_values(self):
        """Emit config_applied signal with the current unsaved configurations to preview them."""
        self.config["device_index"] = self.combo_device.currentData()
        self.config["source_lang"] = self.combo_source.currentData()
        self.config["target_lang1"] = self.combo_trg1.currentData()
        self.config["target_lang2"] = self.combo_trg2.currentData()
        self.config["transcription_align"] = self.combo_align.currentData()
        self.config["history_limit"] = self.combo_history_limit.currentData()
        self.config["bottom_offset"] = self.spin_offset.value()
        self.config["font_family"] = self.combo_font.currentFont().family()
        self.config["font_size"] = self.spin_font_size.value()
        self.config["bg_opacity"] = self.slider_opacity.value() / 100.0
        
        self.config_applied.emit(self.config)

    def get_updated_config(self):
        """Return the modified configuration dict."""
        return self.config

    def choose_bg_color(self):
        """Open a color dialog with alpha channel enabled to choose the overlay background color."""
        curr_rgba = self.config.get("bg_color", "rgba(255, 255, 255, 0.78)")
        initial_color = self.parse_rgba_string(curr_rgba)
        
        dialog = QColorDialog(self)
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        dialog.setCurrentColor(initial_color)
        if dialog.exec():
            color = dialog.currentColor()
            # Formulate CSS rgba string
            rgba_str = f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha() / 255.0:.2f})"
            self.config["bg_color"] = rgba_str
            self.update_color_button_style(self.btn_bg_color, color, rgba_str)
            # Update opacity slider to match color alpha
            self.slider_opacity.setValue(int((color.alpha() / 255.0) * 100))

    def choose_text_color(self):
        """Open a color dialog to choose the overlay text color."""
        curr_hex = self.config.get("text_color", "#000000")
        initial_color = QColor(curr_hex)
        
        dialog = QColorDialog(self)
        dialog.setCurrentColor(initial_color)
        if dialog.exec():
            color = dialog.currentColor()
            hex_str = color.name()
            self.config["text_color"] = hex_str
            self.update_color_button_style(self.btn_text_color, color, hex_str)

    def parse_rgba_string(self, rgba_str: str) -> QColor:
        """Parse 'rgba(r, g, b, a)' or hex strings into a QColor object."""
        try:
            if rgba_str.startswith("rgba"):
                content = rgba_str.split("(")[1].split(")")[0]
                parts = content.split(",")
                r = int(parts[0].strip())
                g = int(parts[1].strip())
                b = int(parts[2].strip())
                a = int(float(parts[3].strip()) * 255)
                return QColor(r, g, b, a)
            elif rgba_str.startswith("rgb"):
                content = rgba_str.split("(")[1].split(")")[0]
                parts = content.split(",")
                r = int(parts[0].strip())
                g = int(parts[1].strip())
                b = int(parts[2].strip())
                return QColor(r, g, b, 255)
            else:
                return QColor(rgba_str)
        except Exception as e:
            print(f"Error parsing color '{rgba_str}': {e}")
            return QColor(255, 255, 255, 200)

    def update_color_button_style(self, button, color, color_str):
        """Update button style to visually show the selected color."""
        text_color = "#000000" if color.lightness() > 140 else "#FFFFFF"
        button.setText(color_str)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_str};
                color: {text_color};
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 12px;
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: #06B6D4;
            }}
        """)

    # Localized greetings with "(example)" in respective languages
    GREETINGS = {
        "auto": "สวัสดี (ตัวอย่าง)",
        "th": "สวัสดี (ตัวอย่าง)",
        "en": "Hello (example)",
        "es": "Hola (ejemplo)",
        "fr": "Bonjour (exemple)",
        "de": "Hallo (Beispiel)",
        "zh-cn": "你好 (示例)",
        "zh-tw": "你好 (範例)",
        "ja": "こんにちは (例)",
        "ko": "안녕하세요 (예)",
        "ru": "Привет (пример)",
        "ar": "مرحباً (مثال)",
        "hi": "नमस्ते (उदाहरण)",
        "it": "Ciao (esempio)",
        "pt": "Olá (exemplo)",
        "vi": "Xin chào (ví dụ)"
    }

    def _get_greeting_for_lang(self, lang_code: str) -> str:
        """Return greeting with (example) for the given language code."""
        if not lang_code:
            return ""
        code = lang_code.lower().strip()
        base_code = code.split("-")[0]
        
        if code in self.GREETINGS:
            return self.GREETINGS[code]
        elif base_code in self.GREETINGS:
            return self.GREETINGS[base_code]
        else:
            return f"Greeting (example) [{lang_code}]"

    def update_overlay_preview(self):
        """Update the overlay text to show selected languages' greetings while settings UI is open."""
        if not self.overlay:
            return
            
        src_lang = self.combo_source.currentData()
        trg1 = self.combo_trg1.currentData()
        trg2 = self.combo_trg2.currentData()
        
        src_greet = self._get_greeting_for_lang(src_lang or "auto")
        trg1_greet = self._get_greeting_for_lang(trg1)
        trg2_greet = self._get_greeting_for_lang(trg2)
        
        # Display live preview on overlay, bypassing history tracking
        self.overlay.update_text(src_greet, [trg1_greet, trg2_greet], is_preview=True)
