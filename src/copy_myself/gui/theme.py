from __future__ import annotations

from typing import Protocol

from PyQt6.QtGui import QIcon


class StyleTarget(Protocol):
    def setStyleSheet(self, style_sheet: str) -> None: ...


PALETTE = {
    "window": "#0B0D0F",
    "surface": "#121518",
    "surface_raised": "#191D21",
    "primary": "#39C6B4",
    "primary_hover": "#54D6C5",
    "attention": "#F07D62",
    "text": "#F3F5F4",
    "text_muted": "#98A29F",
    "border": "#29302F",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


WORKBENCH_QSS = f"""
#WorkbenchRoot, QDialog#MemoryDialog, QDialog#SettingsDialog, QDialog#ExecutionGraphDialog {{
    background: {PALETTE['window']};
    color: {PALETTE['text']};
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 12px;
}}
#Sidebar {{
    background: #0F1214;
    border: none;
    border-right: 1px solid {PALETTE['border']};
}}
#BrandMark {{
    background: {PALETTE['primary']};
    color: #07110F;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 800;
}}
#Brand {{
    color: {PALETTE['text']};
    font-size: 17px;
    font-weight: 700;
}}
#BrandCaption, #SidebarSection, #Subtitle, #DialogSubtitle, #SectionHint, #ModelSourceValue {{
    color: {PALETTE['text_muted']};
}}
#SidebarSection {{
    font-size: 10px;
    font-weight: 700;
    padding-top: 8px;
}}
#SidebarButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #BBC3C1;
    padding: 9px 12px;
    text-align: left;
}}
#SidebarButton:hover {{
    background: {PALETTE['surface_raised']};
    color: {PALETTE['text']};
}}
#SidebarButton:checked {{
    background: #18312D;
    border-color: #28564F;
    color: #79E1D3;
    font-weight: 700;
}}
#CenterPanel {{ background: {PALETTE['window']}; }}
#HeaderBand, #StageBand, #Composer, #SettingsStatus, #SettingsSection {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
}}
#Title {{ color: {PALETTE['text']}; font-size: 23px; font-weight: 700; }}
#PanelTitle, #SectionTitle, #DialogTitle {{
    color: #DDE2E0;
    font-size: 12px;
    font-weight: 700;
}}
#DialogTitle {{ font-size: 20px; }}
#StatusValue, #IntentValue, #CurrentModelValue {{
    color: #72DED0;
    font-size: 14px;
    font-weight: 700;
}}
#StatusDot {{ background: {PALETTE['primary']}; border-radius: 4px; }}
#ToolChip {{
    background: #171B1E;
    border: 1px solid #313938;
    border-radius: 6px;
    color: #C9D0CE;
    padding: 7px 11px;
    font-weight: 600;
}}
#ToolChip:hover {{ border-color: #4C817A; color: #7BE1D3; }}
#ToolChip:pressed {{ background: #20312E; }}
#ChatList, #StageList, #PlanList, #MemoryContextList, #MemoryMessageList,
#ModelProviderList, #McpServiceList {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    color: {PALETTE['text']};
    outline: none;
    padding: 6px;
}}
#ChatList::item, #StageList::item {{ background: transparent; border: none; padding: 3px 0; }}
#PlanList::item, #MemoryContextList::item, #MemoryMessageList::item,
#ModelProviderList::item, #McpServiceList::item {{
    border-bottom: 1px solid #232927;
    padding: 8px 6px;
}}
#PlanList::item:selected, #MemoryContextList::item:selected, #MemoryMessageList::item:selected,
#ModelProviderList::item:selected, #McpServiceList::item:selected {{
    background: #1B302D;
    color: {PALETTE['text']};
}}
#UserMessage, #AssistantMessage {{ border-radius: 8px; }}
#UserMessage {{ background: #173632; border: 1px solid #285A53; }}
#AssistantMessage {{ background: #191D20; border: 1px solid #2C3332; }}
#MessageText {{ background: transparent; border: none; color: {PALETTE['text']}; }}
#ExecutionStep {{ background: transparent; border: none; }}
#StepBadge {{
    background: #1D3531;
    border: 1px solid #35655D;
    border-radius: 10px;
    color: #7BE1D3;
    font-size: 10px;
    font-weight: 700;
}}
#StepName {{ color: #D7DDDB; font-weight: 600; }}
#StepMeta {{ color: {PALETTE['text_muted']}; font-size: 10px; }}
#Inspector {{
    background: #0F1214;
    border: none;
    border-left: 1px solid {PALETTE['border']};
}}
#ExecutionGraphButton, #PrimaryButton, QPushButton#DialogPrimaryButton {{
    background: {PALETTE['primary']};
    border: 1px solid {PALETTE['primary']};
    border-radius: 6px;
    color: #07110F;
    padding: 8px 13px;
    font-weight: 700;
}}
#ExecutionGraphButton:hover, #PrimaryButton:hover, QPushButton#DialogPrimaryButton:hover {{
    background: {PALETTE['primary_hover']};
}}
#ExecutionGraphButton:disabled, #PrimaryButton:disabled {{
    background: #27302F;
    border-color: #27302F;
    color: #69716F;
}}
#SecondaryButton, QPushButton#DialogSecondaryButton {{
    background: #1A1E21;
    border: 1px solid #343B3A;
    border-radius: 6px;
    color: #D8DDDB;
    padding: 8px 13px;
    font-weight: 600;
}}
#SecondaryButton:hover, QPushButton#DialogSecondaryButton:hover {{ border-color: #4F6561; }}
#ComposerInput, QLineEdit#SettingsInput, QComboBox#SettingsCombo {{
    background: #0D1012;
    border: 1px solid #343B3A;
    border-radius: 6px;
    color: {PALETTE['text']};
    padding: 9px 11px;
    selection-background-color: #285A53;
}}
#ComposerInput:focus, QLineEdit#SettingsInput:focus, QComboBox#SettingsCombo:focus {{
    border-color: {PALETTE['primary']};
}}
QTabWidget#SettingsTabs::pane {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    top: -1px;
}}
QTabWidget#SettingsTabs QTabBar::tab {{
    background: transparent;
    color: {PALETTE['text_muted']};
    padding: 8px 18px;
}}
QTabWidget#SettingsTabs QTabBar::tab:selected {{
    color: #7BE1D3;
    border-bottom: 2px solid {PALETTE['primary']};
}}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3A4442; min-height: 28px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: #53615E; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def apply_workbench_theme(target: StyleTarget) -> None:
    try:
        from qfluentwidgets import Theme, setTheme

        setTheme(Theme.DARK)
    except (ImportError, RuntimeError):
        pass
    target.setStyleSheet(WORKBENCH_QSS)


def fluent_icon(name: str) -> QIcon:
    try:
        from qfluentwidgets import FluentIcon

        return getattr(FluentIcon, name).icon()
    except (AttributeError, ImportError, RuntimeError):
        return QIcon()
