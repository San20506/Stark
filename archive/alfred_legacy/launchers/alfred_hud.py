"""
ALFRED HUD - Holographic User Interface
Wraps the core voice assistant in a futuristic PyQt6 GUI.
"""

import sys
import threading
import time
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QHBoxLayout, QFrame, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QPoint, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QRadialGradient

# Import main Alfred class
try:
    from main import Alfred, AssistantState
except ImportError:
    # Allow running GUI without backend for testing
    Alfred = None

# ============================================================================
# STYLING CONSTANTS
# ============================================================================

THEME_COLOR = QColor("#00CCFF")  # Cyan/Blue "Iron Man" color
BG_COLOR = QColor(10, 15, 20, 220)  # Dark Blue-Black, Semi-transparent
TEXT_COLOR = QColor("#E0FFFF")
FONT_FAMILY = "Segoe UI"  # Or "Consolas" for more tech feel

STYLE_SHEET = f"""
QMainWindow {{
    background-color: transparent;
}}
QLabel {{
    color: {TEXT_COLOR.name()};
    font-family: '{FONT_FAMILY}';
}}
QFrame#MainFrame {{
    background-color: rgba(10, 15, 20, 220);
    border: 1px solid {THEME_COLOR.name()};
    border-radius: 15px;
}}
"""

# ============================================================================
# WORKER THREAD FOR ALFRED
# ============================================================================

class AlfredWorker(QThread):
    """Runs the Alfred voice assistant in a background thread."""
    text_updated = pyqtSignal(str, str)  # type ("user" or "alfred"), text
    state_updated = pyqtSignal(str)      # "listening", "processing", "speaking"
    
    def __init__(self):
        super().__init__()
        self.alfred = None
        self._is_running = True

    def run(self):
        if not Alfred:
            self.text_updated.emit("alfred", "Backend not found. Demo mode.")
            return

        self.alfred = Alfred()
        
        # Monkey-patch or hook into Alfred's state to emit signals
        # This is a bit hacky but effective for wrapping an existing class
        original_speak = self.alfred.tts.speak
        original_transcribe = self.alfred.state.last_transcription
        
        self.alfred.start()
        
    def stop(self):
        if self.alfred:
            self.alfred.stop()
        self.quit()

class AlfredStatePoller(QThread):
    """
    Since Alfred.start() blocks, we run Alfred in one thread,
    and this poller monitors its state object in another.
    """
    state_signal = pyqtSignal(str)       # status text
    viz_signal = pyqtSignal(float)       # audio amplitude for visualizer
    transcript_signal = pyqtSignal(str, str) # type, text

    def __init__(self, alfred_instance):
        super().__init__()
        self.alfred = alfred_instance
        self.last_transcript = ""
        self.last_history_len = 0
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.1)
            if not self.alfred: continue

            # Check Status
            status = "IDLE"
            # access state safely?
            if hasattr(self.alfred, 'state'):
                if self.alfred.state.speaking:
                    status = "SPEAKING"
                elif self.alfred.state.listening: 
                    status = "LISTENING"
                
                # Inference overlay
                if hasattr(self.alfred.tts, 'tts_thread') and self.alfred.tts.tts_thread and self.alfred.tts.tts_thread.is_alive():
                    status = "SPEAKING"
            
            self.state_signal.emit(status)

            # Check History
            if hasattr(self.alfred.state, 'conversation_history'):
                history = self.alfred.state.conversation_history
                if len(history) > self.last_history_len:
                    new_exchange = history[-1]
                    self.transcript_signal.emit("user", new_exchange['user'])
                    self.transcript_signal.emit("alfred", new_exchange['assistant'])
                    self.last_history_len = len(history)

# ============================================================================
# CUSTOM WIDGETS
# ============================================================================

