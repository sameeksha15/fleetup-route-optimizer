"""Gymnasium environment for wave-based single-truck routing.

The agent sequences deliveries inside each reload wave; wave membership and
reloads are fixed by :mod:`engine.waves`. Rewards are the negative marginal
cost under the shared :class:`~engine.costs.CostModel`, so the RL policy is
trained on exactly the objective the heuristic optimizes.

Observation: one entry per package (1 = deliverable now, i.e. unvisited and in
the current wave; 0 = otherwise) plus normalized time-of-day and remaining-day
fraction.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .costs import CostModel
from .routing import RoutingContext


class FleetRouteEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, ctx: RoutingContext, waves: list[list[int]]):
        super().__init__()
        self.ctx = ctx
        self.waves = [list(w) for w in waves if w]
        n = len(ctx.packages)
        self.action_space = spaces.Discrete(n)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(n + 2,), dtype=np.float32)
        self.reset()

    # -- Gymnasium API ---------------------------------------------------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.time = float(self.ctx.rules.shift_start_min)
        self.node = 0
        self.wave_index = 0
        self.active = set(self.waves[0]) if self.waves else set()
        return self.observation(), {}

    def step(self, action: int):
        node = int(action) + 1
        if node not in self.active:
            if not self.active:
                return self.observation(), 0.0, True, False, {}
            node = min(self.active, key=lambda n: self.ctx.travel_min[self.node][n])

        cost = self._travel_cost(self.node, node)
        arrival = self.time
        window = self.ctx.window(node)
        if arrival < window.start_min:
            waited = window.start_min - arrival
            cost += self.ctx.cost_model.waiting_weight * waited
            self.time = window.start_min
        elif arrival > window.end_min:
            cost += self.ctx.cost_model.lateness_cost(
                arrival - window.end_min, self.ctx.priority(node)
            )
        self.time += self.ctx.rules.service_time_min
        self.active.discard(node)

        terminated = False
        if not self.active:
            cost += self._travel_cost(self.node, 0)  # back to the depot
            self.wave_index += 1
            if self.wave_index < len(self.waves):
                cost += self.ctx.cost_model.trip_fixed_cost
                self.time += self.ctx.rules.reload_time_min
                self.active = set(self.waves[self.wave_index])
            else:
                overtime = max(0.0, self.time - self.ctx.rules.shift_end_min)
                cost += self.ctx.cost_model.overtime_weight * overtime
                terminated = True

        return self.observation(), -cost, terminated, False, {}

    # -- Helpers -----------------------------------------------------------

    def _travel_cost(self, src: int, dst: int) -> float:
        self.time += self.ctx.travel_min[src][dst]
        self.node = dst
        return (
            self.ctx.cost_model.drive_weight * self.ctx.travel_min[src][dst]
            + self.ctx.cost_model.fuel_weight * self.ctx.distance_km[src][dst]
        )

    def observation(self) -> np.ndarray:
        n = len(self.ctx.packages)
        obs = np.zeros(n + 2, dtype=np.float32)
        for node in self.active:
            obs[node - 1] = 1.0
        day_len = self.ctx.rules.shift_end_min - self.ctx.rules.shift_start_min
        elapsed = (self.time - self.ctx.rules.shift_start_min) / day_len
        obs[n] = float(np.clip(elapsed, 0.0, 1.0))
        obs[n + 1] = self.wave_index / max(len(self.waves), 1)
        return obs
