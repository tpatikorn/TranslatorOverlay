from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, QStyle
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QMouseEvent

class ControlMenu(QWidget):
    """
    Floating control menu window pinned near the overlay.
    Fades smoothly between transparent (0.4) and opaque (0.95) based on hover and focus.
    Provides Play/Pause toggle, Settings, and Exit buttons.
    """
    def __init__(self, position_name: str = "bottom-center"):
        super().__init__()
        self.current_position = position_name
        self.paused = False
        
        # Frameless, stays on top, tool window (not in taskbar)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowOpacity(0.4)
        
        # Smooth fade animation setup
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Support dragging the control menu (optional convenience)
        self.drag_position = None
        
        self.init_ui()

    def init_ui(self):
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main container frame
        self.container = QFrame(self)
        self.container.setObjectName("MenuContainer")
        self.container.setStyleSheet("""
            QFrame#MenuContainer {
                background-color: rgba(22, 22, 29, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
        """)
        
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(15, 6, 15, 6)
        container_layout.setSpacing(10)
        
        # Fetch standard QStyle icons for modern cross-platform visuals
        style = self.style()
        self.icon_play = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.icon_pause = style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        self.icon_settings = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.icon_exit = style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        
        # Title Label
        self.label_title = QLabel("Overlay Captioner", self)
        self.label_title.setStyleSheet("""
            color: #FFFFFF;
            font-family: 'Outfit', 'Inter', 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        
        # Separator line
        self.separator = QFrame(self)
        self.separator.setFrameShape(QFrame.Shape.VLine)
        self.separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); width: 1px;")
        self.separator.setFixedWidth(1)
        
        # Pause / Play Button (Fixed size 100px so it doesn't jitter when text changes)
        self.btn_pause = QPushButton("Pause", self)
        self.btn_pause.setIcon(self.icon_pause)
        self.btn_pause.setFixedWidth(100)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet(self.get_button_style(is_pause=True, active=True))
        
        # Settings Button
        self.btn_settings = QPushButton("Settings", self)
        self.btn_settings.setIcon(self.icon_settings)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setStyleSheet(self.get_button_style())
        
        # Exit Button
        self.btn_exit = QPushButton("Exit", self)
        self.btn_exit.setIcon(self.icon_exit)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                color: #FCA5A5;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.35);
                color: #FFFFFF;
                border: 1px solid rgba(239, 68, 68, 0.5);
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.5);
            }
        """)
        
        # Assemble
        container_layout.addWidget(self.label_title)
        container_layout.addWidget(self.separator)
        container_layout.addWidget(self.btn_pause)
        container_layout.addWidget(self.btn_settings)
        container_layout.addWidget(self.btn_exit)
        
        layout.addWidget(self.container)
        self.setFixedSize(430, 48)

    def get_button_style(self, is_pause=False, active=True):
        if is_pause:
            if active:  # App is playing, showing "Pause" button
                return """
                    QPushButton {
                        background-color: rgba(6, 182, 212, 0.15);
                        color: #67E8F9;
                        border: 1px solid rgba(6, 182, 212, 0.3);
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-family: 'Inter', 'Segoe UI', sans-serif;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: rgba(6, 182, 212, 0.35);
                        color: #FFFFFF;
                        border: 1px solid rgba(6, 182, 212, 0.5);
                    }
                """
            else:  # App is paused, showing "Resume" button
                return """
                    QPushButton {
                        background-color: rgba(234, 179, 8, 0.15);
                        color: #FEF08A;
                        border: 1px solid rgba(234, 179, 8, 0.3);
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-family: 'Inter', 'Segoe UI', sans-serif;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: rgba(234, 179, 8, 0.35);
                        color: #FFFFFF;
                        border: 1px solid rgba(234, 179, 8, 0.5);
                    }
                """
        else:
            return """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #E2E8F0;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-family: 'Inter', 'Segoe UI', sans-serif;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.3);
                }
            """

    def toggle_pause_style(self, is_paused: bool):
        self.paused = is_paused
        if self.paused:
            self.btn_pause.setText("Resume")
            self.btn_pause.setIcon(self.icon_play)
            self.btn_pause.setStyleSheet(self.get_button_style(is_pause=True, active=False))
        else:
            self.btn_pause.setText("Pause")
            self.btn_pause.setIcon(self.icon_pause)
            self.btn_pause.setStyleSheet(self.get_button_style(is_pause=True, active=True))

    def position_near_overlay(self, overlay_geometry):
        """Position the control menu directly above the overlay bottom-center."""
        width = self.width()
        height = self.height()
        
        # Reference coordinates of overlay (which stays at bottom-center)
        overlay_x = overlay_geometry.x()
        overlay_y = overlay_geometry.y()
        overlay_w = overlay_geometry.width()
        
        # Center relative to overlay, position just above it
        x = overlay_x + (overlay_w - width) // 2
        y = overlay_y - height - 12
            
        self.move(x, y)

    # Hover and Focus opacity fade implementation
    def fade_to_opacity(self, target_opacity: float):
        if self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(target_opacity)
        self.fade_animation.start()

    def update_opacity(self):
        # We fade to 0.95 (fully readable but keeping glass look) if mouse is hovering
        # OR if this menu window is currently the active window. Otherwise, fade back to 0.4.
        is_hovered = self.underMouse()
        is_active = self.isActiveWindow()
        
        target = 0.95 if (is_hovered or is_active) else 0.4
        self.fade_to_opacity(target)

    def enterEvent(self, event):
        self.update_opacity()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_opacity()
        super().leaveEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            self.update_opacity()
        super().changeEvent(event)

    # Optional drag interaction to move the control menu individually
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.drag_position = None
        super().mouseReleaseEvent(event)
