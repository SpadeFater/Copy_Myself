from __future__ import annotations

import asyncio
from urllib.parse import urlparse
from uuid import uuid4

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
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
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import (
    ModelProviderSettings,
    delete_model_provider_setting,
    import_mcp_service_setting,
    import_model_provider_setting,
    list_mcp_service_settings,
    list_model_provider_settings,
    load_settings,
    select_model_provider_model,
)
from llm.openai_compatible import fetch_available_models
from gui.view_model import ChatMessage, RunSummary, WorkbenchViewModel
from gui.execution_graph import ExecutionGraphDialog
from gui.memory_graph import MemoryGraphPanel
from gui.theme import WORKBENCH_QSS, apply_workbench_theme, fluent_icon
from gui.widgets import (
    MESSAGE_BODY_MAX_HEIGHT,
    ChatListWidget,
    ChatMessageWidget,
    ExecutionStepWidget,
)
from agent.service import ChatRunResult, ChatService


THINKING_MESSAGE = "管家正在思考问题..."
PENDING_RESPONSE_DELAY_MS = 60


class ChatWorker(QThread):
    completed = pyqtSignal(object)
    approval_required = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.message = message
        self.session_id = f"gui-{uuid4().hex}"
        self._loop: asyncio.AbstractEventLoop | None = None
        self._decision: asyncio.Future[bool] | None = None

    def run(self) -> None:
        try:
            asyncio.run(self._run_conversation())
        except Exception as exc:
            self.failed.emit(str(exc))

    async def _run_conversation(self) -> None:
        self._loop = asyncio.get_running_loop()
        service = ChatService()
        try:
            result = await service.achat(self.message, self.session_id)
            while result.status == "pending_approval" and result.pending_approval is not None:
                self._decision = self._loop.create_future()
                self.approval_required.emit(result.pending_approval)
                approved = await self._decision
                result = await service.resume(result.pending_approval.approval_id, approved, self.session_id)
            self.completed.emit(result)
        finally:
            await service.runner.close()

    def decide(self, approved: bool) -> None:
        if self._loop is not None and self._decision is not None and not self._decision.done():
            self._loop.call_soon_threadsafe(self._decision.set_result, approved)


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
        self.available_models_combo = QComboBox()
        self.probe_models_button = QPushButton("探测模型")
        self.manual_model_button = QPushButton("手动填写模型名")
        self.import_model_button = QPushButton("保存模型")
        self.delete_model_button = QPushButton("删除模型")
        self.model_providers = QListWidget()
        self.mcp_name_input = QLineEdit()
        self.mcp_url_input = QLineEdit()
        self.mcp_transport_input = QComboBox()
        self.mcp_command_input = QLineEdit()
        self.mcp_args_input = QLineEdit()
        self.import_mcp_button = QPushButton("导入外部 MCP")
        self.mcp_services = QListWidget()
        self.tabs = QTabWidget()
        self.setObjectName("SettingsDialog")
        self.tabs.setObjectName("SettingsTabs")
        self.model_providers.setObjectName("ModelProviderList")
        self.mcp_services.setObjectName("McpServiceList")
        for field in (
            self.model_name_input,
            self.model_url_input,
            self.model_id_input,
            self.model_api_key_input,
            self.model_provider_input,
            self.mcp_name_input,
            self.mcp_url_input,
            self.mcp_command_input,
            self.mcp_args_input,
        ):
            field.setObjectName("SettingsInput")
        self.mcp_transport_input.setObjectName("SettingsCombo")
        self.available_models_combo.setObjectName("SettingsCombo")
        self.probe_models_button.setObjectName("DialogSecondaryButton")
        self.manual_model_button.setObjectName("DialogSecondaryButton")
        self.import_model_button.setObjectName("DialogPrimaryButton")
        self.delete_model_button.setObjectName("DialogSecondaryButton")
        self.import_mcp_button.setObjectName("DialogPrimaryButton")

        self.setWindowTitle("设置")
        self.setModal(False)
        self.resize(720, 520)

        self._build_ui()
        self.refresh()
        self.probe_models_button.clicked.connect(self._probe_models)
        self.manual_model_button.clicked.connect(lambda checked=False: self._show_manual_model_input(True))
        self.available_models_combo.currentTextChanged.connect(self._apply_probed_model)
        self.import_model_button.clicked.connect(self._import_model)
        self.delete_model_button.clicked.connect(self._delete_model)
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
        model_form_layout.addRow("API Key", self.model_api_key_input)
        model_form_layout.addRow("提供方", self.model_provider_input)
        model_form_layout.addRow("可用模型", self.available_models_combo)
        model_form_layout.addRow("模型", self.model_id_input)
        self._set_form_field_hidden(model_form_layout, self.model_name_input, True)
        self._set_form_field_hidden(model_form_layout, self.model_provider_input, True)
        self._set_form_field_hidden(model_form_layout, self.available_models_combo, True)
        self._set_form_field_hidden(model_form_layout, self.model_id_input, True)
        model_layout.addWidget(model_form)
        model_layout.addWidget(self.probe_models_button)
        model_layout.addWidget(self.manual_model_button)
        model_layout.addWidget(self.import_model_button)
        model_layout.addWidget(self.delete_model_button)
        self.model_providers.setMinimumHeight(140)
        model_layout.addWidget(self.model_providers, stretch=1)

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
        close_button.setObjectName("DialogSecondaryButton")
        close_button.clicked.connect(self.close)
        footer.addWidget(close_button)
        root.addLayout(footer)

    def _set_form_field_hidden(self, form: QFormLayout, field: QWidget, hidden: bool) -> None:
        label = form.labelForField(field)
        if label is not None:
            label.setHidden(hidden)
        field.setHidden(hidden)

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
            item = QListWidgetItem("暂无已导入模型")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.model_providers.addItem(item)
            return
        for provider in providers:
            suffix = f" · {len(provider.available_models)} 个可用模型" if provider.available_models else ""
            item = QListWidgetItem(f"{provider.name} · {provider.model_name} · {provider.base_url}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, provider.name)
            self.model_providers.addItem(item)

    def _refresh_mcp_services(self) -> None:
        self.mcp_services.clear()
        services = list_mcp_service_settings()
        if not services:
            self.mcp_services.addItem("暂无已导入的 MCP 服务")
            return
        for service in services:
            self.mcp_services.addItem(f"{service.name} · {service.transport} · {service.endpoint}")

    def _import_model(self) -> None:
        base_url = self.model_url_input.text().strip()
        model_name = self.model_id_input.text().strip()
        if not base_url or not model_name:
            return
        available_models = self._available_model_items()
        if model_name not in available_models:
            available_models = (*available_models, model_name)
        import_model_provider_setting(
            name=self.model_name_input.text().strip() or self._default_model_provider_name(base_url, model_name),
            base_url=base_url,
            model_name=model_name,
            api_key=self.model_api_key_input.text().strip(),
            provider=self.model_provider_input.text().strip() or "openai-compatible",
            available_models=available_models,
        )
        for field in (
            self.model_name_input,
            self.model_url_input,
            self.model_id_input,
            self.model_api_key_input,
        ):
            field.clear()
        self.available_models_combo.clear()
        self._show_manual_model_input(False)
        self._show_available_models(False)
        self.refresh()
        if isinstance(self.parent(), MainWindow):
            self.parent()._refresh_model_selector()

    def _delete_model(self) -> None:
        item = self.model_providers.currentItem()
        if item is None:
            return
        provider_name = item.data(Qt.ItemDataRole.UserRole)
        if not provider_name:
            return
        result = QMessageBox.question(
            self,
            "删除模型",
            f"确定删除模型配置“{provider_name}”吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        delete_model_provider_setting(str(provider_name))
        self.refresh()
        parent = self.parent()
        if isinstance(parent, MainWindow):
            parent._refresh_model_selector()

    def _probe_models(self) -> None:
        name = self.model_name_input.text().strip() or "probe"
        base_url = self.model_url_input.text().strip()
        if not base_url:
            QMessageBox.warning(self, "探测失败", "请先填写模型 URL。")
            return
        provider = ModelProviderSettings(
            name=name,
            base_url=base_url,
            model_name=self.model_id_input.text().strip() or "probe",
            api_key=self.model_api_key_input.text().strip(),
            provider=self.model_provider_input.text().strip() or "openai-compatible",
        )
        try:
            models = fetch_available_models(provider)
        except Exception as exc:
            self.available_models_combo.clear()
            self._show_available_models(False)
            self._show_manual_model_input(True)
            QMessageBox.warning(self, "探测失败", str(exc))
            return
        self.available_models_combo.clear()
        self.available_models_combo.addItems(list(models))
        self._show_available_models(True)
        self.model_id_input.setText(models[0])
        self._show_manual_model_input(False)

    def _apply_probed_model(self, model_name: str) -> None:
        if model_name:
            self.model_id_input.setText(model_name)

    def _available_model_items(self) -> tuple[str, ...]:
        models: list[str] = []
        for index in range(self.available_models_combo.count()):
            model = self.available_models_combo.itemText(index).strip()
            if model and model not in models:
                models.append(model)
        return tuple(models)

    def _show_available_models(self, visible: bool) -> None:
        form = self.available_models_combo.parent().layout()
        if isinstance(form, QFormLayout):
            self._set_form_field_hidden(form, self.available_models_combo, not visible)

    def _show_manual_model_input(self, visible: bool = True) -> None:
        form = self.model_id_input.parent().layout()
        if isinstance(form, QFormLayout):
            self._set_form_field_hidden(form, self.model_id_input, not visible)

    @staticmethod
    def _default_model_provider_name(base_url: str, model_name: str) -> str:
        host = urlparse(base_url).hostname or base_url.split("/")[0] or "model"
        return f"{host} · {model_name}"

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
        self.settings_dialog: SettingsDialog | None = None
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(18)
        self._stream_timer.timeout.connect(self._advance_response_stream)
        self._stream_text = ""
        self._stream_index = 0
        self._pending_message: str | None = None
        self._chat_worker: ChatWorker | None = None
        self._approval_dialog: QMessageBox | None = None
        self._refreshing_model_selector = False

        self.chat_list = ChatListWidget()
        self.model_selector = QComboBox()
        self.input_box = QLineEdit()
        self.send_button = QPushButton("发送")
        self.status_value = QLabel("standby")
        self.execution_list = QListWidget()
        self.execution_list.setObjectName("StageList")
        self.plan_list = QListWidget()
        self.plan_list.setObjectName("PlanList")
        self.intent_value = QLabel("standby")
        self.tool_entry_label = QLabel("可调用工具")
        self.execution_graph_button = QPushButton("展开流程图")
        self.execution_graph_button.setObjectName("ExecutionGraphButton")
        self.execution_graph_button.setIcon(fluent_icon("CODE"))
        self.execution_graph_dialog: ExecutionGraphDialog | None = None
        self.memory_graph_panel = MemoryGraphPanel(self.view_model.memory)

        self._build_ui()
        self._connect_events()
        self._refresh_model_selector()
        self._refresh_messages()
        self._refresh_inspector(None)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("WorkbenchRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.memory_graph_panel)
        root_layout.addWidget(self._build_center_panel(), stretch=1)

        self.setCentralWidget(root)
        apply_workbench_theme(self)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(208)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(14)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_mark = QLabel("CM")
        brand_mark.setObjectName("BrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(32, 32)
        brand_column = QVBoxLayout()
        brand_column.setSpacing(0)
        brand = QLabel("Copy_Myself")
        brand.setObjectName("Brand")
        brand_caption = QLabel("PERSONAL AGENT")
        brand_caption.setObjectName("BrandCaption")
        brand_column.addWidget(brand)
        brand_column.addWidget(brand_caption)
        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_column)
        layout.addLayout(brand_row)

        nav_section = QLabel("导航")
        nav_section.setObjectName("SidebarSection")
        layout.addWidget(nav_section)

        nav_icons = {"工作台": "HOME", "设置": "SETTING"}
        for text in ("工作台", "设置"):
            button = QPushButton(text)
            button.setObjectName("SidebarButton")
            button.setIcon(fluent_icon(nav_icons[text]))
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
        panel.setObjectName("CenterPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 0, 28, 26)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("MinimalHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 14, 0, 14)
        header_layout.setSpacing(8)

        brand = QLabel("Copy_Myself")
        brand.setObjectName("Brand")
        header_layout.addWidget(brand)
        header_layout.addStretch()

        nav_icons = {"设置": "SETTING"}
        for text in ("设置",):
            button = QToolButton()
            button.setObjectName("NavButton")
            button.setIcon(fluent_icon(nav_icons[text]))
            button.setFixedSize(34, 34)
            button.setToolTip(text)
            button.setAccessibleName(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, name=text: self._handle_nav_click(name))
            header_layout.addWidget(button)
            self.nav_buttons[text] = button
        layout.addWidget(header)

        self.chat_list.setObjectName("ChatList")
        self.chat_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_list, stretch=1)

        composer = QFrame()
        composer.setObjectName("Composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(10, 10, 10, 10)
        composer_layout.setSpacing(8)
        self.input_box.setPlaceholderText("发送消息给 Copy_Myself")
        self.input_box.setObjectName("ComposerInput")
        self.input_box.setFixedHeight(42)
        self.model_selector.setObjectName("ComposerModelSelector")
        self.model_selector.setFixedHeight(42)
        self.model_selector.setMinimumWidth(180)
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.setText("")
        self.send_button.setFixedSize(42, 42)
        self.send_button.setIcon(fluent_icon("SEND"))
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(8)
        add_button = QToolButton()
        add_button.setObjectName("ComposerGhostButton")
        add_button.setIcon(fluent_icon("ADD"))
        add_button.setAccessibleName("添加")
        add_button.setToolTip("添加")
        add_button.setFixedSize(34, 34)
        add_button.setText("")
        add_button.setEnabled(False)
        bottom_row.addWidget(add_button)
        bottom_row.addStretch()
        bottom_row.addWidget(self.model_selector)
        bottom_row.addWidget(self.send_button)
        composer_layout.addWidget(self.input_box)
        composer_layout.addLayout(bottom_row)
        layout.addWidget(composer)

        return panel

        header = QFrame()
        header.setObjectName("HeaderBand")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("工作台")
        title.setObjectName("Title")
        subtitle = QLabel("本地智能工作台")
        subtitle.setObjectName("Subtitle")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(subtitle)
        header_layout.addLayout(title_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.tool_entry_label.setObjectName("PanelTitle")
        action_row.addWidget(self.tool_entry_label)

        tool_icons = {"内置工具": "DEVELOPER_TOOLS", "MCP 调用": "ROBOT"}
        for text in ("内置工具", "MCP 调用"):
            button = QToolButton()
            button.setText(text)
            button.setObjectName("ToolChip")
            button.setIcon(fluent_icon(tool_icons[text]))
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
        self.input_box.setObjectName("ComposerInput")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.setIcon(fluent_icon("SEND"))
        composer_layout.addWidget(self.input_box, stretch=1)
        composer_layout.addWidget(self.send_button)
        layout.addWidget(composer)

        return panel

    def _build_inspector(self) -> QWidget:
        inspector = QFrame()
        inspector.setObjectName("Inspector")
        inspector.setFixedWidth(320)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(18, 20, 18, 20)
        layout.setSpacing(14)

        execution_header = QHBoxLayout()
        execution_header.addWidget(self._section_title("执行阶段"))
        execution_header.addStretch()
        execution_header.addWidget(self.execution_graph_button)
        layout.addLayout(execution_header)
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
        self.model_selector.currentIndexChanged.connect(self._select_chat_model)
        self.execution_graph_button.clicked.connect(self._open_execution_graph_dialog)

    def _handle_nav_click(self, name: str) -> None:
        for button_name, button in self.nav_buttons.items():
            button.setChecked(button_name == name)
        if name == "设置":
            self._open_settings_dialog()

    def _refresh_model_selector(self) -> None:
        self._refreshing_model_selector = True
        self.model_selector.clear()
        providers = [provider for provider in list_model_provider_settings() if provider.enabled]
        for provider in providers:
            models = list(provider.available_models or (provider.model_name,))
            if provider.model_name not in models:
                models.insert(0, provider.model_name)
            for model in models:
                self.model_selector.addItem(model, (provider.name, model))
        if self.model_selector.count() == 0:
            settings = load_settings()
            self.model_selector.addItem(settings.model_name, ("", settings.model_name))
            self.model_selector.setEnabled(False)
        else:
            self.model_selector.setEnabled(True)
        self._refreshing_model_selector = False

    def _select_chat_model(self) -> None:
        if self._refreshing_model_selector:
            return
        data = self.model_selector.currentData()
        if not data:
            return
        provider_name, model_name = data
        if not provider_name:
            return
        try:
            select_model_provider_model(provider_name, model_name)
        except Exception as exc:
            QMessageBox.warning(self, "模型切换失败", str(exc))
            self._refresh_model_selector()
            return
        if self.settings_dialog is not None:
            self.settings_dialog.refresh()

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
        worker = ChatWorker(pending_message, self)
        self._chat_worker = worker
        worker.completed.connect(self._complete_worker_result)
        worker.approval_required.connect(self._show_approval_dialog)
        worker.failed.connect(self._complete_worker_error)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _complete_worker_result(self, result: ChatRunResult) -> None:
        pending_message = self._pending_message or result.message
        self._pending_message = None
        summary = RunSummary(
            message=pending_message,
            response=result.response,
            intent=result.intent,
            display_intent=result.display_intent,
            stage_label=result.display_intent,
            tool_result=result.tool_result,
            memory_context=result.memory_context,
            graph_steps=result.graph_steps,
        )
        self.view_model.latest_run = summary
        if self.view_model.messages and self.view_model.messages[-1].content == THINKING_MESSAGE:
            self.view_model.messages[-1] = ChatMessage(role="assistant", content=summary.response)
        else:
            self.view_model.messages.append(ChatMessage(role="assistant", content=summary.response))
        self.send_button.setEnabled(True)
        self.input_box.setEnabled(True)
        self.memory_graph_panel.refresh()
        self._refresh_inspector(summary)
        self.status_value.setText(summary.stage_label)
        self._start_response_stream(summary.response)

    def _complete_worker_error(self, message: str) -> None:
        self._pending_message = None
        if self.view_model.messages and self.view_model.messages[-1].content == THINKING_MESSAGE:
            self.view_model.messages[-1] = ChatMessage(role="assistant", content=message)
        self.send_button.setEnabled(True)
        self.input_box.setEnabled(True)
        self.status_value.setText("failed")
        self._refresh_messages()

    def _show_approval_dialog(self, pending) -> None:
        dialog = QMessageBox(QMessageBox.Icon.Warning, "Tool approval", f"{pending.service_id} / {pending.tool}\n\n{pending.summary}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.finished.connect(lambda result: self._resolve_approval(result == QMessageBox.StandardButton.Yes.value))
        self._approval_dialog = dialog
        dialog.open()

    def _resolve_approval(self, approved: bool) -> None:
        if self._chat_worker is not None:
            self._chat_worker.decide(approved)
        self._approval_dialog = None

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
            item = QListWidgetItem()
            widget = ExecutionStepWidget(index, step, active=summary is not None and index == len(steps))
            self.execution_list.addItem(item)
            self.execution_list.setItemWidget(item, widget)
            item.setSizeHint(widget.sizeHint())

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
            "3. 记忆图将在保存后自动更新",
        ]

    def _open_settings_dialog(self) -> None:
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.refresh()
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _open_execution_graph_dialog(self) -> None:
        steps = (
            self.view_model.latest_run.graph_steps
            if self.view_model.latest_run is not None
            else [
                "load_memory",
                "classify_intent",
                "run_tool",
                "create_response",
            ]
        )
        if self.execution_graph_dialog is None:
            self.execution_graph_dialog = ExecutionGraphDialog(steps, self)
        else:
            self.execution_graph_dialog.refresh_steps(steps)
        self.execution_graph_dialog.show()
        self.execution_graph_dialog.raise_()
        self.execution_graph_dialog.activateWindow()


STYLESHEET = WORKBENCH_QSS
