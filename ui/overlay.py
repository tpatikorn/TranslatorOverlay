from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QGuiApplication, QFont, QColor

class SubtitleBlock(QFrame):
    """
    Individual subtitle block widget mapping source and target languages.
    Wraps text contents tightly in modern subtitle style.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SubtitleBlock")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(4)
        
        self.label_src = QLabel(self)
        self.label_src.setWordWrap(True)
        self.label_src.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_src.setMaximumWidth(900)
        
        self.label_trg1 = QLabel(self)
        self.label_trg1.setWordWrap(True)
        self.label_trg1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_trg1.setMaximumWidth(900)
        
        self.label_trg2 = QLabel(self)
        self.label_trg2.setWordWrap(True)
        self.label_trg2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_trg2.setMaximumWidth(900)
        
        layout.addWidget(self.label_src)
        layout.addWidget(self.label_trg1)
        layout.addWidget(self.label_trg2)


class SubtitleOverlay(QWidget):
    """
    Translucent, frameless, and click-through window for displaying subtitle overlays.
    Supports source text and up to two target translations.
    """
    def __init__(self, position_name: str = "bottom-center"):
        super().__init__()
        self.current_position = position_name
        self.bottom_offset = 35
        self.history_limit = 1
        self.history = []
        self.current_status_msg = ("Subtitle Overlay Ready", ["", ""])
        
        # Set window flags: Frameless, Pinned to Top, and Tool (hides from Taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Enable translucent background and click-through (WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        self.init_ui()
        self.reposition(self.current_position)

    def init_ui(self):
        # Master Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Transparent container frame
        self.container = QFrame(self)
        self.container.setObjectName("ContainerFrame")
        self.container.setStyleSheet("background: transparent; border: none;")
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(15, 0, 15, 0)
        self.container_layout.setSpacing(10)
        
        # Pre-create 3 subtitle blocks
        self.blocks = [SubtitleBlock(self.container) for _ in range(3)]
        
        # Add stretches and blocks to layout
        self.container_layout.addStretch()
        for block in self.blocks:
            self.container_layout.addWidget(block, alignment=Qt.AlignmentFlag.AlignCenter)
            block.hide()
        self.container_layout.addStretch()
        
        # Show initial greeting block
        self.blocks[0].label_src.setText("Subtitle Overlay Ready")
        self.blocks[0].label_src.show()
        self.blocks[0].show()
        
        layout.addWidget(self.container)

    def set_style_config(self, config: dict):
        """
        Update the overlay aesthetics (colors, fonts, layout settings) dynamically.
        """
        self.style_config = config
        self.bottom_offset = int(config.get("bottom_offset", 35))
        self.history_limit = int(config.get("history_limit", 1))
        
        # Retrieve and parse transcription alignments
        align_str = config.get("transcription_align", "middle")
        if align_str == "left":
            self.layout_alignment = Qt.AlignmentFlag.AlignLeft
            self.text_alignment = Qt.AlignmentFlag.AlignLeft
        elif align_str == "right":
            self.layout_alignment = Qt.AlignmentFlag.AlignRight
            self.text_alignment = Qt.AlignmentFlag.AlignRight
        else:  # middle
            self.layout_alignment = Qt.AlignmentFlag.AlignCenter
            self.text_alignment = Qt.AlignmentFlag.AlignCenter
            
        # Apply layout alignment to all subtitle blocks
        for block in self.blocks:
            self.container_layout.setAlignment(block, self.layout_alignment)
        
        # Trim history to the new limit
        while len(self.history) > self.history_limit:
            self.history.pop(0)
            
        # Rerender current state
        if getattr(self, "current_status_msg", None) is not None:
            self.show_status_message(self.current_status_msg[0], self.current_status_msg[1])
        else:
            self.render_history()
            
        # Reposition (calculates proportional height based on self.history_limit)
        self.reposition(self.current_position)

    def _apply_opacity_to_color(self, color_str: str, opacity: float) -> str:
        """Parses rgba(r,g,b,a) or rgb(r,g,b) or #rrggbb and returns rgba(r,g,b,opacity)."""
        try:
            clean_str = color_str.strip().lower()
            if clean_str.startswith("rgba"):
                parts = clean_str.split("(")[1].split(")")[0].split(",")
                return f"rgba({parts[0].strip()}, {parts[1].strip()}, {parts[2].strip()}, {opacity:.2f})"
            elif clean_str.startswith("rgb"):
                parts = clean_str.split("(")[1].split(")")[0].split(",")
                return f"rgba({parts[0].strip()}, {parts[1].strip()}, {parts[2].strip()}, {opacity:.2f})"
            else:
                color = QColor(clean_str)
                if color.isValid():
                    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {opacity:.2f})"
        except Exception as e:
            print(f"Error applying opacity to color {color_str}: {e}")
        return f"rgba(255, 255, 255, {opacity:.2f})"

    def _apply_opacity_to_text(self, color_str: str, opacity: float) -> str:
        """Parses a text color and applies the target opacity for historical fading."""
        try:
            clean_str = color_str.strip().lower()
            if clean_str.startswith("rgba"):
                parts = clean_str.split("(")[1].split(")")[0].split(",")
                return f"rgba({parts[0].strip()}, {parts[1].strip()}, {parts[2].strip()}, {opacity:.2f})"
            elif clean_str.startswith("rgb"):
                parts = clean_str.split("(")[1].split(")")[0].split(",")
                return f"rgba({parts[0].strip()}, {parts[1].strip()}, {parts[2].strip()}, {opacity:.2f})"
            else:
                color = QColor(clean_str)
                if color.isValid():
                    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {opacity:.2f})"
        except Exception as e:
            print(f"Error applying opacity to text {color_str}: {e}")
        return color_str

    def _style_block(self, block, is_current: bool):
        """Dynamically style an individual block frame and its internal labels."""
        if not getattr(self, "style_config", None):
            return
            
        bg_color = self.style_config.get("bg_color", "rgba(255, 255, 255, 0.78)")
        bg_opacity = float(self.style_config.get("bg_opacity", 0.78))
        text_color = self.style_config.get("text_color", "#000000")
        font_family = self.style_config.get("font_family", "Segoe UI")
        font_size = int(self.style_config.get("font_size", 19))
        
        # Historical blocks fade text to 50% opacity
        text_opacity = 1.0 if is_current else 0.5
        applied_text_color = self._apply_opacity_to_text(text_color, text_opacity)
        
        applied_bg_color = self._apply_opacity_to_color(bg_color, bg_opacity)
        
        clean_bg = applied_bg_color.replace(" ", "").lower()
        if "rgba(255,255,255" in clean_bg or "rgb(255,255,255" in clean_bg or "#fff" in clean_bg:
            border_color = "rgba(0, 0, 0, 0.12)"
        else:
            border_color = "rgba(255, 255, 255, 0.12)"
            
        block.setStyleSheet(f"""
            QFrame#SubtitleBlock {{
                background-color: {applied_bg_color};
                border: 1.5px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        src_font_size = max(10, font_size - 4)
        
        block.label_src.setAlignment(self.text_alignment)
        block.label_src.setStyleSheet(f"""
            color: {applied_text_color};
            font-family: '{font_family}', 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            font-size: {src_font_size}px;
            font-weight: 500;
            background: transparent;
            border: none;
        """)
        
        block.label_trg1.setAlignment(self.text_alignment)
        block.label_trg1.setStyleSheet(f"""
            color: {applied_text_color};
            font-family: '{font_family}', 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            font-size: {font_size}px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        
        block.label_trg2.setAlignment(self.text_alignment)
        block.label_trg2.setStyleSheet(f"""
            color: {applied_text_color};
            font-family: '{font_family}', 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            font-size: {font_size}px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)

    def get_current_text(self) -> tuple:
        """Return the current source and translations displayed on the overlay."""
        if getattr(self, "current_status_msg", None) is not None:
            return self.current_status_msg
            
        if self.history:
            return self.history[-1]
            
        return ("Subtitle Overlay Ready", ["", ""])

    def update_text(self, src: str, translations: list, is_preview: bool = False):
        """
        Update the subtitle text. Appends real transcriptions to history,
        or displays temporary status messages. Bypasses history during previews.
        """
        is_status = is_preview or src in ("...", "Session Paused", "Session Resumed", "Subtitle Overlay Ready") or not src.strip()
        
        if is_status:
            if not is_preview:
                self.current_status_msg = (src, translations)
            self.show_status_message(src, translations)
        else:
            self.current_status_msg = None
            self.history.append((src, translations))
            while len(self.history) > self.history_limit:
                self.history.pop(0)
            self.render_history()
            
        self.reposition(self.current_position)

    def show_status_message(self, src: str, translations: list):
        """Display a single temporary status message block."""
        for i, block in enumerate(self.blocks):
            if i == 0:
                block.label_src.setText(src)
                block.label_src.show()
                
                t1 = translations[0] if len(translations) > 0 else ""
                if t1.strip():
                    block.label_trg1.setText(t1)
                    block.label_trg1.show()
                else:
                    block.label_trg1.hide()
                    
                t2 = translations[1] if len(translations) > 1 else ""
                if t2.strip():
                    block.label_trg2.setText(t2)
                    block.label_trg2.show()
                else:
                    block.label_trg2.hide()
                    
                self._style_block(block, is_current=True)
                block.show()
            else:
                block.hide()

    def render_history(self):
        """Render active history items onto subtitle blocks."""
        H = len(self.history)
        for i in range(3):
            block = self.blocks[i]
            if i < H:
                hist_src, hist_trans = self.history[i]
                is_current = (i == H - 1)
                
                block.label_src.setText(hist_src)
                block.label_src.show()
                
                ht1 = hist_trans[0] if len(hist_trans) > 0 else ""
                if ht1.strip():
                    block.label_trg1.setText(ht1)
                    block.label_trg1.show()
                else:
                    block.label_trg1.hide()
                    
                ht2 = hist_trans[1] if len(hist_trans) > 1 else ""
                if ht2.strip():
                    block.label_trg2.setText(ht2)
                    block.label_trg2.show()
                else:
                    block.label_trg2.hide()
                    
                self._style_block(block, is_current)
                block.show()
            else:
                block.hide()

    def reposition(self, position_name: str = "bottom-center"):
        """
        Position the overlay onto one of six screen regions.
        Always forces bottom-center positioning for subtitles.
        Takes exactly 10% vertical space per active history item.
        """
        self.current_position = "bottom-center"
        position_name = "bottom-center"
        
        screen = QGuiApplication.primaryScreen()
        geometry = screen.availableGeometry()
        screen_width = geometry.width()
        screen_height = geometry.height()
        screen_x = geometry.x()
        screen_y = geometry.y()
        
        # Take screen vertical space proportional to history limit (10% per item)
        width = 950
        height = int(screen_height * 0.10) * self.history_limit
        margin = self.bottom_offset
        
        # Calculate coordinates (always bottom-center but respecting bottom_offset)
        x = screen_x + (screen_width - width) // 2
        y = screen_y + screen_height - height - margin
            
        self.setGeometry(x, y, width, height)
