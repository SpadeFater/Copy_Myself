from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QLineF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.theme import PALETTE, SPACING
from memory.models import MemoryEdge, MemoryNode


GRAPH_SCENE_RADIUS = 220.0
NODE_POSITION_SPACING = 22.0
MIN_ZOOM = 0.05
MAX_ZOOM = 3.5
ZOOM_STEP = 1.15
INITIAL_ZOOM = 0.56


class MemoryNodeItem(QGraphicsEllipseItem):
    def __init__(self, node: MemoryNode, on_click: Callable[[str], None]) -> None:
        radius = 6.0 + node.importance * 4.0
        super().__init__(-radius, -radius, radius * 2.0, radius * 2.0)
        self.node_id = node.id
        self._on_click = on_click
        self._selected = False
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(node.user_input.strip() or "暂无用户问题")
        self.setZValue(2)
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def _apply_style(self, hovered: bool = False) -> None:
        active = self._selected or hovered
        fill = (
            PALETTE["graph_node_selected"]
            if self._selected
            else PALETTE["graph_node_hover"]
            if hovered
            else PALETTE["graph_node"]
        )
        outline = PALETTE["graph_text"] if active else PALETTE["graph_border"]
        self.setBrush(QBrush(QColor(fill)))
        self.setPen(QPen(QColor(outline), 1.4 if active else 1.0))

    def hoverEnterEvent(self, event: Any) -> None:
        self._apply_style(hovered=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: Any) -> None:
        self._apply_style()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        self._on_click(self.node_id)
        event.accept()


class MemoryGraphView(QGraphicsView):
    def __init__(self, on_node_selected: Callable[[str], None]) -> None:
        self.graph_scene = QGraphicsScene()
        super().__init__(self.graph_scene)
        self._on_node_selected = on_node_selected
        self._zoom = INITIAL_ZOOM
        self.selected_node_id: str | None = None
        self.node_items: dict[str, MemoryNodeItem] = {}
        self.edge_items: list[QGraphicsLineItem] = []
        self.setObjectName("MemoryGraphView")
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(PALETTE["graph_background"])))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSceneRect(-330.0, -260.0, 660.0, 520.0)
        self.scale(INITIAL_ZOOM, INITIAL_ZOOM)

    def set_graph(self, nodes: list[MemoryNode], edges: list[MemoryEdge]) -> None:
        previous_selection = self.selected_node_id
        initial_graph = not self.node_items
        self.graph_scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        positions = _node_positions(nodes)
        radius = _scene_radius(len(nodes))
        self.setSceneRect(-radius, -radius, radius * 2.0, radius * 2.0)
        if initial_graph:
            self.resetTransform()
            self._zoom = min(INITIAL_ZOOM, 125.0 / radius)
            self.scale(self._zoom, self._zoom)

        for edge in edges:
            start = positions.get(edge.from_node)
            end = positions.get(edge.to_node)
            if start is None or end is None:
                continue
            line = QGraphicsLineItem(QLineF(start[0], start[1], end[0], end[1]))
            alpha = max(52, min(150, int(52 + edge.weight * 98)))
            color = QColor(PALETTE["graph_edge"])
            color.setAlpha(alpha)
            line.setPen(QPen(color, 0.6 + edge.weight * 0.7))
            line.setZValue(0)
            self.graph_scene.addItem(line)
            self.edge_items.append(line)

        for node in nodes:
            item = MemoryNodeItem(node, self.select_node)
            item.setPos(*positions[node.id])
            self.graph_scene.addItem(item)
            self.node_items[node.id] = item

        selection = previous_selection if previous_selection in self.node_items else None
        if selection is None and nodes:
            selection = nodes[-1].id
        self.select_node(selection)

    def select_node(self, node_id: str | None) -> None:
        self.selected_node_id = node_id
        for item_id, item in self.node_items.items():
            item.set_selected(item_id == node_id)
        if node_id is not None:
            self._on_node_selected(node_id)

    def wheelEvent(self, event: Any) -> None:
        direction = event.angleDelta().y()
        if direction == 0:
            event.accept()
            return
        next_zoom = self._zoom * (ZOOM_STEP if direction > 0 else 1.0 / ZOOM_STEP)
        next_zoom = max(MIN_ZOOM, min(MAX_ZOOM, next_zoom))
        factor = next_zoom / self._zoom
        if not math.isclose(factor, 1.0):
            self.scale(factor, factor)
            self._zoom = next_zoom
        event.accept()


