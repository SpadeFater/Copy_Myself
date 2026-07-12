from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFontMetrics, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from copy_myself.agent.graph import build_default_registry, stream_agent
from copy_myself.config import (
    McpServiceSettings,
    ModelSettings,
    list_mcp_service_settings,
    list_model_settings,
    load_settings,
    save_mcp_service_settings,
    save_model_settings,
    switch_active_model,
)
from copy_myself.gui.view_model import ChatMessage, RunSummary, WorkbenchViewModel


BRAND_LOGO_PATH = Path(__file__).with_name("assets") / "brand_c.png"


class BrandLogo(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("BrandLogo")
        self.setFixedSize(64, 64)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QLabel()
        self.image_label.setObjectName("BrandLogoImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(False)
        self._load_logo()
        layout.addWidget(self.image_label)

    def _load_logo(self) -> None:
        pixmap = QPixmap(str(BRAND_LOGO_PATH))
        if pixmap.isNull():
            self.image_label.setText("CM")
            return
        scaled = pixmap.scaled(
            QSize(64, 64),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)


class AgentWorkerSignals(QObject):
    chunk = pyqtSignal(str)
    finished = pyqtSignal(str, object)
    failed = pyqtSignal(str, str)


class AgentWorker(QRunnable):
    def __init__(self, message: str, view_model: WorkbenchViewModel) -> None:
        super().__init__()
        self.message = message
        self.view_model = view_model
        self.signals = AgentWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            final_state = None
            for event in stream_agent(self.message, memory=self.view_model.memory):
                if event.kind == "chunk":
                    self.signals.chunk.emit(event.content)
                elif event.kind == "done":
                    final_state = event.state
            if final_state is None:
                raise RuntimeError("Agent stream ended without a final state.")
        except Exception as exc:
            self.signals.failed.emit(self.message, str(exc))
            return
        self.signals.finished.emit(self.message, final_state)


class MainWindow(QMainWindow):
    def __init__(self, view_model: WorkbenchViewModel | None = None) -> None:
        super().__init__()
        self.view_model = view_model or WorkbenchViewModel()
        self.tool_registry = build_default_registry()
        self.setWindowTitle("Copy_Myself")
        self.resize(1240, 780)

        self.workbench_button = QPushButton("工作台")
        self.complete_memory_button = QPushButton("记忆")
        self.settings_button = QPushButton("设置")
        self.new_session_button = QPushButton("新会话")
        self.chat_list = QListWidget()
        self.input_box = QLineEdit()
        self.send_button = QPushButton("发送")
        self.intent_value = QLabel("待命")
        self.steps_list = QListWidget()
        self.plan_list = QListWidget()
        self.tools_list = QListWidget()
        self.tool_result = QTextEdit()
        self.memory_context = QListWidget()
        self.complete_memory = QListWidget()
        self.model_switch_combo = QComboBox()
        self.model_input = QLineEdit()
        self.base_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.save_settings_button = QPushButton("保存模型配置")
        self.settings_status = QLabel("")
        self.mcp_name_input = QLineEdit()
        self.mcp_endpoint_input = QLineEdit()
        self.import_mcp_button = QPushButton("导入 MCP")
        self.mcp_status = QLabel("")
        self.mcp_services_list = QListWidget()
        self.thread_pool = QThreadPool.globalInstance()

        self._build_ui()
        self._connect_events()
        self._load_model_settings()
        self._refresh_mcp_services()
        self._refresh_messages()
        self._refresh_inspector(None)
        self._show_workbench()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
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
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(14)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        brand_row.addWidget(BrandLogo())
        brand = QLabel("Copy_Myself")
        brand.setObjectName("Brand")
        brand_row.addWidget(brand, stretch=1)
        layout.addLayout(brand_row)

        layout.addSpacing(12)
        layout.addWidget(self.workbench_button)
        layout.addWidget(self.complete_memory_button)
        layout.addWidget(self.settings_button)
        layout.addStretch()
        return sidebar

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("CenterPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        self.workbench_panel = self._build_workbench_panel()
        self.settings_panel = self._build_settings_scroll_area()
        layout.addWidget(self.workbench_panel)
        layout.addWidget(self.settings_panel)
        return panel

    def _build_settings_scroll_area(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setObjectName("SettingsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumSize(0, 0)
        scroll_area.setWidget(self._build_settings_panel())
        return scroll_area

    def _build_workbench_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("Copy_Myself 工作台")
        title.setObjectName("Title")
        layout.addWidget(title)

        subtitle = QLabel("对话在中心，执行阶段、计划和工具在右侧，记忆只通过左侧按钮打开。")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(subtitle)

        self.chat_list.setObjectName("ChatList")
        self.chat_list.setWordWrap(True)
        self.chat_list.setUniformItemSizes(False)
        self.chat_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_list, stretch=1)

        composer = QHBoxLayout()
        composer.setSpacing(10)
        self.input_box.setPlaceholderText("向 Copy_Myself 发送指令...")
        composer.addWidget(self.input_box, stretch=1)
        composer.addWidget(self.send_button)
        layout.addLayout(composer)
        return panel

    def _build_settings_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("SettingsPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        title = QLabel("设置")
        title.setObjectName("Title")
        layout.addWidget(title)

        subtitle = QLabel("配置模型名称、Base URL 和 API Key；保存后下一次发送会使用当前配置。")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(subtitle)

        form = QFrame()
        form.setObjectName("SettingsCard")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(18, 18, 18, 18)
        form_layout.setSpacing(12)

        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        self.model_input.setPlaceholderText("例如 deepseek-v4-pro / gpt-4.1-mini")
        self.base_url_input.setPlaceholderText("https://.../v1")

        form_layout.addWidget(self._field("切换模型", self.model_switch_combo))
        form_layout.addWidget(self._field("模型名称", self.model_input))
        form_layout.addWidget(self._field("Base URL", self.base_url_input))
        form_layout.addWidget(self._field("API Key", self.api_key_input))
        form_layout.addWidget(self.save_settings_button)
        self.settings_status.setObjectName("SettingsStatus")
        form_layout.addWidget(self.settings_status)
        layout.addWidget(form)

        mcp_form = QFrame()
        mcp_form.setObjectName("SettingsCard")
        mcp_layout = QVBoxLayout(mcp_form)
        mcp_layout.setContentsMargins(18, 18, 18, 18)
        mcp_layout.setSpacing(12)

        mcp_title = QLabel("导入外部 MCP 服务")
        mcp_title.setObjectName("PanelTitle")
        mcp_layout.addWidget(mcp_title)
        self.mcp_name_input.setPlaceholderText("例如 filesystem")
        self.mcp_endpoint_input.setPlaceholderText("启动命令或 URL")
        mcp_layout.addWidget(self._field("服务名称", self.mcp_name_input))
        mcp_layout.addWidget(self._field("启动命令 / URL", self.mcp_endpoint_input))
        mcp_layout.addWidget(self.import_mcp_button)
        self.mcp_status.setObjectName("SettingsStatus")
        mcp_layout.addWidget(self.mcp_status)
        self.mcp_services_list.setObjectName("McpServicesList")
        self.mcp_services_list.setFixedHeight(96)
        mcp_layout.addWidget(self.mcp_services_list)
        layout.addWidget(mcp_form)
        layout.addStretch()
        return panel

    def _field(self, label_text: str, widget: QWidget) -> QWidget:
        field = QWidget()
        layout = QVBoxLayout(field)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)
        return field

    def _build_inspector(self) -> QWidget:
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(340)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(12)

        layout.addWidget(self._section_label("执行阶段"))
        self.steps_list.setObjectName("StepsList")
        layout.addWidget(self.steps_list, stretch=1)

        layout.addWidget(self._section_label("计划列表"))
        self.plan_list.setObjectName("PlanList")
        layout.addWidget(self.plan_list, stretch=1)

        layout.addWidget(self._section_label("可调用工具"))
        self.tools_list.setObjectName("ToolsList")
        layout.addWidget(self.tools_list, stretch=1)

        layout.addWidget(self._section_label("当前意图"))
        self.intent_value.setObjectName("IntentValue")
        layout.addWidget(self.intent_value)
        return inspector

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _connect_events(self) -> None:
        self.send_button.clicked.connect(self._send_message)
        self.input_box.returnPressed.connect(self._send_message)
        self.new_session_button.clicked.connect(self._start_new_conversation)
        self.workbench_button.clicked.connect(self._show_workbench)
        self.complete_memory_button.clicked.connect(self._show_complete_memory_dialog)
        self.settings_button.clicked.connect(self._show_settings)
        self.model_switch_combo.currentTextChanged.connect(self._switch_model_profile)
        self.save_settings_button.clicked.connect(self._save_model_settings)
        self.import_mcp_button.clicked.connect(self._save_mcp_service)

    def _show_workbench(self) -> None:
        current_size = self.size()
        self.workbench_panel.show()
        self.settings_panel.hide()
        self.workbench_button.setProperty("active", True)
        self.settings_button.setProperty("active", False)
        self._refresh_button_styles()
        if self.isVisible():
            self.resize(current_size)

    def _show_settings(self) -> None:
        current_size = self.size()
        self.workbench_panel.hide()
        self.settings_panel.show()
        self.workbench_button.setProperty("active", False)
        self.settings_button.setProperty("active", True)
        self._refresh_button_styles()
        if self.isVisible():
            self.resize(current_size)

    def _refresh_button_styles(self) -> None:
        for button in (self.workbench_button, self.complete_memory_button, self.settings_button):
            button.style().unpolish(button)
            button.style().polish(button)

    def _load_model_settings(self) -> None:
        settings = load_settings()
        self._refresh_model_switch(settings.model_name)
        self.model_input.setText(settings.model_name)
        self.base_url_input.setText(settings.base_url)
        self.api_key_input.setText(settings.api_key)

    def _refresh_model_switch(self, active_model: str) -> None:
        self.model_switch_combo.blockSignals(True)
        self.model_switch_combo.clear()
        for profile in list_model_settings():
            self.model_switch_combo.addItem(profile.model_name)
        if active_model and self.model_switch_combo.findText(active_model) < 0:
            self.model_switch_combo.addItem(active_model)
        if active_model:
            self.model_switch_combo.setCurrentText(active_model)
        self.model_switch_combo.blockSignals(False)

    def _switch_model_profile(self, model_name: str) -> None:
        if not model_name:
            return
        try:
            settings = switch_active_model(model_name)
        except ValueError:
            return
        self.model_input.setText(settings.model_name)
        self.base_url_input.setText(settings.base_url)
        self.api_key_input.setText(settings.api_key)
        self.settings_status.setText(f"已切换到模型：{settings.model_name}")

    def _save_model_settings(self) -> None:
        settings = ModelSettings(
            model_name=self.model_input.text().strip(),
            api_key=self.api_key_input.text().strip(),
            base_url=self.base_url_input.text().strip(),
        )
        save_model_settings(settings)
        self._refresh_model_switch(settings.model_name)
        self.settings_status.setText("已保存，下一次发送会使用该模型配置。")

    def _save_mcp_service(self) -> None:
        settings = McpServiceSettings(
            name=self.mcp_name_input.text().strip(),
            endpoint=self.mcp_endpoint_input.text().strip(),
        )
        try:
            save_mcp_service_settings(settings)
        except ValueError as exc:
            self.mcp_status.setText(str(exc))
            return
        self.mcp_status.setText(f"已导入 MCP：{settings.name}")
        self.mcp_name_input.clear()
        self.mcp_endpoint_input.clear()
        self._refresh_mcp_services()
        self._refresh_tools()

    def _send_message(self) -> None:
        clean_message = self.view_model.begin_message(self.input_box.text())
        if clean_message is None:
            return
        self.input_box.clear()
        self._refresh_messages()
        self._set_composer_enabled(False)

        worker = AgentWorker(clean_message, self.view_model)
        worker.signals.chunk.connect(self._append_response_chunk)
        worker.signals.finished.connect(self._finish_message)
        worker.signals.failed.connect(self._fail_message)
        self.thread_pool.start(worker)

    def _set_composer_enabled(self, enabled: bool) -> None:
        self.input_box.setEnabled(enabled)
        self.send_button.setEnabled(enabled)

    def _append_response_chunk(self, chunk: str) -> None:
        self.view_model.append_response_chunk(chunk)
        self._refresh_messages()

    def _finish_message(self, clean_message: str, state: object) -> None:
        summary = self.view_model.complete_message(clean_message, state)
        self._refresh_messages()
        self._refresh_inspector(summary)
        self._set_composer_enabled(True)
        self.input_box.setFocus()

    def _fail_message(self, clean_message: str, error: str) -> None:
        summary = self.view_model.complete_message(
            clean_message,
            {
                "response": f"发送失败：{error}",
                "intent": "chat",
                "tool_result": None,
                "memory_context": [],
            },
        )
        self._refresh_messages()
        self._refresh_inspector(summary)
        self._set_composer_enabled(True)
        self.input_box.setFocus()

    def _start_new_conversation(self) -> None:
        self.view_model.start_new_conversation()
        self._refresh_messages()
        self._refresh_inspector(None)
        self.input_box.clear()
        self._set_composer_enabled(True)
        self.input_box.setFocus()

    def _refresh_messages(self) -> None:
        self.chat_list.clear()
        for message in self.view_model.messages:
            self.chat_list.addItem(self._format_message_item(message))
        self.chat_list.scrollToBottom()

    def _format_message_item(self, message: ChatMessage) -> QListWidgetItem:
        speaker = "你" if message.role == "user" else "Copy_Myself"
        text = f"{speaker}: {message.content}"
        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
        item.setSizeHint(QSize(0, self._message_item_height(text)))
        return item

    def _message_item_height(self, text: str) -> int:
        available_width = max(self.chat_list.viewport().width() - 28, 420)
        metrics = QFontMetrics(self.chat_list.font())
        rect = metrics.boundingRect(
            0,
            0,
            available_width,
            10000,
            int(Qt.TextFlag.TextWordWrap),
            text,
        )
        return max(44, rect.height() + 24)

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

        self.plan_list.clear()
        for item in self.view_model.plan_items():
            self.plan_list.addItem(item)

        self.intent_value.setText(summary.intent if summary else "待命")
        self._refresh_tools()

    def _refresh_tools(self) -> None:
        self.tools_list.clear()
        for item in self.tool_registry.catalog():
            self.tools_list.addItem(f"内置 · {item.name} - {item.description}")
        services = list_mcp_service_settings()
        if services:
            for service in services:
                self.tools_list.addItem(f"MCP · {service.name} - {service.endpoint}")
        else:
            self.tools_list.addItem("MCP · 外部服务可接入，当前未连接")

    def _refresh_mcp_services(self) -> None:
        self.mcp_services_list.clear()
        services = list_mcp_service_settings()
        if services:
            for service in services:
                self.mcp_services_list.addItem(f"{service.name} · {service.endpoint}")
        else:
            self.mcp_services_list.addItem("暂无已导入 MCP 服务。")

    def _show_complete_memory_dialog(self) -> None:
        dialog = self._build_complete_memory_dialog()
        dialog.exec()

    def _build_complete_memory_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("完整记忆")
        dialog.resize(620, 520)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("完整记忆")
        title.setObjectName("Title")
        layout.addWidget(title)

        memory_list = QListWidget()
        memory_list.setObjectName("CompleteMemoryList")
        items = self.view_model.complete_memory_items()
        if items:
            memory_list.addItems(items)
        else:
            memory_list.addItem("暂无完整记忆。")
        dialog.memory_list = memory_list
        layout.addWidget(memory_list, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.setStyleSheet(STYLESHEET)
        return dialog

    def closeEvent(self, event) -> None:
        self.view_model.flush_memory()
        super().closeEvent(event)


STYLESHEET = """
QMainWindow, #Root {
    background: #020817;
}
#Sidebar, #Inspector {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
        stop: 0 #061b3a, stop: 0.52 #031226, stop: 1 #020817);
    border: 1px solid #164e8a;
    color: #e8f7ff;
}
#CenterPanel {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #020817, stop: 0.28 #061b3a, stop: 0.68 #082a5a, stop: 1 #020817);
}
#Brand {
    color: #f8fdff;
    font-size: 17px;
    font-weight: 900;
}
#BrandLogo {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #020817, stop: 0.55 #0b5cff, stop: 1 #35d7ff);
    border: 1px solid #8bdcff;
    border-radius: 8px;
}
#BrandLogoImage {
    border-radius: 7px;
}
#SectionTitle, #PanelTitle, #FieldLabel {
    color: #35d7ff;
    font-size: 14px;
    font-weight: 800;
}
#Title {
    color: #f8fdff;
    font-size: 29px;
    font-weight: 900;
}
#Subtitle, #SettingsStatus {
    color: #9fc9e8;
    font-size: 14px;
}
#SettingsCard {
    background: rgba(8, 28, 61, 0.82);
    border: 1px solid #1d72c9;
    border-radius: 8px;
}
QListWidget, QTextEdit, QLineEdit, QComboBox {
    background: rgba(3, 18, 38, 0.88);
    border: 1px solid #1a5f9f;
    border-radius: 6px;
    color: #e8f7ff;
    padding: 8px;
    selection-background-color: #0b5cff;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #35d7ff;
}
#ChatList {
    border: 1px solid #2387d6;
}
QPushButton {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #061b3a, stop: 1 #082a5a);
    border: 1px solid #1a5f9f;
    border-radius: 6px;
    color: #e8f7ff;
    font-weight: 800;
    padding: 10px 12px;
    text-align: left;
}
QPushButton:hover {
    background: #0a3d7a;
    border: 1px solid #35d7ff;
}
QPushButton[active="true"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #0b5cff, stop: 1 #35d7ff);
    border: 1px solid #8bdcff;
    color: #ffffff;
}
QPushButton:disabled {
    background: #0f2338;
    border: 1px solid #294764;
    color: #7896b4;
}
#IntentValue {
    color: #77e8ff;
    font-size: 18px;
    font-weight: 900;
}
"""
