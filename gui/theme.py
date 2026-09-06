from __future__ import annotations

from typing import Protocol

from PyQt6.QtGui import QIcon


class StyleTarget(Protocol):
    def setStyleSheet(self, style_sheet: str) -> None: ...


PALETTE = {
    "window": "#F4FAF8",
    "surface": "#FFFFFF",
    "surface_raised": "#ECF5F3",
    "primary": "#3F8587",
    "primary_end": "#79B8C0",
    "primary_hover": "#347477",
    "primary_soft": "#E1EFED",
    "focus": "#6FAEB3",
    "attention": "#D69A62",
    "text": "#203136",
    "text_muted": "#718184",
    "border": "#D7E6E3",
    "graph_background": "#234248",
    "graph_surface": "#2C5157",
    "graph_edge": "#4C7D82",
    "graph_node": "#A8C9C9",
    "graph_node_hover": "#79B8C0",
    "graph_node_selected": "#D69A62",
    "graph_text": "#F3FBFA",
    "graph_text_muted": "#B5CACA",
    "graph_border": "#477178",
}

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}


WORKBENCH_QSS = f"""
#WorkbenchRoot, QDialog#SettingsDialog, QDialog#ExecutionGraphDialog {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EAF5F2, stop:0.52 #F8FBFA, stop:1 #F9F4EC);
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
    border-radius: 10px;
    color: {PALETTE['text_muted']};
    padding: 8px;
}}
#NavButton:hover {{
    background: {PALETTE['primary_soft']};
    border-color: {PALETTE['border']};
    color: {PALETTE['primary']};
}}
#BrandMark {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {PALETTE['primary']}, stop:1 {PALETTE['primary_end']});
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
#WelcomeBand {{ background: transparent; border: none; }}
#Eyebrow {{ color: {PALETTE['text_muted']}; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
#WelcomeTitle {{ color: {PALETTE['text']}; font-size: 25px; font-weight: 600; }}
#WelcomeNote {{ color: {PALETTE['text_muted']}; font-size: 12px; }}
#MemoryGraphPanel {{
    background: transparent;
    border: none;
}}
#MemoryGraphSurface {{
    background: {PALETTE['graph_background']};
    border: 1px solid {PALETTE['graph_border']};
    border-radius: 16px;
}}
#MemoryGraphView {{
    background: {PALETTE['graph_background']};
    border: none;
}}
#MemoryGraphTitle {{
    background: {PALETTE['graph_background']};
    border: none;
    color: {PALETTE['graph_text']};
    font-size: 14px;
    font-weight: 700;
}}
#MemorySearchInput {{
    background: #31565D;
    border: 1px solid {PALETTE['graph_edge']};
    border-radius: 8px;
    color: {PALETTE['graph_text']};
    padding: 7px 10px;
    selection-background-color: {PALETTE['graph_border']};
}}
#MemorySearchInput:focus {{
    border-color: {PALETTE['graph_node_hover']};
}}
#MemoryDetailPanel {{
    background: {PALETTE['graph_surface']};
    border: 1px solid {PALETTE['graph_border']};
    border-radius: 16px;
}}
#MemoryDetailContent, #MemoryDetailScroll {{
    background: transparent;
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:0.52 #F1F9F7, stop:1 #FFF9F1);
    border: none;
}}
#Composer {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:0.52 #F3FAF8, stop:1 #FFF9F2);
    border: 1px solid {PALETTE['border']};
    border-radius: 16px;
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
#AgentStatus {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EEF8F6, stop:1 #F3F8FA);
    border: 1px solid #D7E9E6;
    border-radius: 12px;
}}
#StatusValue {{ color: {PALETTE['text_muted']}; font-size: 12px; }}
#StatusValue[ready="true"] {{ color: #4A856E; }}
#StatusDot {{ background: {PALETTE['attention']}; border-radius: 4px; }}
#StatusDot[ready="true"] {{ background: #4A856E; }}
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
#ChatList, #StageList, #MemoryContextList, #MemoryMessageList, #MemoryDetail,
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
#StageList {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:0.55 #F1F9F7, stop:1 #FFF9F1);
}}
#MemoryDetail {{
    selection-background-color: {PALETTE['primary_soft']};
}}
#ChatList::item, #StageList::item {{ background: transparent; border: none; padding: 3px 0; }}
#MemoryContextList::item, #MemoryMessageList::item,
#ModelProviderList::item, #McpServiceList::item {{
    border-bottom: 1px solid {PALETTE['border']};
    padding: 8px 6px;
}}
#MemoryContextList::item:selected, #MemoryMessageList::item:selected,
#ModelProviderList::item:selected, #McpServiceList::item:selected {{
    background: {PALETTE['primary_soft']};
    color: {PALETTE['text']};
}}
#UserMessage, #AssistantMessage {{ border-radius: 10px; }}
#UserMessage {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {PALETTE['primary']}, stop:1 {PALETTE['primary_end']}); border: 1px solid {PALETTE['primary']}; }}
#AssistantMessage {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:0.55 #F1F8F7, stop:1 #FFF9F1); border: 1px solid {PALETTE['border']}; }}
#MessageText {{ background: transparent; border: none; color: {PALETTE['text']}; }}
#ExecutionStep {{ background: transparent; border: none; }}
#ExecutionStep[active="true"] {{ background: #E7F3F0; border-radius: 10px; }}
#ExecutionStep[active="true"] #StepName {{ color: {PALETTE['primary']}; }}
#StepBadge {{
    background: {PALETTE['primary_soft']};
    border: 1px solid #CFE4E1;
    border-radius: 10px;
    color: {PALETTE['primary']};
    font-size: 10px;
    font-weight: 700;
}}
#StepName {{ color: {PALETTE['text']}; font-weight: 600; }}
#StepMeta {{ color: {PALETTE['text_muted']}; font-size: 10px; }}
#Inspector {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EAF5F2, stop:1 #F8F2EA);
    border: none;
    border-left: 1px solid {PALETTE['border']};
}}
#IntentCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFF, stop:0.55 #F1F9F7, stop:1 #FFF9F1);
    border: 1px solid {PALETTE['border']};
    border-radius: 14px;
}}
#IntentEyebrow {{
    color: {PALETTE['attention']};
    font-size: 10px;
    font-weight: 700;
}}
#IntentTitle {{ color: {PALETTE['text']}; font-size: 12px; font-weight: 700; }}
#IntentValue {{ color: {PALETTE['primary']}; font-size: 16px; font-weight: 700; }}
#PrimaryButton, QPushButton#DialogPrimaryButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {PALETTE['primary']}, stop:1 {PALETTE['primary_end']});
    border: 1px solid {PALETTE['primary']};
    border-radius: 6px;
    color: #FFFFFF;
    padding: 8px 13px;
    font-weight: 700;
}}
#PrimaryButton:hover, QPushButton#DialogPrimaryButton:hover {{
    background: {PALETTE['primary_hover']};
}}
#PrimaryButton:disabled {{
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
QComboBox#ComposerModelSelector {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F7FCFB, stop:1 #EEF6F5);
    border: 1px solid #CFE2DF;
    border-radius: 12px;
    color: {PALETTE['text']};
    padding: 6px 34px 6px 12px;
    font-size: 12px;
    font-weight: 600;
}}
QComboBox#ComposerModelSelector:hover {{
    background: #F4FBF9;
    border-color: {PALETTE['focus']};
}}
QComboBox#ComposerModelSelector:focus {{
    border-color: {PALETTE['focus']};
    outline: 2px solid rgba(111, 174, 179, 0.22);
    outline-offset: 0;
}}
QComboBox#ComposerModelSelector::drop-down {{
    width: 28px;
    border: none;
    border-left: 1px solid #D7E6E3;
    border-top-right-radius: 12px;
    border-bottom-right-radius: 12px;
}}
QComboBox#ComposerModelSelector QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid {PALETTE['border']};
    border-radius: 8px;
    color: {PALETTE['text']};
    padding: 4px;
    selection-background-color: {PALETTE['primary_soft']};
    selection-color: {PALETTE['text']};
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
    background: #EEF6F4;
    border: 1px solid transparent;
    border-radius: 9px;
    color: {PALETTE['text_muted']};
    margin: 3px 8px 3px 0;
    min-width: 112px;
    padding: 10px 14px;
    text-align: left;
}}
QTabWidget#SettingsTabs QTabBar {{
    qproperty-drawBase: 0;
    background: transparent;
}}
QTabWidget#SettingsTabs QTabBar::tab:selected {{
    background: {PALETTE['primary_soft']};
    color: {PALETTE['primary']};
    border-color: #CFE4E1;
    font-weight: 700;
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
