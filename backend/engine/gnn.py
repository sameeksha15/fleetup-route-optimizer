"""Graph neural network over the stop graph.

A two-layer GCN embeds each stop from its coordinates and the traffic-aware
travel-time graph. The resulting visit-order suggestion is recorded with each
run for comparison against the planner's output.

Note: training currently uses each node's own index as its label, so the
network learns embeddings rather than a meaningful tour; making this
prediction target route-quality-aware is planned as a follow-up redesign.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv
from torch_geometric.utils import from_networkx

from .entities import Stop


class StopGraphGCN(nn.Module):
    def __init__(self, in_feats: int, hidden_feats: int, out_feats: int):
        super().__init__()
        self.conv1 = GCNConv(in_feats, hidden_feats)
        self.conv2 = GCNConv(hidden_feats, out_feats)

    def forward(self, data):
        x = torch.relu(self.conv1(data.x, data.edge_index))
        return self.conv2(x, data.edge_index)


def suggest_visit_order(
    stops: list[Stop],
    travel_times: np.ndarray,
    hidden_feats: int = 16,
    epochs: int = 50,
    lr: float = 0.005,
    seed: int = 42,
) -> list[int]:
    """Train the GCN on the stop graph and return its per-node predictions."""
    torch.manual_seed(seed)
    n = len(stops)

    graph = nx.DiGraph()
    for i, stop in enumerate(stops):
        graph.add_node(i, pos=(stop.latitude, stop.longitude))
    for i in range(n):
        for j in range(n):
            if i != j:
                graph.add_edge(i, j, weight=float(travel_times[i][j]))

    data = from_networkx(graph)
    data.x = torch.tensor([[s.latitude, s.longitude] for s in stops], dtype=torch.float32)

    model = StopGraphGCN(in_feats=2, hidden_feats=hidden_feats, out_feats=n)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    labels = torch.arange(n, dtype=torch.long)

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = criterion(model(data), labels)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        return torch.argmax(model(data), dim=1).tolist()
