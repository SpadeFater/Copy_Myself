from __future__ import annotations

from typing import Protocol

from PyQt6.QtGui import QIcon


class StyleTarget(Protocol):
    def setStyleSheet(self, style_sheet: str) -> None: ...


PALETTE = {
    "window": "#F4F8F7",
    "surface": "#FFFFFF",
    "surface_raised": "#F5F7FF",
    "primary": "#637BC4",
    "primary_hover": "#526BB5",
    "attention": "#D58D6C",
    "text": "#26313B",
    "text_muted": "#7D8791",
    "border": "#DCE5E5",
    "graph_background": "#0D1214",
    "graph_surface": "#151C1F",
    "graph_edge": "#536467",
    "graph_node": "#A0B4B0",
    "graph_node_selected": "#62C9BB",
    "graph_text": "#E7EFEE",
    "graph_text_muted": "#82918F",
    "gradient": (
        "qlineargradient(x1:0, y1:0, x2:1, y2:1, "
        "stop:0 #F8FBFA, stop:0.52 #F4F6FF, stop:1 #EEF8F5)"
    ),
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


WORKBENCH_QSS = f"""
/* Hallmark · macrostructure: Workbench · tone: technical · anchor hue: teal */
/* Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V4 */
#WorkbenchRoot, QDialog#SettingsDialog, QDialog#ExecutionGraphDialog {{
    background: {PALETTE['gradient']};
    color: {PALETTE['text']};
    font-family: "Open Sans", "Segoe UI", "Microsoft YaHei";
    font-size: 13px;
}}
#Sidebar {{
    background: #0F1214;
    border: none;
    border-right: 1px solid {PALETTE['border']};
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
    background: #EEF2FF;
    border-color: #CBD6F4;
    color: #4E66AE;
}}
#BrandMark {{
    background: {PALETTE['primary']};
    color: #FFFFFF;
    border-radius: 6px;
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
#CenterPanel {{ background: transparent; }}
#MemoryGraphPanel {{
    background: {PALETTE['graph_surface']};
    border: none;
    border-right: 1px solid {PALETTE['graph_edge']};
}}
#MemoryGraphSurface, #MemoryGraphView {{
    background: {PALETTE['graph_background']};
    border: none;
}}
#MemoryGraphTitle {{
    background: {PALETTE['graph_background']};
    border: none;
    border-bottom: 1px solid {PALETTE['graph_edge']};
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
#MemoryDetailSummary, #MemoryDetailMeta {{ color: {PALETTE['graph_text_muted']}; }}
#MemoryDetailRelations {{ color: {PALETTE['graph_text']}; }}
#MemoryPanelSplitter::handle {{
    background: {PALETTE['graph_edge']};
    height: 1px;
}}
#HeaderBand, #StageBand, #Composer, #SettingsStatus, #SettingsSection {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
}}
#Composer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFFFFF, stop:1 #F7F9FF);
    border: 1px solid #D6DFE8;
    border-radius: 14px;
}}
#Title {{ color: {PALETTE['text']}; font-size: 23px; font-weight: 700; }}
#PanelTitle, #SectionTitle, #DialogTitle {{
    color: #34424E;
    font-size: 12px;
    font-weight: 700;
}}
#DialogTitle {{ font-size: 20px; }}
#StatusValue, #IntentValue, #CurrentModelValue {{
    color: #5A71B7;
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
    selection-background-color: #D7E1FF;
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
#UserMessage, #AssistantMessage {{ border-radius: 12px; }}
#UserMessage {{ background: #EEF2FF; border: 1px solid #D9E1FA; }}
#AssistantMessage {{ background: #FFFFFF; border: 1px solid #E1E8E8; }}
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
    color: #FFFFFF;
    padding: 8px 13px;
    font-weight: 700;
}}
#ExecutionGraphButton:hover, #PrimaryButton:hover, QPushButton#DialogPrimaryButton:hover {{
    background: {PALETTE['primary_hover']};
}}
#ExecutionGraphButton:disabled, #PrimaryButton:disabled {{
    background: #D8DEE4;
    border-color: #D8DEE4;
    color: #8C969F;
}}
#SecondaryButton, QPushButton#DialogSecondaryButton {{
    background: #F7F9FA;
    border: 1px solid #D8E0E4;
    border-radius: 6px;
    color: #52606B;
    padding: 8px 13px;
    font-weight: 600;
}}
#SecondaryButton:hover, QPushButton#DialogSecondaryButton:hover {{ border-color: #AAB9C4; }}
#ComposerInput, QLineEdit#SettingsInput, QComboBox#SettingsCombo {{
    background: #FFFFFF;
    border: 1px solid #D8E0E4;
    border-radius: 6px;
    color: {PALETTE['text']};
    padding: 9px 11px;
    selection-background-color: #D7E1FF;
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
    color: #526BB5;
    border-bottom: 2px solid {PALETTE['primary']};
}}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C8D4D7; min-height: 28px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: #AABCC2; }}
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
