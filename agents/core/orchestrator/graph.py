from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    COMPLETE = "complete"
    FAILED   = "failed"

@dataclass
class GraphNode:
    node_id: str          # agent_id
    node_type: str        # agent_type
    status: NodeStatus
    parent_id: str | None
    children: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

class ExecutionGraph:
    """
    Tracks the agent execution tree for one pipeline run.
    Used for frontend ReactFlow visualization and Omium tracing.
    Stored in Redis as JSON. Not persisted to PostgreSQL.
    """

    def __init__(self, pipeline_id: str):
        self.pipeline_id = pipeline_id
        self.nodes: dict[str, GraphNode] = {}
        self.root_id: str | None = None

    def add_node(self, node_id: str, node_type: str,
                 parent_id: str | None = None,
                 metadata: dict | None = None) -> GraphNode:
        """Create GraphNode, add to self.nodes."""
        node = GraphNode(
            node_id=node_id,
            node_type=node_type,
            status=NodeStatus.PENDING,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        self.nodes[node_id] = node
        
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children.append(node_id)
            
        if self.root_id is None:
            self.root_id = node_id
            
        return node

    def update_node_status(self, node_id: str, status: NodeStatus) -> None:
        """Update node status."""
        if node_id in self.nodes:
            self.nodes[node_id].status = status
        else:
            logger.warning(f"Node {node_id} not found in graph for pipeline {self.pipeline_id}")

    def to_dict(self) -> dict:
        """Serialize graph to dict for Redis storage and WS broadcast."""
        return {
            "pipeline_id": self.pipeline_id,
            "root_id": self.root_id,
            "nodes": {
                node_id: {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "status": node.status.value,
                    "parent_id": node.parent_id,
                    "children": node.children,
                    "metadata": node.metadata
                }
                for node_id, node in self.nodes.items()
            }
        }

    async def save(self, redis_client) -> None:
        """Serialize and store in Redis."""
        # Note: redis_client is passed but we use our db.redis helper as requested
        from db.redis import set_state
        await set_state(f"pipeline:{self.pipeline_id}:graph", self.to_dict())

    @classmethod
    async def load(cls, pipeline_id: str, redis_client) -> "ExecutionGraph | None":
        """Load from Redis and reconstruct ExecutionGraph."""
        from db.redis import get_state
        data = await get_state(f"pipeline:{pipeline_id}:graph")
        if not data:
            return None
            
        graph = cls(pipeline_id)
        graph.root_id = data.get("root_id")
        
        for node_id, node_data in data.get("nodes", {}).items():
            graph.nodes[node_id] = GraphNode(
                node_id=node_data["node_id"],
                node_type=node_data["node_type"],
                status=NodeStatus(node_data["status"]),
                parent_id=node_data["parent_id"],
                children=node_data["children"],
                metadata=node_data["metadata"]
            )
            
        return graph