class MemoryDetailPanel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("MemoryDetailPanel")
        self.user_input_label = QLabel("暂无记忆节点")
        self.assistant_response_label = QLabel()
        self.created_at_label = QLabel()
        self.related_ids_label = QLabel()
        self.user_input_label.setObjectName("MemoryDetailTitle")
        self.assistant_response_label.setObjectName("MemoryDetailSummary")
        self.created_at_label.setObjectName("MemoryDetailMeta")
        self.related_ids_label.setObjectName("MemoryDetailRelations")
        self.related_nodes_button = QPushButton("查看关联节点（0）")
        self.related_nodes_button.setObjectName("DialogSecondaryButton")
        self.related_nodes_button.setEnabled(False)

        content = QWidget()
        content.setObjectName("MemoryDetailContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["lg"]
        )
        content_layout.setSpacing(SPACING["sm"])
        section_label = QLabel("节点详情")
        section_label.setObjectName("MemoryPanelSectionTitle")
        content_layout.addWidget(section_label)
        for label in (
            self.user_input_label,
            self.assistant_response_label,
            self.created_at_label,
            self.related_ids_label,
        ):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content_layout.addWidget(label)
        content_layout.addWidget(self.related_nodes_button)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("MemoryDetailScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def show_node(self, node: MemoryNode, related_nodes: list[MemoryNode]) -> None:
        self.user_input_label.setText(
            f"用户问题\n{node.user_input.strip() or '暂无用户问题'}"
        )
        self.assistant_response_label.setText(
            f"助手回答\n{node.assistant_response.strip() or '暂无助手回答'}"
        )
        self.created_at_label.setText(
            f"创建时间\n{node.created_at.replace('T', ' ', 1)}"
        )
        related_ids = "\n".join(related.id for related in related_nodes) or "暂无关联节点"
        self.related_ids_label.setText(f"关联节点\n{related_ids}")
        self.related_nodes_button.setText(f"查看关联节点（{len(related_nodes)}）")
        self.related_nodes_button.setEnabled(bool(related_nodes))

    def clear(self) -> None:
        self.user_input_label.setText("暂无匹配记忆节点")
        self.assistant_response_label.clear()
        self.created_at_label.clear()
        self.related_ids_label.clear()
        self.related_nodes_button.setText("查看关联节点（0）")
        self.related_nodes_button.setEnabled(False)


class RelatedNodesDialog(QDialog):
    def __init__(self, nodes: list[MemoryNode], parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("关联节点")
        self.setModal(True)
        self.resize(520, 560)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            SPACING["lg"], SPACING["lg"], SPACING["lg"], SPACING["lg"]
        )
        content_layout.setSpacing(SPACING["md"])
        if not nodes:
            content_layout.addWidget(QLabel("暂无关联节点"))
        for node in nodes:
            for title, value in (
                ("ID", node.id),
                ("用户问题", node.user_input.strip() or "暂无用户问题"),
                ("助手回答", node.assistant_response.strip() or "暂无助手回答"),
                ("创建时间", node.created_at.replace("T", " ", 1)),
            ):
                label = QLabel(f"{title}\n{value}")
                label.setWordWrap(True)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                content_layout.addWidget(label)
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            content_layout.addWidget(separator)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        close_button = QPushButton("关闭")
        close_button.setObjectName("DialogSecondaryButton")
        close_button.clicked.connect(self.close)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(close_button)


class MemoryGraphPanel(QFrame):
    def __init__(self, memory: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.memory = memory
        self.nodes: list[MemoryNode] = []
        self.edges: list[MemoryEdge] = []
        self.filtered_nodes: list[MemoryNode] = []
        self.filtered_edges: list[MemoryEdge] = []
        self._nodes_by_id: dict[str, MemoryNode] = {}
        self._related_dialog: RelatedNodesDialog | None = None
        self.setObjectName("MemoryGraphPanel")
        self.setMinimumWidth(318)
        self.setMaximumWidth(372)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.detail_panel = MemoryDetailPanel()
        self.detail_panel.related_nodes_button.clicked.connect(self._open_related_nodes_dialog)
        self.graph_view = MemoryGraphView(self._show_node)
        graph_frame = QFrame()
        graph_frame.setObjectName("MemoryGraphSurface")
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_header = QHBoxLayout()
        graph_header.setContentsMargins(SPACING["lg"], SPACING["md"], SPACING["lg"], SPACING["md"])
        graph_title = QLabel("记忆图")
        graph_title.setObjectName("MemoryGraphTitle")
        self.search_input = QLineEdit()
        self.search_input.setObjectName("MemorySearchInput")
        self.search_input.setPlaceholderText("搜索记忆节点...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(240)
        self.search_input.textChanged.connect(self._apply_search)
        graph_header.addWidget(graph_title)
        graph_header.addStretch()
        graph_header.addWidget(self.search_input)
        graph_layout.addLayout(graph_header)
        graph_layout.addWidget(self.graph_view, stretch=1)
        graph_frame.setMinimumHeight(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING["lg"])
        layout.addWidget(graph_frame, stretch=3)
        self.detail_panel.setMinimumHeight(260)
        layout.addWidget(self.detail_panel, stretch=2)
        self.refresh()

    def refresh(self) -> None:
        list_nodes = getattr(self.memory, "list_nodes", None)
        list_edges = getattr(self.memory, "list_edges", None)
        self.nodes = list_nodes() if callable(list_nodes) else []
        self.edges = list_edges() if callable(list_edges) else []
        self._nodes_by_id = {node.id: node for node in self.nodes}
        self._apply_search(self.search_input.text())

    def _apply_search(self, query: str) -> None:
        needle = query.strip().casefold()
        if needle:
            visible_nodes = [
                node for node in self.nodes if needle in self._node_search_text(node).casefold()
            ]
        else:
            visible_nodes = list(self.nodes)
        visible_ids = {node.id for node in visible_nodes}
        visible_edges = [
            edge
            for edge in self.edges
            if edge.from_node in visible_ids and edge.to_node in visible_ids
        ]
        self.filtered_nodes = visible_nodes
        self.filtered_edges = visible_edges
        self.graph_view.set_graph(visible_nodes, visible_edges)
        if needle and visible_nodes:
            self.graph_view.select_node(visible_nodes[0].id)
        elif not visible_nodes:
            self.detail_panel.clear()

    @staticmethod
    def _node_search_text(node: MemoryNode) -> str:
        return " ".join(
            (
                node.user_input,
                node.assistant_response,
                node.summary,
                " ".join(node.tags),
            )
        )

    def _show_node(self, node_id: str) -> None:
        node = self._nodes_by_id.get(node_id)
        if node is not None:
            self.detail_panel.show_node(node, self._related_nodes(node_id))

    def _related_nodes(self, node_id: str) -> list[MemoryNode]:
        get_related_nodes = getattr(self.memory, "get_related_nodes", None)
        if callable(get_related_nodes):
            return get_related_nodes(node_id)
        related_ids: set[str] = set()
        for edge in self.edges:
            if edge.from_node == node_id:
                related_ids.add(edge.to_node)
            elif edge.to_node == node_id:
                related_ids.add(edge.from_node)
        related = sorted(
            (self._nodes_by_id[node_id] for node_id in related_ids if node_id in self._nodes_by_id),
            key=lambda node: node.id,
        )
        return sorted(related, key=lambda node: node.created_at, reverse=True)

    def _open_related_nodes_dialog(self) -> None:
        node_id = self.graph_view.selected_node_id
        if node_id is None:
            return
        self._related_dialog = RelatedNodesDialog(self._related_nodes(node_id), self.window())
        self._related_dialog.open()


def _node_positions(nodes: list[MemoryNode]) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    for index, node in enumerate(nodes):
        radius = NODE_POSITION_SPACING * math.sqrt(index + 0.5)
        angle = index * golden_angle
        positions[node.id] = (math.cos(angle) * radius, math.sin(angle) * radius)
    return positions


def _scene_radius(node_count: int) -> float:
    return max(GRAPH_SCENE_RADIUS, NODE_POSITION_SPACING * math.sqrt(node_count + 0.5) + 32.0)


__all__ = ["MemoryDetailPanel", "MemoryGraphPanel", "MemoryGraphView"]
