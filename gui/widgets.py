from __future__ import annotations

from math import ceil, sin
from typing import Protocol

from PyQt6.QtCore import QTimer, QSize, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


MESSAGE_BODY_MAX_HEIGHT = 420


class AnimatedGradientFrame(QFrame):
    """Subtle animated wash used behind the workbench without affecting child widgets."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def _advance(self) -> None:
        self._phase = (self._phase + 0.014) % (2 * 3.141592653589793)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        drift = (sin(self._phase) + 1.0) / 2.0
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#EAF5F2"))
        gradient.setColorAt(0.44 + drift * 0.08, QColor("#F8FBFA"))
        gradient.setColorAt(1.0, QColor("#F9F4EC"))
        painter.fillRect(self.rect(), gradient)
        painter.end()


class MessageLike(Protocol):
    role: str
    content: str


class ChatMessageWidget(QFrame):
    def __init__(self, message: MessageLike, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.role = message.role
        self.setObjectName("UserMessage" if self.role == "user" else "AssistantMessage")
        self.setAccessibleName("我的消息" if self.role == "user" else "Copy_Myself 消息")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.message_body = QPlainTextEdit()
        self.message_body.setObjectName("MessageText")
        self.message_body.setPlainText(message.content)
        self.message_body.setReadOnly(True)
        self.message_body.setFrameShape(QFrame.Shape.NoFrame)
        self.message_body.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.message_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.message_body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.message_body.document().setDocumentMargin(0)
        self.message_body.setStyleSheet("QPlainTextEdit { background: transparent; border: none; }")
        self.message_body.viewport().setStyleSheet("background: transparent;")
        self.message_body.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self.message_body)

    def fit_to_width(self, width: int) -> None:
        self.setFixedWidth(width)
        body_width = max(1, width - 28)
        self.message_body.setFixedWidth(body_width)
        self.message_body.document().setTextWidth(body_width)
        text_height = self._text_height_for_width(body_width)
        body_height = min(
            MESSAGE_BODY_MAX_HEIGHT,
            max(self.message_body.fontMetrics().lineSpacing() + 8, text_height + 8),
        )
        self.message_body.setFixedHeight(body_height)
        self.setFixedHeight(max(44, body_height + 20))

    def _text_height_for_width(self, width: int) -> int:
        metrics = self.message_body.fontMetrics()
        available_width = max(1, width - 8)
        visual_lines = 0
        for paragraph in self.message_body.toPlainText().split("\n"):
            visual_lines += 1 if not paragraph else max(
                1, ceil(metrics.horizontalAdvance(paragraph) / available_width)
            )
        return max(metrics.lineSpacing(), visual_lines * metrics.lineSpacing())

    def scroll_body_to_bottom(self) -> None:
        scroll_bar = self.message_body.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.maximum())


class ChatListWidget(QListWidget):
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.resize_message_widgets()

    def resize_message_widgets(self) -> None:
        width = max(1, self.viewport().width() - 8)
        for index in range(self.count()):
            item = self.item(index)
            widget = self.itemWidget(item)
            if not isinstance(widget, ChatMessageWidget):
                continue
            widget.fit_to_width(width)
            item.setSizeHint(QSize(width, widget.height() + 8))

    def scroll_last_message_body_to_bottom(self) -> None:
        if self.count() == 0:
            return
        widget = self.itemWidget(self.item(self.count() - 1))
        if isinstance(widget, ChatMessageWidget):
            widget.scroll_body_to_bottom()


class ExecutionStepWidget(QFrame):
    def __init__(
        self,
        position: int,
        step_name: str,
        *,
        active: bool = False,
        meta_text: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.position = position
        self.step_name = step_name
        self.setObjectName("ExecutionStep")
        self.setProperty("active", active)

        badge = QLabel(str(position))
        badge.setObjectName("StepBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(22, 22)

        name = QLabel(step_name)
        name.setObjectName("StepName")
        meta = QLabel(meta_text or ("当前节点" if active else "执行节点"))
        meta.setObjectName("StepMeta")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        text_layout.addWidget(name)
        text_layout.addWidget(meta)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 5, 4, 5)
        layout.setSpacing(9)
        layout.addWidget(badge)
        layout.addLayout(text_layout)
        layout.addStretch()
