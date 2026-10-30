import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, 
    QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem,
    QLabel, QPushButton, QSlider, QScrollArea, QSplitter, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QColor, QPen, QBrush, QFont, QPainter, QPainterPath, QShortcut, QKeySequence
import uuid

from timeline_model import Timeline, Track, Clip, TrackType

PIXELS_PER_SECOND = 100
MS_PER_PIXEL = 1000 / PIXELS_PER_SECOND

TRACK_HEIGHT = 40
TRACK_SPACING = 2
RULER_HEIGHT = 30
HEADER_WIDTH = 120

TRACK_COLORS = {
    TrackType.VIDEO: QColor("#2980b9"),     # 蓝色
    TrackType.AUDIO: QColor("#27ae60"),     # 绿色
    TrackType.SUBTITLE: QColor("#d35400"),  # 橙色
    TrackType.IMAGE: QColor("#8e44ad"),     # 紫色
    TrackType.LOGO: QColor("#e84393"),      # 粉色
    TrackType.COVER: QColor("#f39c12")      # 橙黄色
}

class TimelineRulerItem(QGraphicsItem):
    """时间轴刻度尺"""
    def __init__(self, duration_ms, parent=None):
        super().__init__(parent)
        self.duration_ms = duration_ms
        self.setZValue(50) # 高于片段，低于播放头

    def boundingRect(self):
        return QRectF(0, 0, self.duration_ms / MS_PER_PIXEL, RULER_HEIGHT)

    def paint(self, painter, option, widget):
        rect = self.boundingRect()
        # 刻度尺背景
        painter.fillRect(rect, QColor("#1E1E1E"))
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawLine(0, RULER_HEIGHT, int(rect.width()), RULER_HEIGHT)

        # 绘制时间刻度
        painter.setPen(QColor("#888888"))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)

        total_seconds = int(self.duration_ms / 1000)
        if PIXELS_PER_SECOND <= 2: step = 120
        elif PIXELS_PER_SECOND <= 5: step = 60
        elif PIXELS_PER_SECOND < 20: step = 30
        elif PIXELS_PER_SECOND > 150: step = 1
        else: step = 5
        
        for s in range(0, total_seconds + step, step):
            x = s * 1000 / MS_PER_PIXEL
            # 画短线
            painter.drawLine(int(x), RULER_HEIGHT - 8, int(x), RULER_HEIGHT)
            
            # 画文字
            m = s // 60
            sec = s % 60
            text = f"{m:02d}:{sec:02d}"
            painter.drawText(int(x) + 2, RULER_HEIGHT - 10, text)