class ArcReactorWidget(QWidget):
    """A glowing, rotating circular visualizer."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)
        self.angle = 0
        self.pulse = 0
        self.active = True

    def update_animation(self):
        self.angle = (self.angle + 5) % 360
        self.pulse = (self.pulse + 0.1)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2 - 10
        
        # Outer Glow
        glow = QRadialGradient(QPointF(center), radius)
        glow.setColorAt(0, QColor(0, 200, 255, 50))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)

        # Outer Ring
        pen = QPen(THEME_COLOR)
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - 10, radius - 10)

        # Rotating Arc
        pen.setWidth(5)
        painter.setPen(pen)
        painter.drawArc(10 + 10, 10 + 10, self.width()-40, self.height()-40, int(self.angle * 16), 120 * 16)
        painter.drawArc(10 + 10, 10 + 10, self.width()-40, self.height()-40, int((self.angle + 180) * 16), 120 * 16)

        # Inner Core
        core_radius = 40 + int(np.sin(self.pulse) * 5)
        painter.setBrush(QBrush(THEME_COLOR))
        painter.drawEllipse(center, core_radius, core_radius)


class HolographicWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ALFRED HUD")
        self.setGeometry(100, 100, 800, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Main Frame (The glass pane)
        self.frame = QFrame()
        self.frame.setObjectName("MainFrame")
        self.frame_layout = QVBoxLayout(self.frame)
        self.layout.addWidget(self.frame)
        
        # Header
        self.header_layout = QHBoxLayout()
        self.title_label = QLabel("ALFRED SYSTEM V2.0")
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold; letter-spacing: 2px;")
        self.status_label = QLabel("ONLINE")
        self.status_label.setStyleSheet("color: #00FF00; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.status_label)
        self.frame_layout.addLayout(self.header_layout)
        
        # Content Area
        self.content_layout = QHBoxLayout()
        
        # Left: Viz
        self.reactor = ArcReactorWidget()
        self.content_layout.addWidget(self.reactor)
        
        # Right: Text
        self.text_display = QLabel("Initializing systems...\nWaiting for voice command...")
        self.text_display.setWordWrap(True)
        self.text_display.setStyleSheet(f"font-size: 16pt; color: {TEXT_COLOR.name()}; padding: 10px;")
        self.text_display.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.text_display, stretch=1)
        
        self.frame_layout.addLayout(self.content_layout)
        
        # Footer
        self.footer_label = QLabel("CPU: --% | RAM: --% | NETWORK: SECURE")
        self.footer_label.setStyleSheet("color: #888888; font-size: 10pt;")
        self.frame_layout.addWidget(self.footer_label)

        # Apply Styles
        self.setStyleSheet(STYLE_SHEET)
        
        # Mouse Drag Logic
        self.old_pos = None

        # Start Backend Thread
        self.start_backend()

    def start_backend(self):
        # NOTE: In a real implementation, we'd need to refactor main.py 
        # to be more friendly to external control. 
        # For this prototype, we will just simulate the connection or 
        # run a dummy process if Alfred isn't importable.
        if Alfred:
             # Run full backend
             self.worker = AlfredWorker()
             self.worker.start()
             
             # Poller
             self.poller = AlfredStatePoller(self.worker.alfred) 
             # This race condition needs fixing.
             QTimer.singleShot(1000, self.attach_poller)
        else:
            self.text_display.setText("DEMO MODE: Alfred backend not found.")

    def attach_poller(self):
        if self.worker.alfred:
            self.poller = AlfredStatePoller(self.worker.alfred)
            self.poller.transcript_signal.connect(self.update_transcript)
            self.poller.state_signal.connect(self.update_status)
            self.poller.start()

    def update_transcript(self, role, text):
        prefix = "YOU: " if role == "user" else "ALFRED: "
        color = "#FFFFFF" if role == "user" else THEME_COLOR.name()
        current = self.text_display.text()
        
        # Keep last 3 lines
        lines = current.split('\n')
        if len(lines) > 4:
            lines = lines[-4:]
            
        new_line = f"<span style='color:{color}'><b>{prefix}</b> {text}</span>"
        # We need to handle HTML in label or use a TextEdit
        # Label supports simple HTML
        self.text_display.setText(current + "\n" + f"{prefix}{text}") # Simplified for label safely

    def update_status(self, status):
        self.status_label.setText(status)
        if status == "SPEAKING":
            self.status_label.setStyleSheet(f"color: {THEME_COLOR.name()};")
        else:
             self.status_label.setStyleSheet("color: #00FF00;")

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HolographicWindow()
    window.show()
    sys.exit(app.exec())
