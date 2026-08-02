from __future__ import annotations

from math import ceil

from PyQt6.QtCore import QTimer, QSize, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from copy_myself.config import (
    import_mcp_service_setting,
    import_model_provider_setting,
    list_mcp_service_settings,
    list_model_provider_settings,
    load_settings,
)
from copy_myself.gui.view_model import ChatMessage, RunSummary, WorkbenchViewModel


THINKING_MESSAGE = "管家正在思考问题..."
MESSAGE_BODY_MAX_HEIGHT = 420
PENDING_RESPONSE_DELAY_MS = 60


class ChatMessageWidget(QFrame):
    def __init__(self, message: ChatMessage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("UserMessage" if message.role == "user" else "AssistantMessage")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.message_body = QPlainTextEdit()
        self.message_body.setObjectName("MessageText")
        self.message_body.setPlainText(message.content)
        self.message_body.setReadOnly(True)
        self.message_body.setFrameShape(QFrame.Shape.NoFrame)
        self.message_body.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.message_body.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_body.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.message_body.document().setDocumentMargin(0)
        self.message_body.setStyleSheet(
            "QPlainTextEdit { background: transparent; border: none; color: #eff9ff; }"
        )
        self.message_body.viewport().setStyleSheet("background: transparent;")
        self.message_body.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(self.message_body)

    def fit_to_width(self, width: int) -> None:
        self.setFixedWidth(width)
        inner_width = max(1, width - 28)
        body_width = max(1, inner_width)
        self.message_body.setFixedWidth(body_width)
        self.message_body.document().setTextWidth(body_width)
        text_height = self._text_height_for_width(body_width)
        body_height = min(
            MESSAGE_BODY_MAX_HEIGHT,
            max(self.message_body.fontMetrics().lineSpacing() + 8, text_height + 8),
        )
        height = max(44, body_height + 20)
        self.message_body.setFixedHeight(body_height)
        self.setFixedHeight(height)

    def _text_height_for_width(self, width: int) -> int:
        metrics = self.message_body.fontMetrics()
        line_spacing = metrics.lineSpacing()
        available_width = max(1, width - 8)
        visual_lines = 0
        for paragraph in self.message_body.toPlainText().split("\n"):
            if not paragraph:
                visual_lines += 1
                continue
            visual_lines += max(1, ceil(metrics.horizontalAdvance(paragraph) / available_width))
        return max(line_spacing, visual_lines * line_spacing)

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
            if widget is None:
                continue
            widget.fit_to_width(width)
            item.setSizeHint(QSize(width, widget.height() + 8))

    def scroll_last_message_body_to_bottom(self) -> None:
        if self.count() == 0:
            return
        widget = self.itemWidget(self.item(self.count() - 1))
        if isinstance(widget, ChatMessageWidget):
            widget.scroll_body_to_bottom()


class MemoryDialog(QDialog):
    def __init__(self, view_model: WorkbenchViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._view_model = view_model
        self.context_list = QListWidget()
        self.message_list = QListWidget()

        self.setWindowTitle("完整记忆")
        self.setModal(False)
        self.resize(760, 520)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("完整记忆")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("点击查看，不占用主工作台空间")
        subtitle.setObjectName("DialogSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        context_label = QLabel("已保存记忆")
        context_label.setObjectName("SectionTitle")
        root.addWidget(context_label)
        root.addWidget(self.context_list, stretch=1)

        message_label = QLabel("近期对话")
        message_label.setObjectName("SectionTitle")
        root.addWidget(message_label)
        root.addWidget(self.message_list, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def refresh(self) -> None:
        self.context_list.clear()
        if hasattr(self._view_model.memory, "list_nodes"):
            nodes = self._view_model.memory.list_nodes(limit=100)
            context = [
                f"user: {node.user_input}\nassistant: {node.assistant_response}\nsummary: {node.summary}"
                for node in nodes
            ]
        else:
            context = self._view_model.memory.search("", limit=100)
        if context:
            self.context_list.addItems(context)
        else:
            self.context_list.addItem("暂无记忆内容")

        self.message_list.clear()
        for message in self._view_model.messages[-10:]:
            speaker = "我" if message.role == "user" else "Copy_Myself"
            self.message_list.addItem(f"{speaker}: {message.content}")


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_model_value = QLabel()
        self.current_model_source = QLabel()
        self.model_name_input = QLineEdit()
        self.model_url_input = QLineEdit()
        self.model_id_input = QLineEdit()
        self.model_api_key_input = QLineEdit()
        self.model_provider_input = QLineEdit("openai-compatible")
        self.import_model_button = QPushButton("导入模型")
        self.model_providers = QListWidget()
        self.mcp_name_input = QLineEdit()
        self.mcp_url_input = QLineEdit()
        self.mcp_transport_input = QComboBox()
        self.mcp_command_input = QLineEdit()
        self.mcp_args_input = QLineEdit()
        self.import_mcp_button = QPushButton("导入外部 MCP")
        self.mcp_services = QListWidget()
        self.tabs = QTabWidget()

        self.setWindowTitle("设置")
        self.setModal(False)
        self.resize(720, 520)

        self._build_ui()
        self.refresh()
        self.import_model_button.clicked.connect(self._import_model)
        self.import_mcp_button.clicked.connect(self._import_mcp_service)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("设置")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("模型、外部 MCP 与运行入口统一收纳")
        subtitle.setObjectName("DialogSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        model_status = QFrame()
        model_status.setObjectName("SettingsStatus")
        model_status_layout = QHBoxLayout(model_status)
        model_status_layout.setContentsMargins(12, 8, 12, 8)
        model_status_layout.setSpacing(10)
        status_text = QLabel("当前模型")
        status_text.setObjectName("SectionTitle")
        status_column = QVBoxLayout()
        status_column.setContentsMargins(0, 0, 0, 0)
        status_column.setSpacing(2)
        status_column.addWidget(self.current_model_value)
        status_column.addWidget(self.current_model_source)
        model_status_layout.addWidget(status_text)
        model_status_layout.addLayout(status_column)
        model_status_layout.addStretch()
        root.addWidget(model_status)

        model_tab = QWidget()
        model_layout = QVBoxLayout(model_tab)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(6)

        model_form = QFrame()
        model_form_layout = QFormLayout(model_form)
        model_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        model_form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.model_name_input.setPlaceholderText("显示名称，例如 Local Qwen")
        self.model_url_input.setPlaceholderText("URL，例如 http://127.0.0.1:11434/v1")
        self.model_id_input.setPlaceholderText("模型名字，例如 qwen2.5:7b 或 gpt-4.1-mini")
        self.model_api_key_input.setPlaceholderText("API Key，可留空")
        self.model_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.model_provider_input.setPlaceholderText("提供方类型，例如 openai-compatible")
        model_form_layout.addRow("名称", self.model_name_input)
        model_form_layout.addRow("URL", self.model_url_input)
        model_form_layout.addRow("模型", self.model_id_input)
        model_form_layout.addRow("API Key", self.model_api_key_input)
        model_form_layout.addRow("提供方", self.model_provider_input)
        model_layout.addWidget(model_form)
        model_layout.addWidget(self.import_model_button)
        self.model_providers.setMaximumHeight(88)
        model_layout.addWidget(self.model_providers)

        mcp_tab = QWidget()
        mcp_layout = QVBoxLayout(mcp_tab)
        mcp_layout.setContentsMargins(0, 0, 0, 0)
        mcp_layout.setSpacing(6)

        mcp_form = QFrame()
        mcp_form_layout = QFormLayout(mcp_form)
        mcp_form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        mcp_form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.mcp_name_input.setPlaceholderText("服务名称，例如 Filesystem MCP")
        self.mcp_url_input.setPlaceholderText("URL 或 endpoint，例如 http://127.0.0.1:3000/mcp")
        self.mcp_transport_input.addItems(["stdio", "http", "sse"])
        self.mcp_command_input.setPlaceholderText("命令，可留空，例如 npx")
        self.mcp_args_input.setPlaceholderText("参数，可留空，用空格分隔")
        mcp_form_layout.addRow("名称", self.mcp_name_input)
        mcp_form_layout.addRow("URL", self.mcp_url_input)
        mcp_form_layout.addRow("传输", self.mcp_transport_input)
        mcp_form_layout.addRow("命令", self.mcp_command_input)
        mcp_form_layout.addRow("参数", self.mcp_args_input)
        mcp_layout.addWidget(mcp_form)
        mcp_layout.addWidget(self.import_mcp_button)
        self.mcp_services.setMaximumHeight(88)
        mcp_layout.addWidget(self.mcp_services)

        self.tabs.addTab(model_tab, "模型")
        self.tabs.addTab(mcp_tab, "MCP")
        root.addWidget(self.tabs, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def _section_frame(self, title: str, description: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("SettingsSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("SectionTitle")
        text = QLabel(description)
        text.setObjectName("SectionHint")
        text.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(text)
        return frame

    def refresh(self) -> None:
        settings = load_settings()
        self.current_model_value.setObjectName("CurrentModelValue")
        self.current_model_source.setObjectName("ModelSourceValue")
        self.current_model_value.setText(f"当前模型: {settings.model_name}")
        self.current_model_source.setText(
            f"配置值: {settings.configured_model_name} · 来源: {settings.model.source}"
        )
        self.tabs.setCurrentIndex(min(self.tabs.currentIndex(), self.tabs.count() - 1))
        self._refresh_model_providers()
        self._refresh_mcp_services()

    def _refresh_model_providers(self) -> None:
        self.model_providers.clear()
        providers = list_model_provider_settings()
        if not providers:
            self.model_providers.addItem("暂无已导入模型")
            return
        for provider in providers:
            self.model_providers.addItem(f"{provider.name} · {provider.model_name} · {provider.base_url}")

    def _refresh_mcp_services(self) -> None:
        self.mcp_services.clear()
        services = list_mcp_service_settings()
        if not services:
            self.mcp_services.addItem("暂无已导入的 MCP 服务")
            return
        for service in services:
            self.mcp_services.addItem(f"{service.name} · {service.transport} · {service.endpoint}")

    def _import_model(self) -> None:
        name = self.model_name_input.text().strip()
        base_url = self.model_url_input.text().strip()
        model_name = self.model_id_input.text().strip()
        if not name or not base_url or not model_name:
            return
        import_model_provider_setting(
            name=name,
            base_url=base_url,
            model_name=model_name,
            api_key=self.model_api_key_input.text().strip(),
            provider=self.model_provider_input.text().strip() or "openai-compatible",
        )
        for field in (
            self.model_name_input,
            self.model_url_input,
            self.model_id_input,
            self.model_api_key_input,
        ):
            field.clear()
        self.refresh()

    def _import_mcp_service(self) -> None:
        name = self.mcp_name_input.text().strip()
        endpoint = self.mcp_url_input.text().strip()
        if not name or not endpoint:
            return
        args = tuple(part for part in self.mcp_args_input.text().split() if part)
        import_mcp_service_setting(
            endpoint,
            name=name,
            transport=self.mcp_transport_input.currentText(),
            command=self.mcp_command_input.text().strip(),
            args=args,
        )
        for field in (
            self.mcp_name_input,
            self.mcp_url_input,
            self.mcp_command_input,
            self.mcp_args_input,
        ):
            field.clear()
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self, view_model: WorkbenchViewModel | None = None) -> None:
        super().__init__()
        self.view_model = view_model or WorkbenchViewModel()
        self.setWindowTitle("Copy_Myself")
        self.resize(1260, 800)

        self.nav_buttons: dict[str, QPushButton] = {}
        self.tool_buttons: dict[str, QToolButton] = {}
        self.memory_dialog: MemoryDialog | None = None
        self.settings_dialog: SettingsDialog | None = None
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(18)
        self._stream_timer.timeout.connect(self._advance_response_stream)
        self._stream_text = ""
        self._stream_index = 0
        self._pending_message: str | None = None

        self.chat_list = ChatListWidget()
        self.input_box = QLineEdit()
        self.send_button = QPushButton("发送")
        self.status_value = QLabel("standby")
        self.execution_list = QListWidget()
        self.plan_list = QListWidget()
        self.intent_value = QLabel("standby")
        self.tool_entry_label = QLabel("可调用工具")

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
        layout.setSpacing(14)

        brand = QLabel("Copy_Myself")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        nav_section = QLabel("导航")
        nav_section.setObjectName("SidebarSection")
        layout.addWidget(nav_section)

        for text in ("工作台", "记忆", "设置"):
            button = QPushButton(text)
            button.setObjectName("SidebarButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, name=text: self._handle_nav_click(name))
            layout.addWidget(button)
            self.nav_buttons[text] = button

        self.nav_buttons["工作台"].setChecked(True)
        layout.addStretch()
        return sidebar

    def _build_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        header = QFrame()
        header.setObjectName("HeaderBand")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("工作台")
        title.setObjectName("Title")
        subtitle = QLabel("科幻蓝执行面板")
        subtitle.setObjectName("Subtitle")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(subtitle)
        header_layout.addLayout(title_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.tool_entry_label.setObjectName("PanelTitle")
        action_row.addWidget(self.tool_entry_label)

        for text in ("内置工具", "MCP 调用"):
            button = QToolButton()
            button.setText(text)
            button.setObjectName("ToolChip")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            action_row.addWidget(button)
            self.tool_buttons[text] = button

        action_row.addStretch()
        header_layout.addLayout(action_row)
        layout.addWidget(header)

        stage_band = QFrame()
        stage_band.setObjectName("StageBand")
        stage_layout = QHBoxLayout(stage_band)
        stage_layout.setContentsMargins(18, 16, 18, 16)
        stage_layout.setSpacing(12)

        stage_label = QLabel("当前阶段")
        stage_label.setObjectName("PanelTitle")
        self.status_value.setObjectName("StatusValue")
        stage_layout.addWidget(stage_label)
        stage_layout.addWidget(self.status_value)
        stage_layout.addStretch()
        layout.addWidget(stage_band)

        chat_label = QLabel("对话")
        chat_label.setObjectName("PanelTitle")
        layout.addWidget(chat_label)
        self.chat_list.setObjectName("ChatList")
        self.chat_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_list, stretch=1)

        composer = QFrame()
        composer.setObjectName("Composer")
        composer_layout = QHBoxLayout(composer)
        composer_layout.setContentsMargins(16, 16, 16, 16)
        composer_layout.setSpacing(10)
        self.input_box.setPlaceholderText("告诉 Copy_Myself 你想处理什么...")
        composer_layout.addWidget(self.input_box, stretch=1)
        composer_layout.addWidget(self.send_button)
        layout.addWidget(composer)

        return panel

    def _build_inspector(self) -> QWidget:
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(340)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(14)

        layout.addWidget(self._section_title("执行阶段"))
        self.execution_list.setObjectName("StageList")
        self.execution_list.setMinimumHeight(170)
        layout.addWidget(self.execution_list)

        layout.addWidget(self._section_title("计划列表"))
        self.plan_list.setObjectName("PlanList")
        self.plan_list.setMinimumHeight(180)
        layout.addWidget(self.plan_list)

        layout.addWidget(self._section_title("当前意图"))
        self.intent_value.setObjectName("IntentValue")
        self.intent_value.setWordWrap(True)
        layout.addWidget(self.intent_value)

        layout.addStretch()
        return inspector

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("PanelTitle")
        return label

    def _connect_events(self) -> None:
        self.send_button.clicked.connect(self._send_message)
        self.input_box.returnPressed.connect(self._send_message)
        self.tool_buttons["内置工具"].clicked.connect(self._select_builtin_tools)
        self.tool_buttons["MCP 调用"].clicked.connect(self._select_mcp_tools)

    def _handle_nav_click(self, name: str) -> None:
        for button_name, button in self.nav_buttons.items():
            button.setChecked(button_name == name)
        if name == "记忆":
            self._open_memory_dialog()
        elif name == "设置":
            self._open_settings_dialog()

    def _select_builtin_tools(self) -> None:
        self.status_value.setText("builtin tools")
        self.intent_value.setText("内置工具入口已就绪")

    def _select_mcp_tools(self) -> None:
        self.status_value.setText("mcp tools")
        self.intent_value.setText("MCP 调用入口已就绪")

    def _send_message(self) -> None:
        self._finish_response_stream()
        clean_message = self.input_box.text().strip()
        if not clean_message or self._pending_message is not None:
            return
        self.input_box.clear()
        self._pending_message = clean_message
        self.view_model.messages.append(ChatMessage(role="user", content=clean_message))
        self.view_model.messages.append(ChatMessage(role="assistant", content=THINKING_MESSAGE))
        self.status_value.setText(THINKING_MESSAGE)
        self.send_button.setEnabled(False)
        self.input_box.setEnabled(False)
        self._refresh_messages()
        self.chat_list.viewport().repaint()
        QTimer.singleShot(PENDING_RESPONSE_DELAY_MS, self._complete_pending_message)

    def _complete_pending_message(self) -> None:
        pending_message = self._pending_message
        if pending_message is None:
            return
        self._pending_message = None
        self._remove_thinking_placeholder(pending_message)
        messages_before = len(self.view_model.messages)
        try:
            summary = self.view_model.send_message(pending_message)
        finally:
            self.send_button.setEnabled(True)
            self.input_box.setEnabled(True)
        if summary is None:
            self._refresh_messages()
            return
        if len(self.view_model.messages) == messages_before:
            self.view_model.messages.append(ChatMessage(role="user", content=pending_message))
            self.view_model.messages.append(ChatMessage(role="assistant", content=summary.response))
        self._refresh_inspector(summary)
        self.status_value.setText(summary.stage_label)
        self._start_response_stream(summary.response)

    def _remove_thinking_placeholder(self, message: str) -> None:
        if len(self.view_model.messages) < 2:
            return
        user_message = self.view_model.messages[-2]
        assistant_message = self.view_model.messages[-1]
        if (
            user_message == ChatMessage(role="user", content=message)
            and assistant_message == ChatMessage(role="assistant", content=THINKING_MESSAGE)
        ):
            del self.view_model.messages[-2:]

    def _refresh_messages(self, follow_latest_body: bool = False) -> None:
        self.chat_list.clear()
        for message in self.view_model.messages:
            item = QListWidgetItem()
            widget = ChatMessageWidget(message)
            self.chat_list.addItem(item)
            self.chat_list.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())
        self.chat_list.resize_message_widgets()
        if follow_latest_body:
            self.chat_list.scroll_last_message_body_to_bottom()
        self.chat_list.scrollToBottom()

    def _start_response_stream(self, response: str) -> None:
        self._finish_response_stream()
        if not self.view_model.messages:
            return
        self._stream_text = response
        self._stream_index = 0
        self.view_model.messages[-1] = ChatMessage(role="assistant", content="")
        self._refresh_messages(follow_latest_body=True)
        if response:
            self._stream_timer.start()

    def _advance_response_stream(self) -> None:
        self._stream_index = min(self._stream_index + 2, len(self._stream_text))
        self.view_model.messages[-1] = ChatMessage(
            role="assistant",
            content=self._stream_text[: self._stream_index],
        )
        self._refresh_messages(follow_latest_body=True)
        if self._stream_index >= len(self._stream_text):
            self._finish_response_stream()

    def _finish_response_stream(self) -> None:
        if self._stream_timer.isActive():
            self._stream_timer.stop()
        if self._stream_text and self.view_model.messages:
            self.view_model.messages[-1] = ChatMessage(
                role="assistant",
                content=self._stream_text,
            )
            self._refresh_messages(follow_latest_body=True)
        self._stream_text = ""
        self._stream_index = 0

    def _refresh_inspector(self, summary: RunSummary | None) -> None:
        self.execution_list.clear()
        steps = summary.graph_steps if summary else [
            "load_memory",
            "classify_intent",
            "run_tool",
            "create_response",
        ]
        for index, step in enumerate(steps, start=1):
            self.execution_list.addItem(f"{index}. {step}")

        self.plan_list.clear()
        for item in self._build_plan_items(summary):
            self.plan_list.addItem(item)

        self.intent_value.setText(summary.display_intent if summary else "standby")

    def _build_plan_items(self, summary: RunSummary | None) -> list[str]:
        if summary:
            return [
                "1. 识别当前任务",
                "2. 选择内置工具或 MCP",
                "3. 汇总结果并生成响应",
            ]
        return [
            "1. 等待输入",
            "2. 进入执行阶段",
            "3. 点击完整记忆可查看上下文",
        ]

    def _open_memory_dialog(self) -> None:
        if self.memory_dialog is None:
            self.memory_dialog = MemoryDialog(self.view_model, self)
        self.memory_dialog.refresh()
        self.memory_dialog.show()
        self.memory_dialog.raise_()
        self.memory_dialog.activateWindow()

    def _open_settings_dialog(self) -> None:
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.refresh()
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()


STYLESHEET = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #031022, stop:0.45 #071b3a, stop:1 #04131f);
}
QWidget {
    color: #e5f2ff;
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 12px;
}
#Sidebar, #Inspector, #HeaderBand, #StageBand, #Composer, #SettingsSection, #FooterBar {
    background: rgba(7, 18, 37, 0.74);
    border: 1px solid rgba(92, 171, 255, 0.18);
    border-radius: 14px;
}
#Sidebar {
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
    border-left: 0px;
}
#Inspector {
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
    border-right: 0px;
}
#Brand {
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0px;
    color: #dff4ff;
}
#SidebarSection, #SectionTitle, #PanelTitle, #DialogTitle {
    font-size: 13px;
    font-weight: 700;
    color: #9fd7ff;
}
#Subtitle, #DialogSubtitle, #SectionHint {
    color: #7f9ec4;
}
#Title {
    font-size: 28px;
    font-weight: 800;
    color: #f5fbff;
}
#StatusValue, #IntentValue, #CurrentModelValue {
    color: #35d7ff;
    font-size: 16px;
    font-weight: 700;
}
#ModelSourceValue {
    color: #7f9ec4;
}
#ToolChip, #SidebarButton, QPushButton {
    background: rgba(16, 54, 99, 0.9);
    border: 1px solid rgba(95, 190, 255, 0.38);
    border-radius: 10px;
    color: #eff9ff;
    padding: 9px 14px;
    font-weight: 700;
}
#ToolChip:hover, #SidebarButton:hover, QPushButton:hover {
    background: rgba(24, 77, 137, 0.95);
    border-color: rgba(124, 210, 255, 0.65);
}
#SidebarButton:checked {
    background: rgba(28, 92, 161, 0.98);
    border-color: rgba(149, 231, 255, 0.85);
}
QListWidget, QLineEdit, QComboBox {
    background: rgba(3, 13, 28, 0.78);
    border: 1px solid rgba(95, 190, 255, 0.24);
    border-radius: 12px;
    color: #eff9ff;
    selection-background-color: rgba(53, 215, 255, 0.28);
    padding: 10px;
}
QListWidget::item {
    padding: 4px 0px;
}
QListWidget::item:selected {
    background: rgba(53, 215, 255, 0.16);
    color: #ffffff;
}
#ChatList {
    min-height: 320px;
}
#UserMessage, #AssistantMessage {
    border-radius: 10px;
}
#UserMessage {
    background: rgba(24, 77, 137, 0.8);
    border: 1px solid rgba(124, 210, 255, 0.35);
}
#AssistantMessage {
    background: rgba(7, 28, 54, 0.92);
    border: 1px solid rgba(95, 190, 255, 0.22);
}
#MessageText {
    color: #eff9ff;
}
"""
