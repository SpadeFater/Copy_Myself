from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from copy_myself.gui.view_model import ChatMessage, RunSummary, WorkbenchViewModel


class MainWindow(QMainWindow):
    def __init__(self, view_model: WorkbenchViewModel | None = None) -> None:
        super().__init__()
        self.view_model = view_model or WorkbenchViewModel()
        self.setWindowTitle("Copy_Myself")
        self.resize(1220, 760)

        self.nav_list = QListWidget()
        self.chat_list = QListWidget()
        self.input_box = QLineEdit()
        self.send_button = QPushButton("发送")
        self.intent_value = QLabel("standby")
        self.steps_list = QListWidget()
        self.tool_result = QTextEdit()
        self.memory_context = QListWidget()

        self._build_ui()
        self._connect_events()
        self._refresh_messages()
        self._refresh_inspector(None)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_center_panel(), stretch=1)
        root_layout.addWidget(self._build_inspector())

        self.setCentralWidget(root)
        self.setStyleSheet(STYLESHEET)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(16)

        brand = QLabel("CM\nCopy_Myself\nPersonal Butler")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        self.nav_list.addItems(["工作台", "会话", "记忆", "设置"])
        self.nav_list.setCurrentRow(0)
        layout.addWidget(self.nav_list)

        section = QLabel("项目空间")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)
        for project in ["个人管家", "项目复盘", "任务计划"]:
            button = QPushButton(project)
            button.setObjectName("ProjectButton")
            layout.addWidget(button)

        layout.addStretch()
        return sidebar

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        title = QLabel("个人管家工作台")
        title.setObjectName("Title")
        subtitle = QLabel("仪表盘概览 + Agent 执行面板")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(self._build_overview())

        chat_title = QLabel("Agent 对话")
        chat_title.setObjectName("PanelTitle")
        layout.addWidget(chat_title)
        self.chat_list.setObjectName("ChatList")
        self.chat_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_list, stretch=1)

        composer = QHBoxLayout()
        self.input_box.setPlaceholderText("告诉 Copy_Myself 你想处理什么...")
        composer.addWidget(self.input_box, stretch=1)
        composer.addWidget(self.send_button)
        layout.addLayout(composer)
        return panel

    def _build_overview(self) -> QHBoxLayout:
        overview = QHBoxLayout()
        overview.setSpacing(12)
        cards = [
            ("今日计划", "3", "先把可视化外壳和后端接口打通。"),
            ("Agent 状态", "standby", "LangGraph 已作为核心编排层。"),
            ("下一能力", "待定", "任务、提醒、笔记记忆可以作为第一批功能。"),
        ]
        for label, value, description in cards:
            card = QFrame()
            card.setObjectName("OverviewCard")
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(label))
            value_label = QLabel(value)
            value_label.setObjectName("Metric")
            card_layout.addWidget(value_label)
            card_layout.addWidget(QLabel(description))
            overview.addWidget(card)
        return overview

    def _build_inspector(self) -> QWidget:
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(320)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(14)

        layout.addWidget(QLabel("执行过程"))
        layout.addWidget(self.steps_list)

        layout.addWidget(QLabel("当前意图"))
        self.intent_value.setObjectName("IntentValue")
        layout.addWidget(self.intent_value)

        layout.addWidget(QLabel("工具结果"))
        self.tool_result.setReadOnly(True)
        self.tool_result.setFixedHeight(150)
        layout.addWidget(self.tool_result)

        layout.addWidget(QLabel("记忆上下文"))
        layout.addWidget(self.memory_context, stretch=1)
        return inspector

    def _connect_events(self) -> None:
        self.send_button.clicked.connect(self._send_message)
        self.input_box.returnPressed.connect(self._send_message)

    def _send_message(self) -> None:
        summary = self.view_model.send_message(self.input_box.text())
        if summary is None:
            return
        self.input_box.clear()
        self._refresh_messages()
        self._refresh_inspector(summary)

    def _refresh_messages(self) -> None:
        self.chat_list.clear()
        for message in self.view_model.messages:
            self.chat_list.addItem(self._format_message_item(message))
        self.chat_list.scrollToBottom()

    def _format_message_item(self, message: ChatMessage) -> QListWidgetItem:
        speaker = "你" if message.role == "user" else "Copy_Myself"
        item = QListWidgetItem(f"{speaker}: {message.content}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
        return item

    def _refresh_inspector(self, summary: RunSummary | None) -> None:
        self.steps_list.clear()
        steps = summary.graph_steps if summary else [
            "load_memory",
            "classify_intent",
            "run_tool",
            "create_response",
        ]
        for step in steps:
            self.steps_list.addItem(step)

        self.intent_value.setText(summary.intent if summary else "standby")
        tool_payload = summary.tool_result if summary and summary.tool_result else {"status": "idle"}
        self.tool_result.setPlainText(json.dumps(tool_payload, ensure_ascii=False, indent=2))

        self.memory_context.clear()
        if summary and summary.memory_context:
            self.memory_context.addItems(summary.memory_context)
        else:
            self.memory_context.addItem("暂无匹配记忆。")


STYLESHEET = """
QMainWindow {
    background: #f6f7f9;
}
#Sidebar, #Inspector {
    background: #111827;
    color: #f9fafb;
}
#Brand {
    font-size: 15px;
    font-weight: 700;
    line-height: 1.4;
}
#SectionTitle, #PanelTitle {
    font-size: 14px;
    font-weight: 700;
}
#Title {
    color: #111827;
    font-size: 28px;
    font-weight: 800;
}
#Subtitle {
    color: #667085;
    font-size: 14px;
}
#OverviewCard {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
}
#Metric {
    color: #111827;
    font-size: 24px;
    font-weight: 800;
}
QListWidget, QTextEdit, QLineEdit {
    background: #ffffff;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    color: #111827;
    padding: 8px;
}
#Sidebar QListWidget, #Inspector QListWidget, #Inspector QTextEdit {
    background: #1f2937;
    border: 1px solid #374151;
    color: #f9fafb;
}
QPushButton {
    background: #2563eb;
    border: 0;
    border-radius: 6px;
    color: #ffffff;
    font-weight: 700;
    padding: 9px 14px;
}
QPushButton:hover {
    background: #1d4ed8;
}
#ProjectButton {
    background: #1f2937;
    text-align: left;
}
#IntentValue {
    color: #93c5fd;
    font-size: 18px;
    font-weight: 800;
}
"""
