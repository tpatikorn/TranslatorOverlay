import sounddevice as sd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QFormLayout, QSpinBox, QFontComboBox, QColorDialog, QSlider, QGroupBox, QGridLayout, QMessageBox
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
        self.original_config = current_config.copy()
        self.overlay = overlay
        self.is_button_clicked = False
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(950, 550)
        
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
        self.connect_signals()

    def init_ui(self):
        # Master Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 1. System Options Group Box (Top Section: 3 columns)
        group_sys = QGroupBox("System Options", self)
        group_sys.setStyleSheet("""
            QGroupBox {
                color: #06B6D4;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 700;
                border: 1.5px solid #475569;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                background-color: #1A1A22;
            }
        """)
        sys_layout = QHBoxLayout(group_sys)
        sys_layout.setSpacing(20)
        sys_layout.setContentsMargins(15, 12, 15, 12)
        
        # ASR Engine Column
        col_asr = QVBoxLayout()
        col_asr.addWidget(QLabel("ASR Engine:"))
        self.combo_asr = QComboBox(self)
        self.combo_asr.addItem("Google Web Speech (Cloud)", "google")
        self.combo_asr.addItem("Vosk (Local Streaming)", "vosk")
        col_asr.addWidget(self.combo_asr)
        sys_layout.addLayout(col_asr)
        
        # Microphone Column
        col_dev = QVBoxLayout()
        col_dev.addWidget(QLabel("Input Device:"))
        self.combo_device = QComboBox(self)
        self.populate_audio_devices()
        col_dev.addWidget(self.combo_device)
        sys_layout.addLayout(col_dev)
        
        # History Limit Column
        col_hist = QVBoxLayout()
        col_hist.addWidget(QLabel("History Limit:"))
        self.combo_history_limit = QComboBox(self)
        self.combo_history_limit.addItem("1 (Current Only)", 1)
        self.combo_history_limit.addItem("2 Transcriptions", 2)
        self.combo_history_limit.addItem("3 Transcriptions", 3)
        col_hist.addWidget(self.combo_history_limit)
        sys_layout.addLayout(col_hist)
        
        main_layout.addWidget(group_sys)
        
        # 2. Layout & Position Group Box (Middle Section: 3 columns, 2 rows)
        group_layout = QGroupBox("Layout & Position", self)
        group_layout.setStyleSheet("""
            QGroupBox {
                color: #D946EF;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 700;
                border: 1.5px solid #475569;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                background-color: #1A1A22;
            }
        """)
        pos_grid = QGridLayout(group_layout)
        pos_grid.setSpacing(15)
        pos_grid.setContentsMargins(15, 12, 15, 12)
        
        # Row 0, Column 0: Align Position
        lay_align = QHBoxLayout()
        lay_align.addWidget(QLabel("Align Position:"))
        self.combo_align = QComboBox(self)
        self.combo_align.addItem("Left", "left")
        self.combo_align.addItem("Middle", "middle")
        self.combo_align.addItem("Right", "right")
        lay_align.addWidget(self.combo_align)
        pos_grid.addLayout(lay_align, 0, 0)
        
        # Row 0, Column 1: Background Color
        lay_bg = QHBoxLayout()
        lay_bg.addWidget(QLabel("BG Color:"))
        self.btn_bg_color = QPushButton("Choose BG", self)
        self.btn_bg_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bg_color.clicked.connect(self.choose_bg_color)
        lay_bg.addWidget(self.btn_bg_color)
        pos_grid.addLayout(lay_bg, 0, 1)
        
        # Row 0, Column 2: Background Opacity
        lay_opacity = QHBoxLayout()
        lay_opacity.addWidget(QLabel("BG Opacity:"))
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
        opacity_layout.addWidget(self.slider_opacity)
        opacity_layout.addWidget(self.label_opacity_val)
        
        def update_opacity_label(val):
            self.label_opacity_val.setText(f"{val}%")
            self.config["bg_opacity"] = val / 100.0
            self.apply_values()
            
        self.slider_opacity.valueChanged.connect(update_opacity_label)
        lay_opacity.addLayout(opacity_layout)
        pos_grid.addLayout(lay_opacity, 0, 2)
        
        # Row 1, Column 0: Bottom Offset
        lay_bottom = QHBoxLayout()
        lay_bottom.addWidget(QLabel("Bottom Offset:"))
        self.spin_offset = QSpinBox(self)
        self.spin_offset.setRange(0, 500)
        self.spin_offset.setSuffix(" px")
        self.spin_offset.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        lay_bottom.addWidget(self.spin_offset)
        pos_grid.addLayout(lay_bottom, 1, 0)
        
        # Row 1, Column 1: Left Offset
        lay_left = QHBoxLayout()
        lay_left.addWidget(QLabel("Left Offset:"))
        self.spin_left_offset = QSpinBox(self)
        self.spin_left_offset.setRange(0, 1000)
        self.spin_left_offset.setSuffix(" px")
        self.spin_left_offset.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        lay_left.addWidget(self.spin_left_offset)
        pos_grid.addLayout(lay_left, 1, 1)
        
        # Row 1, Column 2: Right Offset
        lay_right = QHBoxLayout()
        lay_right.addWidget(QLabel("Right Offset:"))
        self.spin_right_offset = QSpinBox(self)
        self.spin_right_offset.setRange(0, 1000)
        self.spin_right_offset.setSuffix(" px")
        self.spin_right_offset.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 4px;")
        lay_right.addWidget(self.spin_right_offset)
        pos_grid.addLayout(lay_right, 1, 2)
        
        # Make the columns exactly equal in width
        pos_grid.setColumnStretch(0, 1)
        pos_grid.setColumnStretch(1, 1)
        pos_grid.setColumnStretch(2, 1)
        
        self.combo_align.currentIndexChanged.connect(self.update_offset_states)
        
        main_layout.addWidget(group_layout)
        
        # 3. Languages & Typography Group Box (Bottom Section: Language + Typography together)
        group_lang_typo = QGroupBox("Languages & Typography", self)
        group_lang_typo.setStyleSheet("""
            QGroupBox {
                color: #A855F7;
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                font-weight: 700;
                border: 1.5px solid #475569;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                background-color: #1A1A22;
            }
        """)
        typo_grid = QGridLayout(group_lang_typo)
        typo_grid.setSpacing(10)
        typo_grid.setContentsMargins(15, 12, 15, 12)
        
        # Table Headers
        lbl_h_lang = QLabel("Language Line", self)
        lbl_h_font = QLabel("Font Family", self)
        lbl_h_size = QLabel("Font Size", self)
        lbl_h_color = QLabel("Text Color", self)
        
        hdr_style = "color: #94A3B8; font-family: 'Inter', sans-serif; font-size: 11px; font-weight: bold;"
        lbl_h_lang.setStyleSheet(hdr_style)
        lbl_h_font.setStyleSheet(hdr_style)
        lbl_h_size.setStyleSheet(hdr_style)
        lbl_h_color.setStyleSheet(hdr_style)
        
        typo_grid.addWidget(lbl_h_lang, 0, 0)
        typo_grid.addWidget(lbl_h_font, 0, 1)
        typo_grid.addWidget(lbl_h_size, 0, 2)
        typo_grid.addWidget(lbl_h_color, 0, 3)
        
        # Row 1: Original Language
        self.combo_source = QComboBox(self)
        self.combo_font_src = QFontComboBox(self)
        self.combo_font_src.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.spin_size_src = QSpinBox(self)
        self.spin_size_src.setRange(8, 72)
        self.spin_size_src.setSuffix(" pt")
        self.spin_size_src.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.btn_color_src = QPushButton("Choose Color", self)
        self.btn_color_src.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color_src.clicked.connect(self.choose_color_src)
        
        typo_grid.addWidget(self.combo_source, 1, 0)
        typo_grid.addWidget(self.combo_font_src, 1, 1)
        typo_grid.addWidget(self.spin_size_src, 1, 2)
        typo_grid.addWidget(self.btn_color_src, 1, 3)
        
        # Row 2: Translation Language 1
        self.combo_trg1 = QComboBox(self)
        self.combo_font_trg1 = QFontComboBox(self)
        self.combo_font_trg1.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.spin_size_trg1 = QSpinBox(self)
        self.spin_size_trg1.setRange(8, 72)
        self.spin_size_trg1.setSuffix(" pt")
        self.spin_size_trg1.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.btn_color_trg1 = QPushButton("Choose Color", self)
        self.btn_color_trg1.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color_trg1.clicked.connect(self.choose_color_trg1)
        
        typo_grid.addWidget(self.combo_trg1, 2, 0)
        typo_grid.addWidget(self.combo_font_trg1, 2, 1)
        typo_grid.addWidget(self.spin_size_trg1, 2, 2)
        typo_grid.addWidget(self.btn_color_trg1, 2, 3)
        
        # Row 3: Translation Language 2
        self.combo_trg2 = QComboBox(self)
        self.combo_font_trg2 = QFontComboBox(self)
        self.combo_font_trg2.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.spin_size_trg2 = QSpinBox(self)
        self.spin_size_trg2.setRange(8, 72)
        self.spin_size_trg2.setSuffix(" pt")
        self.spin_size_trg2.setStyleSheet("background-color: #2D2D39; color: #F8FAFC; border: 1px solid #475569; border-radius: 6px; padding: 2px;")
        self.btn_color_trg2 = QPushButton("Choose Color", self)
        self.btn_color_trg2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_color_trg2.clicked.connect(self.choose_color_trg2)
        
        typo_grid.addWidget(self.combo_trg2, 3, 0)
        typo_grid.addWidget(self.combo_font_trg2, 3, 1)
        typo_grid.addWidget(self.spin_size_trg2, 3, 2)
        typo_grid.addWidget(self.btn_color_trg2, 3, 3)
        
        self.populate_languages()
        
        main_layout.addWidget(group_lang_typo)
        
        # Spacer
        main_layout.addStretch()
        
        # Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.cancel_clicked)
        
        btn_save = QPushButton("Save Settings", self)
        btn_save.setObjectName("btn_save")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.save_values)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
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
        """Fetch languages list from translator and populate dropdowns with convenience shortcuts."""
        langs_dict = get_languages()
        
        # Sort languages alphabetically by name
        sorted_langs = sorted(langs_dict.items(), key=lambda x: x[0].lower())
        
        # Popular convenient languages to pin to the top
        popular_langs = [
            ("Thai", "th"),
            ("English", "en"),
            ("Chinese (Simplified)", "zh-CN"),
            ("Chinese (Traditional)", "zh-TW")
        ]
        
        # 1. Source languages combo box (Auto Detect + Popular + Alphabetical list)
        self.combo_source.clear()
        self.combo_source.addItem("Auto Detect Language", "auto")
        for name, code in popular_langs:
            self.combo_source.addItem(f"★ {name}", code)
        self.combo_source.insertSeparator(self.combo_source.count())
        for name, code in sorted_langs:
            self.combo_source.addItem(name.capitalize(), code)
            
        # 2. Target 1 language combo box (None + Popular + Alphabetical list)
        self.combo_trg1.clear()
        self.combo_trg1.addItem("None", "")
        for name, code in popular_langs:
            self.combo_trg1.addItem(f"★ {name}", code)
        self.combo_trg1.insertSeparator(self.combo_trg1.count())
        for name, code in sorted_langs:
            self.combo_trg1.addItem(name.capitalize(), code)
            
        # 3. Target 2 language combo box (None + Popular + Alphabetical list)
        self.combo_trg2.clear()
        self.combo_trg2.addItem("None", "")
        for name, code in popular_langs:
            self.combo_trg2.addItem(f"★ {name}", code)
        self.combo_trg2.insertSeparator(self.combo_trg2.count())
        for name, code in sorted_langs:
            self.combo_trg2.addItem(name.capitalize(), code)

    def load_values(self):
        """Load current configuration values into the dropdown selections."""
        # 0. ASR Engine
        asr_engine = self.config.get("asr_engine", "google")
        idx = self.combo_asr.findData(asr_engine)
        if idx != -1:
            self.combo_asr.setCurrentIndex(idx)

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
            
        # 6. Screen Offsets (Bottom, Left, Right)
        bottom_offset = self.config.get("bottom_offset", 35)
        self.spin_offset.setValue(bottom_offset)
        
        left_offset = self.config.get("left_offset", 35)
        self.spin_left_offset.setValue(left_offset)
        
        right_offset = self.config.get("right_offset", 35)
        self.spin_right_offset.setValue(right_offset)
        
        # 7. Original Styling
        src_font_family = self.config.get("src_font_family", "Segoe UI")
        self.combo_font_src.setCurrentFont(QFont(src_font_family))
        src_font_size = self.config.get("src_font_size", 15)
        self.spin_size_src.setValue(src_font_size)
        src_color = self.config.get("src_text_color", "#000000")
        self.update_color_button_style(self.btn_color_src, QColor(src_color), src_color)
        
        # 8. Translation 1 Styling
        trg1_font_family = self.config.get("trg1_font_family", "Segoe UI")
        self.combo_font_trg1.setCurrentFont(QFont(trg1_font_family))
        trg1_font_size = self.config.get("trg1_font_size", 19)
        self.spin_size_trg1.setValue(trg1_font_size)
        trg1_color = self.config.get("trg1_text_color", "#000000")
        self.update_color_button_style(self.btn_color_trg1, QColor(trg1_color), trg1_color)
        
        # 9. Translation 2 Styling
        trg2_font_family = self.config.get("trg2_font_family", "Segoe UI")
        self.combo_font_trg2.setCurrentFont(QFont(trg2_font_family))
        trg2_font_size = self.config.get("trg2_font_size", 19)
        self.spin_size_trg2.setValue(trg2_font_size)
        trg2_color = self.config.get("trg2_text_color", "#000000")
        self.update_color_button_style(self.btn_color_trg2, QColor(trg2_color), trg2_color)
        
        # 10. Background Color
        bg_color = self.config.get("bg_color", "rgba(255, 255, 255, 0.78)")
        bg_qcolor = self.parse_rgba_string(bg_color)
        self.update_color_button_style(self.btn_bg_color, bg_qcolor, bg_color)
        
        # 11. Opacity Slider
        bg_opacity = self.config.get("bg_opacity", 0.78)
        self.slider_opacity.setValue(int(bg_opacity * 100))
        self.label_opacity_val.setText(f"{int(bg_opacity * 100)}%")
        
        # Update offset states
        self.update_offset_states()
        
        # Update live preview on overlay
        self.update_overlay_preview()

    def save_values(self):
        """Save form options to config dict and accept the dialog."""
        self.is_button_clicked = True
        self.config["asr_engine"] = self.combo_asr.currentData()
        self.config["device_index"] = self.combo_device.currentData()
        self.config["source_lang"] = self.combo_source.currentData()
        self.config["target_lang1"] = self.combo_trg1.currentData()
        self.config["target_lang2"] = self.combo_trg2.currentData()
        self.config["transcription_align"] = self.combo_align.currentData()
        self.config["history_limit"] = self.combo_history_limit.currentData()
        self.config["bottom_offset"] = self.spin_offset.value()
        self.config["left_offset"] = self.spin_left_offset.value()
        self.config["right_offset"] = self.spin_right_offset.value()
        self.config["bg_opacity"] = self.slider_opacity.value() / 100.0
        
        # Typography settings
        self.config["src_font_family"] = self.combo_font_src.currentFont().family()
        self.config["src_font_size"] = self.spin_size_src.value()
        self.config["trg1_font_family"] = self.combo_font_trg1.currentFont().family()
        self.config["trg1_font_size"] = self.spin_size_trg1.value()
        self.config["trg2_font_family"] = self.combo_font_trg2.currentFont().family()
        self.config["trg2_font_size"] = self.spin_size_trg2.value()
        
        self.accept()

    def cancel_clicked(self):
        """Set explicit click flag and reject the settings dialog."""
        self.is_button_clicked = True
        self.reject()

    def closeEvent(self, event):
        """Prompt user to save or discard changes when closing Settings via [x] or Escape key."""
        if getattr(self, "is_button_clicked", False):
            event.accept()
            return
            
        # Style and build the confirmation dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Unsaved Changes")
        msg_box.setText("You have unsaved changes. Do you want to save or discard them?")
        
        # Apply unified dark theme to confirmation box
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1A1A22;
                color: #F8FAFC;
                font-family: 'Inter', sans-serif;
            }
            QLabel {
                color: #F8FAFC;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
        """)
        
        save_btn = msg_box.addButton(QMessageBox.StandardButton.Save)
        discard_btn = msg_box.addButton(QMessageBox.StandardButton.Discard)
        cancel_btn = msg_box.addButton(QMessageBox.StandardButton.Cancel)
        
        msg_box.setDefaultButton(save_btn)
        msg_box.exec()
        
        clicked = msg_box.clickedButton()
        if clicked == save_btn:
            self.save_values()
            event.accept()
        elif clicked == discard_btn:
            self.cancel_clicked()
            event.accept()
        else:
            event.ignore()

    def apply_values(self):
        """Emit config_applied signal with the current unsaved configurations to preview them."""
        self.config["asr_engine"] = self.combo_asr.currentData()
        self.config["device_index"] = self.combo_device.currentData()
        self.config["source_lang"] = self.combo_source.currentData()
        self.config["target_lang1"] = self.combo_trg1.currentData()
        self.config["target_lang2"] = self.combo_trg2.currentData()
        self.config["transcription_align"] = self.combo_align.currentData()
        self.config["history_limit"] = self.combo_history_limit.currentData()
        self.config["bottom_offset"] = self.spin_offset.value()
        self.config["left_offset"] = self.spin_left_offset.value()
        self.config["right_offset"] = self.spin_right_offset.value()
        self.config["bg_opacity"] = self.slider_opacity.value() / 100.0
        
        # Typography settings
        self.config["src_font_family"] = self.combo_font_src.currentFont().family()
        self.config["src_font_size"] = self.spin_size_src.value()
        self.config["trg1_font_family"] = self.combo_font_trg1.currentFont().family()
        self.config["trg1_font_size"] = self.spin_size_trg1.value()
        self.config["trg2_font_family"] = self.combo_font_trg2.currentFont().family()
        self.config["trg2_font_size"] = self.spin_size_trg2.value()
        
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
            self.apply_values()

    def update_offset_states(self):
        """No-op to keep Left/Right screen offsets always enabled and editable."""
        pass

    def choose_color_src(self):
        curr_hex = self.config.get("src_text_color", "#000000")
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(curr_hex))
        if dialog.exec():
            color = dialog.currentColor()
            hex_str = color.name()
            self.config["src_text_color"] = hex_str
            self.update_color_button_style(self.btn_color_src, color, hex_str)
            self.apply_values()

    def choose_color_trg1(self):
        curr_hex = self.config.get("trg1_text_color", "#000000")
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(curr_hex))
        if dialog.exec():
            color = dialog.currentColor()
            hex_str = color.name()
            self.config["trg1_text_color"] = hex_str
            self.update_color_button_style(self.btn_color_trg1, color, hex_str)
            self.apply_values()

    def choose_color_trg2(self):
        curr_hex = self.config.get("trg2_text_color", "#000000")
        dialog = QColorDialog(self)
        dialog.setCurrentColor(QColor(curr_hex))
        if dialog.exec():
            color = dialog.currentColor()
            hex_str = color.name()
            self.config["trg2_text_color"] = hex_str
            self.update_color_button_style(self.btn_color_trg2, color, hex_str)
            self.apply_values()

    def connect_signals(self):
        """Connect all interactive controls to apply live changes immediately to the overlay."""
        self.combo_asr.currentIndexChanged.connect(self.apply_values)
        self.combo_device.currentIndexChanged.connect(self.apply_values)
        self.combo_source.currentIndexChanged.connect(self.apply_values)
        self.combo_trg1.currentIndexChanged.connect(self.apply_values)
        self.combo_trg2.currentIndexChanged.connect(self.apply_values)
        self.combo_history_limit.currentIndexChanged.connect(self.apply_values)
        self.combo_align.currentIndexChanged.connect(self.apply_values)
        self.spin_offset.valueChanged.connect(self.apply_values)
        self.spin_left_offset.valueChanged.connect(self.apply_values)
        self.spin_right_offset.valueChanged.connect(self.apply_values)
        
        self.combo_font_src.currentFontChanged.connect(self.apply_values)
        self.spin_size_src.valueChanged.connect(self.apply_values)
        self.combo_font_trg1.currentFontChanged.connect(self.apply_values)
        self.spin_size_trg1.valueChanged.connect(self.apply_values)
        self.combo_font_trg2.currentFontChanged.connect(self.apply_values)
        self.spin_size_trg2.valueChanged.connect(self.apply_values)

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
