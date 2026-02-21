import sys
import math
import random
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel,
                             QFrame, QSizePolicy, QGraphicsView,
                             QGraphicsScene, QStackedLayout)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QWheelEvent, QIcon, QFontDatabase, QPixmap, QImage, QBrush, QColor, QPainter, QLinearGradient, QPainter, QFontMetrics


from DB import DataBaseManager
from Twitch_bot import TwitchBot
from QRCode import Create_QRCode


class AnimatedColumn(QWidget):
    def __init__(self, font_manager=None, target_height=200, color=None,
                 number=0.0, image_path=None, label_text=""):
        super().__init__()
        self.target_height = target_height
        self.font_manager = font_manager
        self.color = color
        self.label_text = label_text
        self.number = round(number, 1)
        self.current_height = 0

        self.pixmap = QPixmap(image_path) if image_path else QPixmap()
        if not self.pixmap.isNull():

            if self.pixmap.width() > 240:
                self.pixmap = self.pixmap.scaledToWidth(240, Qt.TransformationMode.SmoothTransformation)

        self.setFixedWidth(240)
        image_height = self.pixmap.height()

        self.label_height = 0
        if self.label_text:
            font = self.font_manager.get_Font("InterTight", 16)
            fm = QFontMetrics(font)
            self.label_height = fm.height() + 6
        else:
            self.label_height = 0

        total_height = target_height + image_height+ self.label_height + 30
        self.setMinimumHeight(total_height)

        duration_ms = max(1, int(self.target_height / 120 * 1000))
       
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0)
        self.animation.setEndValue(target_height)
        self.animation.setDuration(duration_ms)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.animation.valueChanged.connect(self._on_value_changed)

    def _on_value_changed(self, value):
       
        self.current_height = value
        self.update() 

    def start_animation(self):
       
        self.animation.start()

    def stop_animation(self):
       
        self.animation.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        col_area_height = self.height() - self.label_height
        col_width = self.width()
        col_height = self.current_height
        col_bottom_y = self.height() - self.label_height
        col_top_y = col_bottom_y - col_height
        col_rect = QRectF(0, col_top_y, col_width, col_height)
        

       
        painter.fillRect(col_rect, self.color)

        progress = self.current_height / self.target_height if self.target_height > 0 else 0.0
        if progress >= 1.0 - 1e-9:
            display_number = self.number
        else:
            # Целочисленное деление на 10 даёт шаг 0.1
            display_number = int(progress * self.number * 10) / 10.0
        # Draw the number inside the column (centered)
        if col_height > 20:
            font = self.font_manager.get_Font("TikTokSans", 64)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor(32, 32 ,33))
            painter.drawText(col_rect, Qt.AlignmentFlag.AlignCenter, str(display_number))

        # Draw image above the column (if available)
        if not self.pixmap.isNull():
            image_height = self.pixmap.height()
            image_width = self.pixmap.width()
            image_bottom_y = col_top_y -30
            image_top_y = image_bottom_y - image_height
            # Center horizontally (use float for consistency, but int is fine)
            image_x = (self.width() - image_width) / 2.0
            # Use QPointF to allow floating-point coordinates
            painter.drawPixmap(QPointF(image_x, image_top_y), self.pixmap)

        if self.label_text:
            label_font = self.font_manager.get_Font("InterTight", 16)
            painter.setFont(label_font)
            painter.setPen(Qt.GlobalColor.white)
            
            label_rect = QRectF(0, self.height() - self.label_height, self.width(), self.label_height)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self.label_text)

        painter.end()


class FontManager():
    def __init__(self):
        self.id1 = QFontDatabase.addApplicationFont("Fonts/Inter/Inter-SemiBold.otf") 
        self.id2 = QFontDatabase.addApplicationFont("Fonts/InterTight/InterTight-SemiBold.ttf")
        self.id3 = QFontDatabase.addApplicationFont("Fonts/TikTokSans/TikTokSans.ttf")
    def get_Font(self, name, size):
        if name == "Inter":
            family = QFontDatabase.applicationFontFamilies(self.id1)[0]
        elif name == "InterTight":
            family = QFontDatabase.applicationFontFamilies(self.id2)[0]
        elif name == "TikTokSans":
            family = QFontDatabase.applicationFontFamilies(self.id3)[0]
        else:
            print(f"Error: couldn't find font '{name}'")
            return -1
        return QFont(family, size)

