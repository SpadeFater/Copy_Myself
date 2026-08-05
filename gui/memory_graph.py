from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QLineF, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gui.theme import PALETTE, SPACING
from memory.models import MemoryEdge, MemoryNode


GRAPH_NODE_LIMIT = 100
GRAPH_SCENE_RADIUS = 220.0
MIN_ZOOM = 0.45
MAX_ZOOM = 3.5
ZOOM_STEP = 1.15
INITIAL_ZOOM = 0.56


class MemoryNodeItem(QGraphicsEllipseItem):
    def __init__(
        self,
        node: MemoryNode,
        on_click: Callable[[str], None],
    ) -> None:
        radius = 6.0 + node.importance * 4.0
        super().__init__(-radius, -radius, radius * 2.0, radius * 2.0)
        self.node_id = node.id
        self._on_click = on_click
        self._selected = False
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setZValue(2)

        label_text = node.summary.strip() or node.user_input.strip() or "未命名记忆"
        self.label = QGraphicsSimpleTextItem(_compact(label_text, 18), self)
        self.label.setBrush(QBrush(QColor(PALETTE["graph_text_muted"])))
        self.label.setPos(radius + SPACING["xs"], -SPACING["sm"])
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style()

    def _apply_style(self, hovered: bool = False) -> None:
        selected = self._selected or hovered
        fill = PALETTE["graph_node_selected"] if selected else PALETTE["graph_node"]
        outline = PALETTE["graph_text"] if selected else PALETTE["graph_background"]
        self.setBrush(QBrush(QColor(fill)))
        self.setPen(QPen(QColor(outline), 1.4 if selected else 0.8))
        self.label.setBrush(
            QBrush(QColor(PALETTE["graph_text"] if selected else PALETTE["graph_text_muted"]))
        )

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
        self.graph_scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        positions = _node_positions(nodes)

        for edge in edges:
            start = positions.get(edge.from_node)
            end = positions.get(edge.to_node)
            if start is None or end is None:
                continue
            line = QGraphicsLineItem(QLineF(start[0], start[1], end[0], end[1]))
            alpha = max(70, min(190, int(70 + edge.weight * 120)))
            color = QColor(PALETTE["graph_edge"])
            color.setAlpha(alpha)
            line.setPen(QPen(color, 0.7 + edge.weight * 0.8))
            line.setZValue(0)
            self.graph_scene.addItem(line)
            self.edge_items.append(line)

        for node in nodes:
            item = MemoryNodeItem(node, self.select_node)
            x, y = positions[node.id]
            item.setPos(x, y)
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
        self.title_label = QLabel("选择一个记忆节点")
        self.summary_label = QLabel("点击上方节点查看详情")
        self.tags_label = QLabel()
        self.meta_label = QLabel()
        self.relations_label = QLabel()
        self.title_label.setObjectName("MemoryDetailTitle")
        self.summary_label.setObjectName("MemoryDetailSummary")
        self.tags_label.setObjectName("MemoryDetailMeta")
        self.meta_label.setObjectName("MemoryDetailMeta")
        self.relations_label.setObjectName("MemoryDetailRelations")

        content = QWidget()
        content.setObjectName("MemoryDetailContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(
            SPACING["lg"],
            SPACING["md"],
            SPACING["lg"],
            SPACING["lg"],
        )
        content_layout.setSpacing(SPACING["sm"])
        section_label = QLabel("节点详情")
        section_label.setObjectName("MemoryPanelSectionTitle")
        content_layout.addWidget(section_label)
        for label in (
            self.title_label,
            self.summary_label,
            self.tags_label,
            self.meta_label,
            self.relations_label,
        ):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            content_layout.addWidget(label)
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setObjectName("MemoryDetailScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def show_node(
        self,
        node: MemoryNode,
        edges: list[MemoryEdge],
        nodes_by_id: dict[str, MemoryNode],
    ) -> None:
        title = node.summary.strip() or node.user_input.strip() or "未命名记忆"
        user_input = node.user_input.strip() or "暂无用户输入"
        memory_summary = node.assistant_response.strip() or node.summary.strip() or "暂无摘要"
        self.title_label.setText(title)
        self.summary_label.setText(f"用户  {user_input}\n记忆  {memory_summary}")
        self.tags_label.setText("标签  " + (" · ".join(node.tags) if node.tags else "无"))
        created_at = node.created_at.replace("T", " ", 1)
        self.meta_label.setText(f"创建  {created_at}\n来源  {node.source}")
        relation_lines = _relation_lines(node.id, edges, nodes_by_id)
        self.relations_label.setText(
            "关联关系\n" + ("\n".join(relation_lines) if relation_lines else "暂无关联节点")
        )


class MemoryGraphPanel(QFrame):
    def __init__(self, memory: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.memory = memory
        self.nodes: list[MemoryNode] = []
        self.edges: list[MemoryEdge] = []
        self._nodes_by_id: dict[str, MemoryNode] = {}
        self.setObjectName("MemoryGraphPanel")
        self.setMinimumWidth(318)
        self.setMaximumWidth(372)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        self.detail_panel = MemoryDetailPanel()
        self.graph_view = MemoryGraphView(self._show_node)
        graph_frame = QFrame()
        graph_frame.setObjectName("MemoryGraphSurface")
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_title = QLabel("记忆图")
        graph_title.setObjectName("MemoryGraphTitle")
        graph_layout.addWidget(graph_title)
        graph_layout.addWidget(self.graph_view, stretch=1)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setObjectName("MemoryPanelSplitter")
        self.splitter.addWidget(graph_frame)
        self.splitter.addWidget(self.detail_panel)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 64)
        self.splitter.setStretchFactor(1, 36)
        self.splitter.setSizes([640, 360])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.refresh()

    def refresh(self) -> None:
        list_nodes = getattr(self.memory, "list_nodes", None)
        list_edges = getattr(self.memory, "list_edges", None)
        self.nodes = list_nodes(limit=GRAPH_NODE_LIMIT) if callable(list_nodes) else []
        self.edges = list_edges() if callable(list_edges) else []
        self._nodes_by_id = {node.id: node for node in self.nodes}
        self.graph_view.set_graph(self.nodes, self.edges)

    def _show_node(self, node_id: str) -> None:
        node = self._nodes_by_id.get(node_id)
        if node is not None:
            self.detail_panel.show_node(node, self.edges, self._nodes_by_id)


def _node_positions(nodes: list[MemoryNode]) -> dict[str, tuple[float, float]]:
    if not nodes:
        return {}
    positions: dict[str, tuple[float, float]] = {}
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    for index, node in enumerate(nodes):
        radius = GRAPH_SCENE_RADIUS * math.sqrt((index + 0.5) / len(nodes))
        angle = index * golden_angle
        positions[node.id] = (math.cos(angle) * radius, math.sin(angle) * radius)
    return positions


def _relation_lines(
    node_id: str,
    edges: list[MemoryEdge],
    nodes_by_id: dict[str, MemoryNode],
) -> list[str]:
    lines: list[str] = []
    for edge in edges:
        if edge.from_node == node_id:
            other_id = edge.to_node
        elif edge.to_node == node_id:
            other_id = edge.from_node
        else:
            continue
        other = nodes_by_id.get(other_id)
        other_title = (
            (other.summary.strip() or other.user_input.strip()) if other is not None else other_id
        )
        reason = f" · {edge.reason}" if edge.reason else ""
        lines.append(f"{edge.relation} · {_compact(other_title, 30)}{reason}")
    return lines


def _compact(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


__all__ = ["MemoryGraphPanel", "MemoryGraphView", "MemoryDetailPanel"]
