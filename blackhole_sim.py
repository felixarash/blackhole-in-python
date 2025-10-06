import sys
import math
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QBrush, QRadialGradient, QMouseEvent, QWheelEvent

class BlackHoleWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        
        # Black hole properties
        self.black_hole_radius = 30
        self.accretion_disk_inner = self.black_hole_radius * 1.5
        self.accretion_disk_outer = self.black_hole_radius * 6
        self.gravitational_lensing_radius = self.black_hole_radius * 3
        
        # Camera controls
        self.zoom_level = 1.0
        self.rotation_x = 0
        self.rotation_y = 0
        self.prev_mouse_x, self.prev_mouse_y = 0, 0
        self.is_dragging = False
        
        # Stars for background
        self.stars = []
        for _ in range(500):
            x = random.randint(-1000, 1000)
            y = random.randint(-1000, 1000)
            z = random.randint(1, 10)
            brightness = random.random() * 0.7 + 0.3
            self.stars.append((x, y, z, brightness))
        
        # Particles for accretion disk
        self.particles = []
        for _ in range(1500):
            distance = random.uniform(self.accretion_disk_inner, self.accretion_disk_outer)
            angle = random.uniform(0, 2 * math.pi)
            speed = 0.02 / math.sqrt(distance)  # Keplerian motion
            size = random.uniform(1.0, 3.0)
            brightness = random.random() * 0.5 + 0.5
            # Color based on temperature (inner disk is hotter)
            if distance < self.accretion_disk_inner * 2:
                color = (255, 100, 50)  # Orange-red
            elif distance < self.accretion_disk_inner * 3:
                color = (255, 150, 100)  # Orange
            else:
                color = (150, 150, 255)  # Blue-white
            self.particles.append({
                'distance': distance,
                'angle': angle,
                'speed': speed,
                'size': size,
                'color': color,
                'brightness': brightness
            })
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)  # ~60 FPS

    def update_particles(self):
        for particle in self.particles:
            particle['angle'] += particle['speed']
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear with black background
        painter.fillRect(self.rect(), Qt.black)
        
        width, height = self.width(), self.height()
        center_x, center_y = width // 2, height // 2
        
        # Draw stars
        for star in self.stars:
            x, y, z, brightness = star
            # Calculate star position with simple parallax
            star_x = center_x + (x - center_x) / z * self.zoom_level
            star_y = center_y + (y - center_y) / z * self.zoom_level
            
            # Draw if visible
            if 0 <= star_x < width and 0 <= star_y < height:
                color_val = int(255 * brightness)
                painter.setPen(QColor(color_val, color_val, color_val))
                painter.drawPoint(int(star_x), int(star_y))
        
        # Draw accretion disk
        for particle in self.particles:
            # Apply rotation
            angle = particle['angle'] + self.rotation_y * 0.01
            distance = particle['distance']
            
            # 3D projection (simplified)
            x = center_x + math.cos(angle) * distance * self.zoom_level
            y = center_y + math.sin(angle) * distance * self.zoom_level * math.cos(self.rotation_x)
            
            # Size and brightness based on zoom and position
            size = max(1, particle['size'] * self.zoom_level)
            brightness = particle['brightness'] * (1 - (distance - self.accretion_disk_inner) / 
                                                  (self.accretion_disk_outer - self.accretion_disk_inner))
            
            # Calculate color with brightness
            r, g, b = particle['color']
            color = QColor(int(r * brightness), int(g * brightness), int(b * brightness))
            painter.setPen(color)
            painter.setBrush(QBrush(color))
            
            # Draw the particle
            if size < 2:
                painter.drawPoint(int(x), int(y))
            else:
                painter.drawEllipse(int(x - size/2), int(y - size/2), int(size), int(size))
        
        # Draw gravitational lensing effect (simplified)
        gradient = QRadialGradient(center_x, center_y, self.gravitational_lensing_radius * self.zoom_level)
        gradient.setColorAt(0, QColor(50, 50, 70, 200))
        gradient.setColorAt(1, Qt.transparent)
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(center_x - self.gravitational_lensing_radius * self.zoom_level),
            int(center_y - self.gravitational_lensing_radius * self.zoom_level),
            int(self.gravitational_lensing_radius * self.zoom_level * 2),
            int(self.gravitational_lensing_radius * self.zoom_level * 2)
        )
        
        # Draw black hole (event horizon)
        painter.setBrush(Qt.black)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(center_x - self.black_hole_radius * self.zoom_level),
            int(center_y - self.black_hole_radius * self.zoom_level),
            int(self.black_hole_radius * self.zoom_level * 2),
            int(self.black_hole_radius * self.zoom_level * 2)
        )

        # Draw photon ring
        painter.setPen(QColor(50, 50, 70))
        painter.setBrush(Qt.NoBrush)
        for i in range(3):
            ring_radius = self.black_hole_radius * self.zoom_level * (1.1 + i * 0.3)
            painter.drawEllipse(
                int(center_x - ring_radius),
                int(center_y - ring_radius),
                int(ring_radius * 2),
                int(ring_radius * 2)
            )

        # Draw instructions
        painter.setPen(Qt.white)
        painter.drawText(10, 20, "Mouse drag: Rotate black hole")
        painter.drawText(10, 40, "Mouse wheel: Zoom in/out")
        painter.drawText(10, 60, f"Zoom: {self.zoom_level:.1f}x")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.prev_mouse_x, self.prev_mouse_y = event.x(), event.y()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            x, y = event.x(), event.y()
            self.rotation_y += (x - self.prev_mouse_x) * 0.01
            self.rotation_x += (y - self.prev_mouse_y) * 0.01
            # Limit x rotation to avoid flipping
            self.rotation_x = max(-math.pi/2, min(math.pi/2, self.rotation_x))
            self.prev_mouse_x, self.prev_mouse_y = x, y
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1
        # Limit zoom
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interstellar Black Hole Simulation")
        self.setCentralWidget(BlackHoleWidget())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())