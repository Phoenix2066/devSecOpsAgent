def build_execution_graph(pipeline_id: str, workers: list[str]) -> dict:
    nodes = [{"id": "orchestrator", "type": "orchestrator"}]
    nodes.extend({"id": worker, "type": worker} for worker in workers)
    edges = [{"source": "orchestrator", "target": worker} for worker in workers]
    return {"pipeline_id": pipeline_id, "nodes": nodes, "edges": edges}
