from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QTextEdit

from copy_myself.config import list_mcp_service_settings, list_model_provider_settings
from copy_myself.gui.main_window import MainWindow
from copy_myself.gui.view_model import WorkbenchViewModel

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    _APP = instance
    return instance


def test_main_window_uses_sci_fi_blue_shell() -> None:
    _app()
    window = MainWindow()

    stylesheet = window.styleSheet()

    assert "qlineargradient" in stylesheet
    assert "#031022" in stylesheet
    assert "#071b3a" in stylesheet
    assert "#35d7ff" in stylesheet
    window.close()


def test_sidebar_keeps_only_three_navigation_buttons() -> None:
    _app()
    window = MainWindow()

    assert list(window.nav_buttons) == ["工作台", "记忆", "设置"]
    assert [button.text() for button in window.nav_buttons.values()] == ["工作台", "记忆", "设置"]
    assert window.findChild(QLabel, "Brand").text() == "Copy_Myself"
    window.close()


def test_toolbar_and_inspector_keep_tool_entry_without_tool_result() -> None:
    _app()
    window = MainWindow()

    assert [button.text() for button in window.tool_buttons.values()] == ["内置工具", "MCP 调用"]
    assert window.execution_list.count() > 0
    assert window.plan_list.count() > 0
    assert not hasattr(window, "tool_result")
    assert not window.findChildren(QTextEdit)
    window.close()


def test_memory_button_opens_memory_dialog_and_settings_button_opens_settings_dialog() -> None:
    app = _app()
    view_model = WorkbenchViewModel()
    view_model.send_message("health check")
    window = MainWindow(view_model)

    window.nav_buttons["记忆"].click()
    app.processEvents()
    assert window.memory_dialog is not None
    assert window.memory_dialog.isVisible()
    assert window.memory_dialog.context_list.count() > 0

    window.settings_button.click()
    app.processEvents()
    assert window.settings_dialog is not None
    assert window.settings_dialog.isVisible()
    window.settings_dialog.close()
    window.memory_dialog.close()
    window.close()


def test_settings_dialog_imports_model_and_mcp_service(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COPY_MYSELF_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("COPY_MYSELF_ACTIVE_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_CURRENT_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL", raising=False)
    monkeypatch.delenv("COPY_MYSELF_MODEL_NAME", raising=False)

    app = _app()
    window = MainWindow()
    window._open_settings_dialog()
    app.processEvents()
    dialog = window.settings_dialog
    assert dialog is not None
    assert dialog.tabs.count() == 2
    assert dialog.size().height() <= 600

    dialog.model_name_input.setText("Local Qwen")
    dialog.model_url_input.setText("http://127.0.0.1:11434/v1")
    dialog.model_id_input.setText("qwen2.5:7b")
    dialog.model_api_key_input.setText("local-key")
    dialog._import_model()

    providers = list_model_provider_settings()
    assert len(providers) == 1
    assert providers[0].name == "Local Qwen"
    assert providers[0].base_url == "http://127.0.0.1:11434/v1"
    assert providers[0].model_name == "qwen2.5:7b"
    assert "qwen2.5:7b" in dialog.current_model_value.text()
    assert dialog.model_providers.count() == 1

    dialog.mcp_name_input.setText("Example MCP")
    dialog.mcp_url_input.setText("https://mcp.example.com")
    dialog.mcp_transport_input.setCurrentText("http")
    dialog.mcp_command_input.setText("npx")
    dialog.mcp_args_input.setText("--yes mcp-server")
    dialog._import_mcp_service()

    services = list_mcp_service_settings()
    assert len(services) == 1
    assert services[0].name == "Example MCP"
    assert services[0].endpoint == "https://mcp.example.com"
    assert services[0].transport == "http"
    assert services[0].command == "npx"
    assert services[0].args == ("--yes", "mcp-server")
    assert dialog.mcp_services.count() == 1
    dialog.close()
    window.close()