class InteractiveGraphicsView(QGraphicsView):

    scaleChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.pixmap_item = None

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.setFrameStyle(0)
        self.setStyleSheet("background: transparent;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.panning = False
        self.pan_start = QPointF()

        self.zoom_factor = 1.1
        self.min_scale = 0.1
        self.max_scale = 10.0
        self.current_scale = 1.0

        self.first_image_loaded = False
        
    def set_image(self, pixmap):

        if self.pixmap_item:
            self.scene.removeItem(self.pixmap_item)

        self.pixmap_item = self.scene.addPixmap(pixmap)

        self.scene.setSceneRect(QRectF(pixmap.rect()))

        self.reset_transform()

        self.center_on_image()
        
        self.first_image_loaded = True
        
        
    def reset_transform(self):
        self.resetTransform()
        self.current_scale = 1.0
        self.scaleChanged.emit(self.current_scale)
    
    def center_on_image(self):
        if self.pixmap_item:
            self.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
            
            transform = self.transform()
            self.current_scale = transform.m11()
            self.scaleChanged.emit(self.current_scale)
    
    def wheelEvent(self, event):
        if not self.pixmap_item:
            return
            
        zoom_out = event.angleDelta().y() < 0
        zoom_factor = 1 / self.zoom_factor if zoom_out else self.zoom_factor
        
        new_scale = self.current_scale * zoom_factor
        if new_scale < self.min_scale or new_scale > self.max_scale:
            return
        
        self.scale(zoom_factor, zoom_factor)
        self.current_scale *= zoom_factor
        self.scaleChanged.emit(self.current_scale)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap_item:

            self.panning = True
            self.pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.panning and self.pixmap_item:

            delta = event.pos() - self.pan_start
            self.pan_start = event.pos()
            
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if self.pixmap_item and not self.first_image_loaded:
            self.center_on_image()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags())
        self.twitch_bot = TwitchBot()
        self.font_manager = FontManager()
        self.db = DataBaseManager()
        self.i = 0
        self.initUI()
        

    def initUI(self):
        self.db.current_id = 0
        self.setWindowTitle('Poll App')
        self.setGeometry(0, 0, 1920, 1080)
        self.setStyleSheet("background-color: rgb(32, 32, 33);")
        # self.setStyleSheet("background-color: rgb(255, 255, 255);")
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный горизонтальный layout
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # === ЛЕВАЯ ЧАСТЬ ===
        left_container = QFrame()
        left_container.setFrameShape(QFrame.Shape.StyledPanel)
        left_container.setStyleSheet("""  
            border: none;
        """)
        left_container.setFixedWidth(1440)
        left_layout = QVBoxLayout(left_container)
        image_container = QFrame()
        image_container.setStyleSheet("""
            border: none;
        """)
        image_layout = QHBoxLayout(image_container)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        
        self.current_image_view = InteractiveGraphicsView()
        
        image = QImage(self.db.authors[self.db.current_id]["art_path"])
        #self.current_image_view.setMaximumSize(image.width(), image.height())
        self.current_image_view.set_image(QPixmap.fromImage(image))

        #self.current_image_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        image_layout.addWidget(self.current_image_view)

        left_layout.addWidget(image_container, 1)
        
        #=== ПАНЕЛЬ С КНОПКАМИ ===
        button_frame = QFrame()
        button_layout = QHBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setSpacing(0)
        
        self.previous_btn = QPushButton()
        self.previous_btn.setFixedHeight(47)
        self.previous_btn.setFixedWidth(72)
        self.previous_btn.clicked.connect(self.PreviousButtonClickEvent)
        self.previous_btn.setStyleSheet("""
            QPushButton {
                background-image: url(./images/Left_Arrow.png);
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(10, 10, 10, 100);
                color: rgba(255, 255, 255, 255);
                border: none;
                margin: 0px;
                padding: 0px;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }
            
            QPushButton:hover {
                background-color: rgba(15, 15, 15, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 100);
            }
        """)

        self.vote_btn = QPushButton("Начать голосование")
        self.vote_btn.setFont(self.font_manager.get_Font("Inter", 20))
        self.vote_btn.setFixedHeight(49)
        self.vote_btn.clicked.connect(self.VoteButtonClickEvent)
        self.vote_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(10, 10, 10, 100);
                color: rgba(255, 255, 255, 255);
                border: none;
                margin: 0px;
                padding: 10px;
                font-weight: semi-bold;
            }
            
            QPushButton:hover {
                background-color: rgba(15, 15, 15, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 100);
            }
        """)

        self.next_btn = QPushButton()
        self.next_btn.setFixedHeight(47)
        self.next_btn.setFixedWidth(72)
        self.next_btn.clicked.connect(self.NextButtonClickEvent)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-image: url(./images/Right_Arrow.png);
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(10, 10, 10, 100);
                color: rgba(255, 255, 255, 255);
                border: none;
                margin: 0px;
                padding: 0px;
            }
            
            QPushButton:hover {
                background-color: rgba(15, 15, 15, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 100);
            }
        """)
        
        self.refresh_btn = QPushButton()
        self.refresh_btn.setFixedHeight(47)
        self.refresh_btn.setFixedWidth(72)
        self.refresh_btn.clicked.connect(self.RefreshButtonClickEvent)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-image: url(./images/Refresh.png);
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(10, 10, 10, 100);
                color: rgba(255, 255, 255, 255);
                border: none;
                margin: 0px;
                padding: 0px;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            
            QPushButton:hover {
                background-color: rgba(15, 15, 15, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 100);
            }
        """)
        if self.db.total_scores == self.db.total_authors:
                self.InitPodiumButton()
        

        button_layout.addWidget(self.previous_btn)
        button_layout.addWidget(self.vote_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.refresh_btn)

        left_layout.addWidget(button_frame)
        
        # === ПРАВАЯ ЧАСТЬ ===
        self.right_container = QFrame()
        self.right_container.setMinimumWidth(400)
        self.right_container.setStyleSheet("""
            border: none;
            border-left: 2px solid rgba(0, 0, 0, 100);
        """)
        self.right_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Верхняя правая часть - информация об авторе
        author_frame = QFrame()
        author_frame.setFrameShape(QFrame.Shape.StyledPanel)
        author_frame.setFixedHeight(100)
        author_frame.setStyleSheet("""
                border: none;
                border-bottom: 2px solid rgba(0, 0, 0, 100);
        """)
        author_layout = QHBoxLayout(author_frame)
        self.author_name_box = QLabel(self.db.authors[self.db.current_id]["nickname"])
        self.author_name_box.setFont(self.font_manager.get_Font("InterTight", 24))
        self.author_name_box.setStyleSheet("""
            color: rgb(255, 255, 255);
            border: none;
        """)
        
        self.author_count_box = QLabel()
        self.author_count_box.setText(f"{self.db.authors[self.db.current_id]["id"]+1}/{self.db.total_authors}")
        self.author_count_box.setFont(self.font_manager.get_Font("InterTight", 24))
        self.author_count_box.setMaximumWidth(100)
        self.author_count_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_count_box.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0);
            color: rgb(85, 85, 85);
            border: none;
        """)

        author_layout.addWidget(self.author_name_box)
        author_layout.addWidget(self.author_count_box)
        
        self.right_layout.addWidget(author_frame)
        self.score_frame = None
        self.score_number_label = None
        self.SetScoreFrame(0)

        # === СОЕДИНЕНИЕ ЧАСТЕЙ ===
        self.main_layout.addWidget(left_container)
        self.main_layout.addWidget(self.right_container)
        
        # Установка соотношения ширины (примерно 3:1)
        self.main_layout.setStretch(0, 3)
        self.main_layout.setStretch(1, 1)
    

    def setAuthorName(self, name):
        self.author_name_box.setText(name)

    def setAuthorId(self, author_id, total_authors_count):
        self.author_count_box.setText(f"{author_id}/{total_authors_count}")

    def setAuthorImage(self, path_to_image):
        image = QImage(path_to_image)
        #self.current_image_view.setMaximumSize(image.width(), image.height())
        self.current_image_view.set_image(QPixmap.fromImage(image))
        self.current_image_view.reset_transform()
        self.current_image_view.center_on_image()

    def setAuthorScore(self, score):
        self.score_number_label.setText(score)

    def setVoteButtonText(self, text):
        self.vote_btn.setText(text)

    def PreviousButtonClickEvent(self, event):
        if(self.db.current_id == 0):
            return
        self.db.current_id -= 1
        self.setAuthorId(self.db.authors[self.db.current_id]["id"]+1, self.db.total_authors)
        self.setAuthorName(self.db.authors[self.db.current_id]["nickname"])
        self.setAuthorImage(self.db.authors[self.db.current_id]["art_path"])
        if self.db.authors[self.db.current_id]["score"]:
            self.SetScoreFrame(2)
            self.setVoteButtonText("Перейти к следующему")
        elif self.twitch_bot.poll_in_progress and self.db.current_id == self.twitch_bot.poll_art_id:
            self.SetScoreFrame(1)
            self.setVoteButtonText("Закончить голосование")
        elif self.twitch_bot.poll_in_progress and not self.db.current_id == self.twitch_bot.poll_art_id:
            self.SetScoreFrame(0)
            self.setVoteButtonText("Начать голосование")
        else:
            self.SetScoreFrame(0)
            self.setVoteButtonText("Начать голосование")

    def NextButtonClickEvent(self):
        if(self.db.current_id == self.db.total_authors-1):
            return
        self.db.current_id += 1
        self.setAuthorId(self.db.authors[self.db.current_id]["id"]+1, self.db.total_authors)
        self.setAuthorName(self.db.authors[self.db.current_id]["nickname"])
        self.setAuthorImage(self.db.authors[self.db.current_id]["art_path"])
        if self.db.authors[self.db.current_id]["score"]:
            self.SetScoreFrame(2)
            self.setVoteButtonText("Перейти к следующему")
        elif self.twitch_bot.poll_in_progress and self.db.current_id == self.twitch_bot.poll_art_id:
            self.SetScoreFrame(1)
            self.setVoteButtonText("Закончить голосование")
        elif self.twitch_bot.poll_in_progress and not self.db.current_id == self.twitch_bot.poll_art_id:
            self.SetScoreFrame(0)
            self.setVoteButtonText("Начать голосование")
        else:
            self.SetScoreFrame(0)
            self.setVoteButtonText("Начать голосование")
   
    def RefreshButtonClickEvent(self):
        if self.db.total_scores == self.db.total_authors:
            self.InitPodiumScreen()
        else:
            self.db._init_records()
            self.setAuthorId(self.db.authors[self.db.current_id]["id"]+1, self.db.total_authors)
            self.setAuthorName(self.db.authors[self.db.current_id]["nickname"])
            self.setAuthorImage(self.db.authors[self.db.current_id]["art_path"])
            if self.db.authors[self.db.current_id]["score"]:
                self.SetScoreFrame(2)
                self.setVoteButtonText("Перейти к следующему")
            elif self.twitch_bot.poll_in_progress and self.db.current_id == self.twitch_bot.poll_art_id:
                self.SetScoreFrame(1)
                self.setVoteButtonText("Закончить голосование")
            elif self.twitch_bot.poll_in_progress and not self.db.current_id == self.twitch_bot.poll_art_id:
                self.SetScoreFrame(0)
                self.setVoteButtonText("Начать голосование")
            else:
                self.SetScoreFrame(0)
                self.setVoteButtonText("Начать голосование")
        
    def VoteButtonClickEvent(self):
        self.current_image_view.reset_transform()
        self.current_image_view.center_on_image()
        if self.twitch_bot.poll_in_progress is False and self.db.authors[self.db.current_id]["score"] is None:
            self.SetScoreFrame(1)
            self.twitch_bot.poll_art_id = self.db.current_id
            self.twitch_bot.poll_in_progress = True
            self.setVoteButtonText("Закончить голосование")
        elif self.twitch_bot.poll_in_progress and self.db.current_id == self.twitch_bot.poll_art_id:
            print(self.db.total_scores, self.db.total_authors)
            if self.db.total_scores + 1 == self.db.total_authors:
                self.InitPodiumButton()
            score = str(self.twitch_bot.CalculateAverageScore())
            if score == -1:
                print("Failed to fetch score results")
                return
            self.db.authors[self.db.current_id]["score"] = score
            self.db.total_scores += 1
            self.db.UpdateScore(self.db.current_id+1, score)

            self.twitch_bot.poll_in_progress = False
            self.setVoteButtonText("Перейти к следующему")
            self.SetScoreFrame(2)
        elif self.db.authors[self.db.current_id]["score"]:
            self.NextButtonClickEvent()
    
    def SetScoreFrame(self, frameid): #0 - Discuss; 1 - Polling; 2 - Score
        if(self.score_frame):
            self.right_layout.removeWidget(self.score_frame)
        if(self.score_number_label):
            self.right_layout.removeWidget(self.score_number_label)
            self.score_number_label = None
        self.score_frame = QFrame()
        self.score_frame.setStyleSheet("""
            border: none;
        """)
        self.main_layout.removeWidget(self.right_container)

        if frameid == 0: #Discuss
            score_frame_layout = QVBoxLayout(self.score_frame)

            score_frame_header = QFrame()
            score_frame_header.setFixedHeight(39)
            score_frame_header.setStyleSheet("""
                border: none;
                margin: 0px;
            """)
            score_frame_header_layout = QHBoxLayout(score_frame_header)
            score_frame_header_layout.setContentsMargins(10, 0, 0, 0)
            score_frame_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) 

            score_frame_header_image = QLabel()
            score_frame_header_image.setFixedHeight(32)
            score_frame_header_image.setFixedWidth(32)
            score_frame_header_image.setStyleSheet("""
                QLabel{
                    background-image: url(./images/Discuss.png);
                    background-repeat: no-repeat;
                    background-position: left;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)

            score_frame_header_text = QLabel("Комментарий автора")
            score_frame_header_text.setFont(self.font_manager.get_Font("InterTight", 24))
            
            score_frame_header_text.setAlignment(Qt.AlignmentFlag.AlignTop)
            score_frame_header_text.setFixedHeight(39)
            score_frame_header_text.setStyleSheet("""
                QLabel{
                    text-align: top;
                    color: rgb(255, 255, 255);
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)

            score_frame_header_layout.addWidget(score_frame_header_image)
            score_frame_header_layout.addWidget(score_frame_header_text)

            score_frame_paragraph = QLabel(self.db.authors[self.db.current_id]["comment"])
            score_frame_paragraph.setWordWrap(True)
            score_frame_paragraph.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding)
            score_frame_paragraph.setFont(self.font_manager.get_Font("InterTight", 16))
            score_frame_paragraph.setContentsMargins(10, 0, 0, 0)
            score_frame_paragraph.setAlignment(Qt.AlignmentFlag.AlignLeft)
            score_frame_paragraph.setFixedWidth(430)
            score_frame_paragraph.setStyleSheet("""
                QLabel{
                    color: rgb(255, 255, 255);
                    border: none;
                    margin: 0px;
                    
                    padding: 0px;
                    
                }
            """)
            
            score_frame_layout.addWidget(score_frame_header)
            score_frame_layout.addWidget(score_frame_paragraph)
            

        elif frameid == 1: #Polling
            score_frame_layout = QVBoxLayout(self.score_frame)
            score_frame_header = QFrame()
            score_frame_header.setFixedHeight(39)
            score_frame_header.setStyleSheet("""
                border: none;
                margin: 0px;
            """)

            score_frame_header_layout = QHBoxLayout(score_frame_header)
            score_frame_header_layout.setContentsMargins(10, 0, 0, 0)
            score_frame_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            score_frame_header_image = QLabel()
            score_frame_header_image.setFixedHeight(32)
            score_frame_header_image.setFixedWidth(32)
            score_frame_header_image.setStyleSheet("""
                QLabel{
                    background-image: url(./images/Poll.png);
                    background-repeat: no-repeat;
                    background-position: center;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)

            score_frame_header_text = QLabel("Голосуем")
            score_frame_header_text.setFont(self.font_manager.get_Font("InterTight", 24))
            score_frame_header_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            score_frame_header_text.setFixedHeight(39)
            score_frame_header_text.setStyleSheet("""
                QLabel{
                    color: rgb(255, 255, 255);
                    border: none;
                    padding: 0px;
                }
            """)

            score_frame_header_layout.addWidget(score_frame_header_image)
            score_frame_header_layout.addWidget(score_frame_header_text)


            score_frame_paragraph = QLabel("Напишите в чат оценку от 1 до 10")
            score_frame_paragraph.setFont(self.font_manager.get_Font("InterTight", 16))
            score_frame_paragraph.setContentsMargins(10, 0, 0, 0)
            score_frame_paragraph.setAlignment(Qt.AlignmentFlag.AlignLeft)
            score_frame_paragraph.setFixedHeight(29)
            score_frame_paragraph.setStyleSheet("""
                QLabel{
                    color: rgb(255, 255, 255);
                    border: none;
                    padding: 0px;
                }
            """)

            score_frame_layout.addWidget(score_frame_header)
            score_frame_layout.addWidget(score_frame_paragraph)

            if self.db.authors[self.db.current_id]["link_social_media"]:
                score_author_link_frame_header = QFrame()
                score_author_link_frame_header.setStyleSheet("""
                    border: none;
                """)
                score_author_link_frame_header_layout = QHBoxLayout(score_author_link_frame_header)

                score_author_link_frame_header_image = QLabel()
                score_author_link_frame_header_image.setFixedHeight(32)
                score_author_link_frame_header_image.setFixedWidth(32)
                score_author_link_frame_header_image.setStyleSheet("""
                    QLabel{
                        background-image: url(./images/Link.png);
                        background-repeat: no-repeat;
                        background-position: center;
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }
                """)

                score_author_link_frame_header_text = QLabel("Автор")
                score_author_link_frame_header_text.setFont(self.font_manager.get_Font("InterTight", 24))
                score_author_link_frame_header_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
                score_author_link_frame_header_text.setFixedHeight(39)
                score_author_link_frame_header_text.setStyleSheet("""
                    QLabel{
                        color: rgb(255, 255, 255);
                        border: none;
                        margin: 0px;
                        padding: 0px;
                    }
                """)

                score_author_link_frame_header_layout.addWidget(score_author_link_frame_header_image)
                score_author_link_frame_header_layout.addWidget(score_author_link_frame_header_text) 
                

                
                
                score_frame_layout.addWidget(score_author_link_frame_header)

           
                score_author_link_code = QLabel()
                score_author_link_code.setContentsMargins(100, 0, 0, 0)
                score_author_link_code.setAlignment(Qt.AlignmentFlag.AlignRight)
                score_author_link_code.setFixedWidth(340)
                score_author_link_code.setFixedHeight(310)
                path = Create_QRCode(self.db.current_id, self.db.authors[self.db.current_id]["link_social_media"])
                score_author_link_code.setStyleSheet(f"""
                    QLabel{{
                        background-image: url({path});
                        background-repeat: no-repeat;
                        background-position: center;
                        border: none;
                        padding: 0px;
                    }}
                """)
                score_frame_layout.addWidget(score_author_link_code)

            

        elif frameid == 2: #Score
            score_frame_layout = QVBoxLayout(self.score_frame)

            self.score_frame_header = QFrame()
            self.score_frame_header.setFixedHeight(39)
            self.score_frame_header.setStyleSheet("""
                border: none;
                margin: 0px;
            """)
            score_frame_header_layout = QHBoxLayout(self.score_frame_header)
            score_frame_header_layout.setContentsMargins(10, 0, 0, 0)
            score_frame_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            
            score__star_frame_header_image = QLabel()
            score__star_frame_header_image.setFixedHeight(32)
            score__star_frame_header_image.setFixedWidth(32)
            score__star_frame_header_image.setStyleSheet("""
                QLabel{
                    background-image: url(./images/Star.png);
                    background-repeat: no-repeat;
                    background-position: center;
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)

            score_frame_header_text = QLabel("Наша оценка")
            score_frame_header_text.setFont(self.font_manager.get_Font("InterTight", 24))
            score_frame_header_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            score_frame_header_text.setFixedHeight(39)
            score_frame_header_text.setStyleSheet("""
                QLabel{
                    color: rgb(251, 145, 168);
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
                    
            score_frame_header_layout.addWidget(score__star_frame_header_image)
            score_frame_header_layout.addWidget(score_frame_header_text)
            
            self.score_number_label = QLabel(str(round(float(self.db.authors[self.db.current_id]["score"]), 1)))
            self.score_number_label.setContentsMargins(10, 0, 0 ,0)
            self.score_number_label.setFixedHeight(148)
            self.score_number_label.setFont(self.font_manager.get_Font("TikTokSans", 96))
            self.score_number_label.setStyleSheet("""
                color: rgb(251, 145, 168);
                font-weight: 900;
                border: none;
            """)

            score_frame_layout.addWidget(self.score_frame_header)
            score_frame_layout.addWidget(self.score_number_label)
        
        elif frameid == 3:
            self.setAuthorName("Итоги")
            self.setAuthorId(self.db.total_authors, self.db.total_authors)
            score_frame_layout = QVBoxLayout(self.score_frame)
            score_frame_header = QFrame()
            score_frame_header.setFixedHeight(39)
            score_frame_header.setStyleSheet("""
                border: none;
                margin: 0px;
            """)

            score_frame_header_layout = QHBoxLayout(score_frame_header)
            score_frame_header_layout.setContentsMargins(10, 0, 0, 0)
            score_frame_header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            score_frame_header_image = QLabel()
            score_frame_header_image.setFixedHeight(32)
            score_frame_header_image.setFixedWidth(32)
            score_frame_header_image.setStyleSheet("""
                QLabel{
                    background-image: url(./images/Winner.png);
                    background-repeat: no-repeat;
                    background-position: center;
                    border: none;
                    padding: 0px;
                }
            """)

            score_frame_header_text = QLabel("Победители")
            score_frame_header_text.setFont(self.font_manager.get_Font("InterTight", 24))
            score_frame_header_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            score_frame_header_text.setFixedHeight(39)
            score_frame_header_text.setStyleSheet("""
                QLabel{
                    color: rgb(255, 185, 55);
                    border: none;
                    margin: 0px;
                    padding: 0px;
                }
            """)
            score_frame_header_layout.addWidget(score_frame_header_image)
            score_frame_header_layout.addWidget(score_frame_header_text)

            score_frame_paragraph = QFrame()
            score_frame_paragraph.setFixedHeight(395)
            score_frame_paragraph.setStyleSheet("""
                
            """)
            score_frame_paragraph_layout = QVBoxLayout(score_frame_paragraph)
            for i in range(min(10, self.db.total_authors)):
                label_frame = QFrame()
                label_frame.setFixedHeight(45)
                label_frame_layout = QHBoxLayout(label_frame)

                label_text = QLabel(f"{i+1}. {self.db.authors[i]["nickname"]}")
                label_text.setFont(self.font_manager.get_Font("InterTight", 16))
                label_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
                label_text.setStyleSheet("""
                    color: rgb(255, 255, 255);
                """)

                label_score = QLabel(str(round(float(self.db.authors[i]["score"]), 1)))
                label_score.setFont(self.font_manager.get_Font("InterTight", 16))
                label_score.setAlignment(Qt.AlignmentFlag.AlignRight)
                label_score.setStyleSheet("""
                    color: rgb(255, 255, 255);
                """)

                label_frame_layout.addWidget(label_text)
                label_frame_layout.addWidget(label_score)

                score_frame_paragraph_layout.addWidget(label_frame)

            
            score_frame_layout.addWidget(score_frame_header)
            score_frame_layout.addWidget(score_frame_paragraph)

            
        self.right_layout.addWidget(self.score_frame) 
        self.main_layout.addWidget(self.right_container)
    
    def InitPodiumButton(self):
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-image: url(./images/Winner.png);
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(10, 10, 10, 100);
                color: rgba(255, 255, 255, 255);
                border: none;
                margin: 0px;
                padding: 0px;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            
            QPushButton:hover {
                background-color: rgba(15, 15, 15, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 0, 0, 100);
            }
        """)

    def InitPodiumScreen(self):
        self.db.authors.sort(key=lambda author: float(author["score"]), reverse=True)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.SetScoreFrame(3)

        left_container = QFrame()
        

        left_container_layout = QHBoxLayout(left_container)
        left_container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        left_container_layout.addStretch(1)

        group_widget = QWidget()
        group_layout = QHBoxLayout(group_widget)
        group_layout.setSpacing(30)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.column_heights = []
        for author_index, height, color in [
            (1, 240, QColor(185, 195, 194)),
            (0, 360, QColor(255, 185, 55)),
            (2, 120, QColor(234, 99, 81))
        ]:
            author = self.db.authors[author_index]
            column = AnimatedColumn(
                font_manager=self.font_manager,
                target_height=height,
                color=color,
                number=float(author["score"]),
                image_path=f"./Arts/Art{author['id'] + 1}.jpg",
                label_text=author["nickname"]
            )
            self.column_heights.append(column.height())
            group_layout.addWidget(column)
            column.start_animation()

        left_container_layout.addWidget(group_widget)

       
        left_container_layout.addStretch(2)

        
        self.solo_column = QWidget()
        # self.solo_column.setStyleSheet("border: 1px solid rgba(0, 0, 0, 100);")
        self.solo_column_layout = QStackedLayout(self.solo_column)
   
        self.solo_column_layout.setContentsMargins(0, 0, 0, 0)
        rand_num = random.randint(3, 30)
        self.column4 = AnimatedColumn(
            font_manager=self.font_manager,
            target_height=100,
            color=QColor(251, 145, 188),
            number=float(self.db.authors[rand_num]["score"]),
            image_path=f"./Arts/Art{self.db.authors[rand_num]['id'] + 1}.jpg",
            label_text=self.db.authors[rand_num]["nickname"]
        )
        self.column_heights.append(self.column4.height())
        self.solo_column.setFixedHeight(max(self.column_heights))
        self.randbutton4 = QPushButton()
        self.randbutton4.setFixedHeight(max(self.column_heights))
        self.randbutton4.setFixedWidth(240)
        self.randbutton4.clicked.connect(self.RandButtonClickEvent)
        self.randbutton4.setStyleSheet("""
            QPushButton {
                background-image: url(./images/Eye.png);
                background-repeat: no-repeat;
                background-position: center;
                background-color: rgba(126, 126, 126, 100);
                border: none;
                margin: 0px;
                padding: 0px;
                border-radius: 5px;
            }
            
            QPushButton:hover {
                background-color: rgba(140, 140, 130, 100);
            }
            
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 100);
            }
        """)


        self.solo_column_layout.addWidget(self.randbutton4)
        self.solo_column_layout.addWidget(self.column4)

        left_container_layout.addWidget(self.solo_column)

       
        left_container_layout.addStretch(1)

        self.main_layout.addWidget(left_container)
        self.main_layout.addWidget(self.right_container)

        self.main_layout.setStretch(0, 3)
        self.main_layout.setStretch(1, 1)
    
    def RandButtonClickEvent(self):
        self.solo_column_layout.setCurrentIndex(1)
        self.column4.start_animation()


def StartWindowApp():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()



    