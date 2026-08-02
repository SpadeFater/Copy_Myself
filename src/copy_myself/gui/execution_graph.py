from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import (
    QDialog,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from copy_myself.gui.theme import PALETTE, apply_workbench_theme


@dataclass(frozen=True)
class ExecutionNode:
    name: str
    position: int


@dataclass(frozen=True)
class ExecutionEdge:
    source: str
    target: str


@dataclass(frozen=True)
class ExecutionGraph:
    nodes: tuple[ExecutionNode, ...]
    edges: tuple[ExecutionEdge, ...]


def build_execution_graph(steps: list[str]) -> ExecutionGraph:
    nodes = tuple(ExecutionNode(name=step, position=index) for index, step in enumerate(steps, 1))
    edges = tuple(
        ExecutionEdge(source=source.name, target=target.name)
        for source, target in zip(nodes, nodes[1:])
    )
    return ExecutionGraph(nodes=nodes, edges=edges)


class ExecutionGraphView(QGraphicsView):
    NODE_WIDTH = 142.0
    NODE_HEIGHT = 78.0
    NODE_GAP = 46.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ExecutionGraphView")
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setInteractive(False)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QColor(PALETTE["window"]))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.scene() and not self.scene().itemsBoundingRect().isEmpty():
            self.fitInView(self.scene().itemsBoundingRect().adjusted(-28, -28, 28, 28), Qt.AspectRatioMode.KeepAspectRatio)


class ExecutionGraphDialog(QDialog):
    def __init__(self, steps: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ExecutionGraphDialog")
        self.setWindowTitle("执行流程图")
        self.setModal(False)
        self.resize(920, 500)
        self.is_read_only = True
        self.step_names: list[str] = []
        self.scene = QGraphicsScene(self)
        self.view = ExecutionGraphView(self)
        self.view.setScene(self.scene)

        self._build_ui()
        apply_workbench_theme(self)
        self.refresh_steps(steps)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel("执行流程图")
        title.setObjectName("DialogTitle")
        subtitle = QLabel("只读视图 · 节点顺序来自当前 LangGraph 运行摘要")
        subtitle.setObjectName("DialogSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()
        close_button = QPushButton("关闭")
        close_button.setObjectName("DialogSecondaryButton")
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)

        root.addLayout(header)
        root.addWidget(self.view, stretch=1)

    def refresh_steps(self, steps: list[str]) -> None:
        self.step_names = list(steps)
        self.scene.clear()
        graph = build_execution_graph(self.step_names)
        if not graph.nodes:
            empty = self.scene.addText("暂无执行节点")
            empty.setDefaultTextColor(QColor(PALETTE["text_muted"]))
            return

        positions: dict[str, QRectF] = {}
        for index, node in enumerate(graph.nodes):
            x = index * (ExecutionGraphView.NODE_WIDTH + ExecutionGraphView.NODE_GAP)
            rect = QRectF(x, 42, ExecutionGraphView.NODE_WIDTH, ExecutionGraphView.NODE_HEIGHT)
            positions[node.name] = rect
            self._add_node(rect, node, is_last=index == len(graph.nodes) - 1)

        for edge in graph.edges:
            self._add_edge(positions[edge.source], positions[edge.target])

        bounds = self.scene.itemsBoundingRect().adjusted(-24, -24, 24, 24)
        self.scene.setSceneRect(bounds)
        self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def _add_node(self, rect: QRectF, node: ExecutionNode, *, is_last: bool) -> None:
        border = QColor(PALETTE["primary"] if is_last else "#40504D")
        fill = QColor("#18312D" if is_last else PALETTE["surface_raised"])
        card = QGraphicsRectItem(rect)
        card.setPen(QPen(border, 1.4))
        card.setBrush(fill)
        self.scene.addItem(card)

        badge = QGraphicsTextItem(f"{node.position:02d}")
        badge.setDefaultTextColor(QColor(PALETTE["primary"]))
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setPos(rect.left() + 12, rect.top() + 8)
        self.scene.addItem(badge)

        label = QGraphicsTextItem(node.name)
        label.setDefaultTextColor(QColor(PALETTE["text"]))
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        label.setTextWidth(rect.width() - 24)
        label.setPos(rect.left() + 12, rect.top() + 31)
        self.scene.addItem(label)

    def _add_edge(self, source: QRectF, target: QRectF) -> None:
        start = QPointF(source.right(), source.center().y())
        end = QPointF(target.left(), target.center().y())
        path = QPainterPath(start)
        midpoint = (start.x() + end.x()) / 2
        path.cubicTo(midpoint, start.y(), midpoint, end.y(), end.x() - 8, end.y())
        edge = QGraphicsPathItem(path)
        edge.setPen(QPen(QColor("#52625F"), 1.6))
        self.scene.addItem(edge)

        arrow = QGraphicsPolygonItem(
            QPolygonF(
                [
                    QPointF(end.x() - 9, end.y() - 4),
                    QPointF(end.x(), end.y()),
                    QPointF(end.x() - 9, end.y() + 4),
                ]
            )
        )
        arrow.setPen(QPen(QColor("#52625F"), 1))
        arrow.setBrush(QColor("#52625F"))
        self.scene.addItem(arrow)
