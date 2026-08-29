from __future__ import annotations

from typing import Protocol

from PyQt6.QtGui import QIcon


class StyleTarget(Protocol):
    def setStyleSheet(self, style_sheet: str) -> None: ...


PALETTE = {
    "window": "#F8F7FC",
    "surface": "#FFFFFF",
    "surface_raised": "#F3F0FC",
    "primary": "#7565C8",
    "primary_hover": "#6656B5",
    "primary_soft": "#EEEAFB",
    "focus": "#9181E5",
    "attention": "#D58D6C",
    "text": "#29263D",
    "text_muted": "#716D84",
    "border": "#DFDBE9",
    "graph_background": "#29253F",
    "graph_surface": "#312D4B",
    "graph_edge": "#5B5577",
    "graph_node": "#B5B0C7",
    "graph_node_hover": "#B8ADFA",
    "graph_node_selected": "#9181E5",
    "graph_text": "#F3F1FB",
    "graph_text_muted": "#B7B0D2",
    "graph_border": "#4D4868",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


WORKBENCH_QSS = f"""
#WorkbenchRoot, QDialog#SettingsDialog, QDialog#ExecutionGraphDialog {{
    background: {PALETTE['window']};
    color: {PALETTE['text']};
    font-family: "Open Sans", "Segoe UI", "Microsoft YaHei";
    font-size: 13px;
}}
#Sidebar {{
    background: {PALETTE['graph_background']};
    border: none;
    border-right: 1px solid {PALETTE['graph_border']};
}}
#MinimalHeader {{
    background: transparent;
    border-bottom: 1px solid {PALETTE['border']};
}}
#NavButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: {PALETTE['text_muted']};
    padding: 8px;
}}
#NavButton:hover {{
    background: {PALETTE['primary_soft']};
    border-color: {PALETTE['border']};
    color: {PALETTE['primary']};
}}
#BrandMark {{
    background: {PALETTE['primary']};
    color: #FFFFFF;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
}}
#Brand {{
    color: {PALETTE['text']};
    font-size: 16px;
    font-weight: 600;
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
    color: {PALETTE['graph_text_muted']};
    padding: 9px 12px;
    text-align: left;
}}
#SidebarButton:hover {{
    background: {PALETTE['graph_surface']};
    color: {PALETTE['graph_text']};
}}
#SidebarButton:checked {{
    background: #403B61;
    border-color: {PALETTE['graph_border']};
    color: {PALETTE['graph_text']};
    font-weight: 700;
}}
#CenterPanel {{ background: transparent; }}
#MemoryGraphPanel {{
    background: {PALETTE['graph_surface']};
    border: none;
    border-right: 1px solid {PALETTE['graph_border']};
}}
#MemoryGraphSurface, #MemoryGraphView {{
    background: {PALETTE['graph_background']};
    border: none;
}}
#MemoryGraphTitle {{
    background: {PALETTE['graph_background']};
    border: none;
    border-bottom: 1px solid {PALETTE['graph_border']};
    color: {PALETTE['graph_text']};
    font-size: 14px;
    font-weight: 700;
    padding: {SPACING['md']}px {SPACING['lg']}px;
}}
#MemoryDetailPanel, #MemoryDetailContent, #MemoryDetailScroll {{
    background: {PALETTE['graph_surface']};
    border: none;
}}
#MemoryPanelSectionTitle {{
    color: {PALETTE['graph_node_selected']};
    font-size: 11px;
    font-weight: 700;
}}
#MemoryDetailTitle {{
    color: {PALETTE['graph_text']};
    font-size: 15px;
    font-weight: 700;
}}
#MemoryDetailSummary {{ color: {PALETTE['graph_text']}; }}
#MemoryDetailMeta {{ color: {PALETTE['graph_text_muted']}; }}
#MemoryDetailRelations {{ color: {PALETTE['graph_text']}; }}
#MemoryPanelSplitter::handle {{
    background: {PALETTE['graph_edge']};
    height: 1px;
}}
#MemoryDetailPanel QPushButton#DialogSecondaryButton {{
    background: #403B61;
    border-color: {PALETTE['graph_edge']};
    color: {PALETTE['graph_text']};
}}
#MemoryDetailPanel QPushButton#DialogSecondaryButton:hover {{
    background: {PALETTE['graph_border']};
    border-color: {PALETTE['graph_node_hover']};
}}
#MemoryDetailPanel QPushButton#DialogSecondaryButton:disabled {{
    background: #393450;
    border-color: {PALETTE['graph_border']};
    color: {PALETTE['graph_text_muted']};
}}
#HeaderBand, #StageBand, #SettingsStatus, #SettingsSection {{
    background: {PALETTE['surface']};
    border: none;
}}
#Composer {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
}}
#Title {{ color: {PALETTE['text']}; font-size: 23px; font-weight: 700; }}
#PanelTitle, #SectionTitle, #DialogTitle {{
    color: {PALETTE['text']};
    font-size: 12px;
    font-weight: 700;
}}
#DialogTitle {{ font-size: 20px; }}
#StatusValue, #IntentValue, #CurrentModelValue {{
    color: {PALETTE['primary']};
    font-size: 14px;
    font-weight: 700;
}}
#StatusDot {{ background: {PALETTE['primary']}; border-radius: 4px; }}
#ToolChip {{
    background: {PALETTE['surface_raised']};
    border: 1px solid transparent;
    border-radius: 8px;
    color: {PALETTE['text']};
    padding: 7px 11px;
    font-weight: 600;
}}
#ToolChip:hover {{ background: {PALETTE['primary_soft']}; border-color: {PALETTE['border']}; color: {PALETTE['primary']}; }}
#ToolChip:pressed {{ background: {PALETTE['primary_soft']}; }}
#ChatList, #StageList, #PlanList, #MemoryContextList, #MemoryMessageList, #MemoryDetail,
#ModelProviderList, #McpServiceList {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    color: {PALETTE['text']};
    outline: none;
    padding: 6px;
}}
#ChatList {{
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 14px 0;
}}
#MemoryDetail {{
    selection-background-color: {PALETTE['primary_soft']};
}}
#ChatList::item, #StageList::item {{ background: transparent; border: none; padding: 3px 0; }}
#PlanList::item, #MemoryContextList::item, #MemoryMessageList::item,
#ModelProviderList::item, #McpServiceList::item {{
    border-bottom: 1px solid {PALETTE['border']};
    padding: 8px 6px;
}}
#PlanList::item:selected, #MemoryContextList::item:selected, #MemoryMessageList::item:selected,
#ModelProviderList::item:selected, #McpServiceList::item:selected {{
    background: {PALETTE['primary_soft']};
    color: {PALETTE['text']};
}}
#UserMessage, #AssistantMessage {{ border-radius: 10px; }}
#UserMessage {{ background: {PALETTE['primary_soft']}; border: 1px solid #DDD7F5; }}
#AssistantMessage {{ background: {PALETTE['surface']}; border: 1px solid {PALETTE['border']}; }}
#MessageText {{ background: transparent; border: none; color: {PALETTE['text']}; }}
#ExecutionStep {{ background: transparent; border: none; }}
#StepBadge {{
    background: {PALETTE['primary_soft']};
    border: 1px solid #D8D1F3;
    border-radius: 10px;
    color: {PALETTE['primary']};
    font-size: 10px;
    font-weight: 700;
}}
#StepName {{ color: {PALETTE['text']}; font-weight: 600; }}
#StepMeta {{ color: {PALETTE['text_muted']}; font-size: 10px; }}
#Inspector {{
    background: {PALETTE['surface_raised']};
    border: none;
    border-left: 1px solid {PALETTE['border']};
}}
#ExecutionGraphButton, #PrimaryButton, QPushButton#DialogPrimaryButton {{
    background: {PALETTE['primary']};
    border: 1px solid {PALETTE['primary']};
    border-radius: 6px;
    color: #FFFFFF;
    padding: 8px 13px;
    font-weight: 700;
}}
#ExecutionGraphButton:hover, #PrimaryButton:hover, QPushButton#DialogPrimaryButton:hover {{
    background: {PALETTE['primary_hover']};
}}
#ExecutionGraphButton:disabled, #PrimaryButton:disabled {{
    background: #DDD9EA;
    border-color: #DDD9EA;
    color: #817B93;
}}
#SecondaryButton, QPushButton#DialogSecondaryButton {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    color: {PALETTE['text']};
    padding: 8px 13px;
    font-weight: 600;
}}
#SecondaryButton:hover, QPushButton#DialogSecondaryButton:hover {{ background: {PALETTE['surface_raised']}; border-color: {PALETTE['focus']}; }}
#ComposerInput, QLineEdit#SettingsInput, QComboBox#SettingsCombo {{
    background: #FFFFFF;
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    color: {PALETTE['text']};
    padding: 9px 11px;
    selection-background-color: {PALETTE['primary_soft']};
}}
#ComposerInput:hover, QLineEdit#SettingsInput:hover, QComboBox#SettingsCombo:hover {{
    background: #FCFBFE;
    border-color: #CFC8E4;
}}
#ComposerInput:focus, QLineEdit#SettingsInput:focus, QComboBox#SettingsCombo:focus {{
    border-color: {PALETTE['focus']};
    outline: 2px solid {PALETTE['focus']};
    outline-offset: 0;
}}
#ComposerModelSelector {{
    background: {PALETTE['surface_raised']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    color: {PALETTE['text']};
    padding: 5px 10px;
}}
#ComposerModelSelector:focus {{
    border-color: {PALETTE['focus']};
    outline: 2px solid {PALETTE['focus']};
    outline-offset: 0;
}}
#ComposerGhostButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
    color: {PALETTE['text_muted']};
    font-size: 18px;
    font-weight: 600;
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
    color: {PALETTE['primary']};
    border-bottom: 2px solid {PALETTE['primary']};
}}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CBC5DD; min-height: 28px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: #AAA2C3; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def apply_workbench_theme(target: StyleTarget) -> None:
    try:
        from qfluentwidgets import Theme, setTheme

        setTheme(Theme.LIGHT)
    except (ImportError, RuntimeError):
        pass
    target.setStyleSheet(WORKBENCH_QSS)


def fluent_icon(name: str) -> QIcon:
    try:
        from qfluentwidgets import FluentIcon

        return getattr(FluentIcon, name).icon()
    except (AttributeError, ImportError, RuntimeError):
        return QIcon()