class ClipGraphicsItem(QGraphicsItem):
    """精美的圆角素材块"""
    def __init__(self, clip: Clip, track_idx: int, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.track_idx = track_idx
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        self.resizing_left = False
        self.resizing_right = False
        self.start_scene_x = 0
        self.start_pos_x = 0
        self.start_width = 0
        self.resize_margin = 8
        self._update_geometry()
        
    def _update_geometry(self):
        x = self.clip.start_time / MS_PER_PIXEL
        y = RULER_HEIGHT + self.track_idx * (TRACK_HEIGHT + TRACK_SPACING)
        width = self.clip.duration / MS_PER_PIXEL
        
        self.clip_rect = QRectF(0, 0, width, TRACK_HEIGHT)
        self.setPos(x, y)

    def boundingRect(self):
        return self.clip_rect

    def paint(self, painter, option, widget):
        path = QPainterPath()
        path.addRoundedRect(self.clip_rect, 4, 4)
        
        base_color = TRACK_COLORS.get(self.clip.clip_type, QColor("#555555"))
        # 半透明填充
        fill_color = QColor(base_color)
        fill_color.setAlpha(180)
        
        painter.fillPath(path, QBrush(fill_color))
        
        # 描边
        if self.isSelected():
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
        else:
            painter.setPen(QPen(base_color, 1))
        painter.drawPath(path)
            
        # 文本
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        text_rect = self.clip_rect.adjusted(6, 2, -6, -2)
        
        # 对于文字类型，显示文字内容
        display_name = self.clip.source_path if self.clip.clip_type == TrackType.SUBTITLE else self.clip.name
        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(display_name, Qt.TextElideMode.ElideRight, int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_text)

    def hoverMoveEvent(self, event):
        x = event.pos().x()
        if x <= self.resize_margin or x >= self.clip_rect.width() - self.resize_margin:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        x = event.pos().x()
        if x <= self.resize_margin:
            self.resizing_left = True
            self.start_scene_x = event.scenePos().x()
            self.start_pos_x = self.pos().x()
            self.start_width = self.clip_rect.width()
        elif x >= self.clip_rect.width() - self.resize_margin:
            self.resizing_right = True
            self.start_scene_x = event.scenePos().x()
            self.start_width = self.clip_rect.width()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing_left or self.resizing_right:
            diff_x = event.scenePos().x() - self.start_scene_x
            if self.resizing_right:
                new_width = max(10, self.start_width + diff_x)
                self.clip_rect.setWidth(new_width)
                self.clip.duration = int(new_width * MS_PER_PIXEL)
            elif self.resizing_left:
                new_width = max(10, self.start_width - diff_x)
                new_x = self.start_pos_x + diff_x
                if new_x < 0:
                    new_width = self.start_width + self.start_pos_x
                    new_x = 0
                self.setPos(new_x, self.pos().y())
                self.clip_rect.setWidth(new_width)
                self.clip.start_time = int(new_x * MS_PER_PIXEL)
                self.clip.duration = int(new_width * MS_PER_PIXEL)
            
            self.prepareGeometryChange()
            if hasattr(self.scene(), 'update_scene_rect'):
                self.scene().update_scene_rect()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing_left or self.resizing_right:
            self.resizing_left = False
            self.resizing_right = False
            if hasattr(self.scene(), 'parent_widget') and self.scene().parent_widget:
                self.scene().parent_widget.clip_updated.emit(self.clip)
                self.scene().parent_widget.save_state()
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            new_pos.setY(RULER_HEIGHT + self.track_idx * (TRACK_HEIGHT + TRACK_SPACING))
            if new_pos.x() < 0:
                new_pos.setX(0)
            return new_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.clip.start_time = int(self.pos().x() * MS_PER_PIXEL)
            if hasattr(self.scene(), 'update_scene_rect'):
                self.scene().update_scene_rect()
            if hasattr(self.scene(), 'parent_widget') and self.scene().parent_widget:
                self.scene().parent_widget.clip_updated.emit(self.clip)
                self.scene().parent_widget.save_state()
        return super().itemChange(change, value)


class PlayheadItem(QGraphicsItem):
    """带倒三角的播放头"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setZValue(100) 
        self.height = 1000
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        
    def boundingRect(self):
        return QRectF(-10, 0, 20, self.height)
        
    def paint(self, painter, option, widget):
        # 画一条贯穿轨道的白线
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.drawLine(0, 0, 0, int(self.height))
        
        # 画顶部倒三角
        path = QPainterPath()
        path.moveTo(-6, 0)
        path.lineTo(6, 0)
        path.lineTo(6, 8)
        path.lineTo(0, 14)
        path.lineTo(-6, 8)
        path.closeSubpath()
        
        painter.fillPath(path, QBrush(QColor("#FFFFFF")))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            new_pos = value
            new_pos.setY(0) # 只能水平移动
            if new_pos.x() < 0:
                new_pos.setX(0)
            return new_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if hasattr(self.scene(), 'parent_widget') and self.scene().parent_widget:
                if not getattr(self.scene().parent_widget, '_is_syncing', False):
                    ms = int(self.pos().x() * MS_PER_PIXEL)
                    self.scene().parent_widget.position_changed.emit(ms)
        return super().itemChange(change, value)

class TimelineScene(QGraphicsScene):
    def __init__(self, timeline: Timeline, parent=None):
        super().__init__(parent)
        self.timeline = timeline
        self.setBackgroundBrush(QColor("#181818"))
        self.clip_items = []
        self.parent_widget = parent
        
        self.ruler = TimelineRulerItem(0)
        self.addItem(self.ruler)
        
        self.playhead = PlayheadItem()
        self.addItem(self.playhead)
        
        self.total_duration_ms = 0
        self.rebuild_ui()
        
    def rebuild_ui(self):
        for item in self.clip_items:
            self.removeItem(item)
        self.clip_items.clear()
        
        max_duration_ms = 0
        
        for i, track in enumerate(self.timeline.tracks):
            for clip in track.clips:
                item = ClipGraphicsItem(clip, i)
                self.addItem(item)
                self.clip_items.append(item)
                end_time = clip.start_time + clip.duration
                if end_time > max_duration_ms:
                    max_duration_ms = end_time
                    
        self.total_duration_ms = max(max_duration_ms, 60000) # 默认最少留1分钟空间，如果有视频会根据视频真实长度扩展
        self.ruler.duration_ms = self.total_duration_ms
        self.update_scene_rect()
        
    def update_scene_rect(self):
        width = self.total_duration_ms / MS_PER_PIXEL
        height = max(400, RULER_HEIGHT + len(self.timeline.tracks) * (TRACK_HEIGHT + TRACK_SPACING))
        
        self.setSceneRect(0, 0, width, height)
        self.playhead.height = height
        # 触发ruler重绘
        self.ruler.prepareGeometryChange()
        self.ruler.update()
        
    def set_playhead_position(self, ms: int):
        x = ms / MS_PER_PIXEL
        self.playhead.setPos(x, 0)

class TimelineWidget(QWidget):
    position_changed = pyqtSignal(int)
    clip_selected = pyqtSignal(object)
    clip_updated = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline_model = Timeline()
        self.undo_stack = []
        self.is_undoing = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet("background-color: #222222; border-bottom: 1px solid #111;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        btn_undo = QPushButton("撤销 (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo_action)
        btn_split = QPushButton("分割 (Ctrl+B)")
        btn_split.clicked.connect(self.split_action)
        btn_delete = QPushButton("删除 (Del)")
        btn_delete.clicked.connect(self.delete_action)
        
        for btn in [btn_undo, btn_split, btn_delete]:
            btn.setStyleSheet("background-color: #333; color: #EEE; border: none; padding: 4px 8px; border-radius: 3px;")
            toolbar_layout.addWidget(btn)
            
        toolbar_layout.addStretch()
        
        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedSize(24, 24)
        btn_zoom_out.setStyleSheet("background-color: #333; color: #EEE; border: none; border-radius: 3px; padding: 0px; font-size: 16px; font-weight: bold;")
        btn_zoom_out.clicked.connect(self.zoom_out)
        toolbar_layout.addWidget(btn_zoom_out)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(1, 300)
        self.zoom_slider.setValue(PIXELS_PER_SECOND)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        toolbar_layout.addWidget(self.zoom_slider)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(24, 24)
        btn_zoom_in.setStyleSheet("background-color: #333; color: #EEE; border: none; border-radius: 3px; padding: 0px; font-size: 16px; font-weight: bold;")
        btn_zoom_in.clicked.connect(self.zoom_in)
        toolbar_layout.addWidget(btn_zoom_in)
        
        layout.addWidget(toolbar)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        
        # 左侧轨道头
        self.header_panel = QWidget()
        self.header_panel.setStyleSheet("background-color: #1A1A1A;")
        self.header_layout = QVBoxLayout(self.header_panel)
        self.header_layout.setContentsMargins(0, RULER_HEIGHT, 0, 0) # 为顶部 Ruler 留空
        self.header_layout.setSpacing(TRACK_SPACING)
        self.header_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        header_scroll = QScrollArea()
        header_scroll.setWidgetResizable(True)
        header_scroll.setWidget(self.header_panel)
        header_scroll.setFixedWidth(HEADER_WIDTH)
        header_scroll.setStyleSheet("border: none; border-right: 1px solid #000;")
        header_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.header_scroll = header_scroll
        
        self.splitter.addWidget(header_scroll)
        
        # 右侧时间轴
        self.scene = TimelineScene(self.timeline_model, parent=self)
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("border: none; background-color: #181818;")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.view.verticalScrollBar().valueChanged.connect(self.header_scroll.verticalScrollBar().setValue)
        
        self.splitter.addWidget(self.view)
        layout.addWidget(self.splitter)
        
        self.view.mousePressEvent = self.on_view_mouse_press
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # 快捷键绑定
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo_action)
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(self.split_action)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.delete_action)
        QShortcut(QKeySequence("Backspace"), self).activated.connect(self.delete_action)
        
    def on_selection_changed(self):
        items = self.scene.selectedItems()
        for item in items:
            if isinstance(item, ClipGraphicsItem):
                self.clip_selected.emit(item.clip)
                return
        self.clip_selected.emit(None)

    def save_state(self):
        if self.is_undoing:
            return
        state = self.timeline_model.to_dict()
        self.undo_stack.append(state)
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)

    def set_model(self, model):
        self.timeline_model = model
        self.scene.timeline = self.timeline_model
        self.rebuild_from_model()
        
    def fit_to_screen(self, duration_ms=None):
        if duration_ms is None:
            duration_ms = self.timeline_model.get_duration()
        if duration_ms <= 0:
            return
            
        view_width = self.view.viewport().width() - 50
        if view_width <= 0:
            return
            
        needed_zoom = int(view_width / (duration_ms / 1000.0))
        # The slider range is [1, 300]
        needed_zoom = max(1, min(300, needed_zoom))
        self.zoom_slider.setValue(needed_zoom)
        
    def undo_action(self):
        if not self.undo_stack:
            return
        self.is_undoing = True
        state = self.undo_stack.pop()
        new_model = Timeline.from_dict(state)
        self.set_model(new_model)
        self.is_undoing = False

    def delete_action(self):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
            
        self.save_state()
        for item in selected_items:
            if isinstance(item, ClipGraphicsItem):
                # 找到并删除 Clip
                track = self.timeline_model.tracks[item.track_idx]
                track.remove_clip(item.clip.id)
                
        self.rebuild_from_model()

    def split_action(self):
        selected_items = self.scene.selectedItems()
        if len(selected_items) != 1:
            QMessageBox.information(self, "提示", "请选中一个片段进行分割！")
            return
            
        item = selected_items[0]
        if not isinstance(item, ClipGraphicsItem):
            return
            
        playhead_ms = int(self.scene.playhead.pos().x() * MS_PER_PIXEL)
        clip = item.clip
        
        if playhead_ms <= clip.start_time or playhead_ms >= clip.start_time + clip.duration:
            QMessageBox.information(self, "提示", "播放头不在选中的片段内部，无法分割！")
            return
            
        self.save_state()
        track = self.timeline_model.tracks[item.track_idx]
        
        # 计算新片段的属性
        new_start = playhead_ms
        new_duration = (clip.start_time + clip.duration) - playhead_ms
        
        # 裁剪老片段
        clip.duration = playhead_ms - clip.start_time
        
        # 创建新片段
        import uuid
        import copy
        new_clip = Clip(
            name=clip.name,
            source_path=clip.source_path,
            start_time=new_start,
            duration=new_duration,
            clip_type=clip.clip_type,
            **clip.meta
        )
        # 强制更新ID防止冲突
        new_clip.id = str(uuid.uuid4())
        
        track.add_clip(new_clip)
        self.rebuild_from_model()
        
    def on_zoom_changed(self, value):
        global PIXELS_PER_SECOND, MS_PER_PIXEL
        PIXELS_PER_SECOND = value
        MS_PER_PIXEL = 1000 / PIXELS_PER_SECOND
        self.scene.rebuild_ui()
        
    def zoom_in(self):
        val = self.zoom_slider.value()
        self.zoom_slider.setValue(min(self.zoom_slider.maximum(), val + 1))

    def zoom_out(self):
        val = self.zoom_slider.value()
        self.zoom_slider.setValue(max(self.zoom_slider.minimum(), val - 1))
        
    def rebuild_from_model(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
                
        for track in self.timeline_model.tracks:
            header = QWidget()
            header.setFixedHeight(TRACK_HEIGHT)
            h_layout = QHBoxLayout(header)
            h_layout.setContentsMargins(10, 0, 5, 0)
            
            # 使用简单的色块代表图标
            icon = QLabel()
            icon.setFixedSize(12, 12)
            color = TRACK_COLORS.get(track.track_type, QColor("#555")).name()
            icon.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
            h_layout.addWidget(icon)
            
            lbl = QLabel(track.name)
            lbl.setStyleSheet("color: #AAAAAA; font-size: 12px;")
            h_layout.addWidget(lbl, stretch=1)
            
            self.header_layout.addWidget(header)
            
        self.scene.rebuild_ui()
        
    def on_view_mouse_press(self, event):
        QGraphicsView.mousePressEvent(self.view, event)
        
        scene_pos = self.view.mapToScene(event.pos())
        
        # 如果点击的不是视频片段，主动清空选择
        item = self.scene.itemAt(scene_pos, self.view.transform())
        if not isinstance(item, ClipGraphicsItem):
            self.scene.clearSelection()
            
        x = scene_pos.x()
        if x >= 0:
            ms = int(x * MS_PER_PIXEL)
            self.set_position(ms)
            self.position_changed.emit(ms)
        
    def set_position(self, ms: int):
        self._is_syncing = True
        self.scene.set_playhead_position(ms)
        playhead_x = self.scene.playhead.pos().x()
        self.view.ensureVisible(playhead_x, 0, 1, 1, 50, 0)
        self._is_syncing = False
