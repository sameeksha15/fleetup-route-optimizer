"""DQN training and rollout for wave sequencing."""

from __future__ import annotations

import numpy as np
import torch
from stable_baselines3 import DQN
from stable_baselines3.common.env_util import make_vec_env

from .environment import FleetRouteEnv
from .routing import RoutingContext


def train_dqn(ctx: RoutingContext, waves: list[list[int]], timesteps: int, seed: int) -> DQN:
    vec_env = make_vec_env(lambda: FleetRouteEnv(ctx, waves), n_envs=1, seed=seed)
    model = DQN("MlpPolicy", vec_env, verbose=0, seed=seed)
    model.learn(total_timesteps=timesteps)
    return model


def sequence_waves_with_dqn(
    model: DQN, ctx: RoutingContext, waves: list[list[int]]
) -> list[list[int]]:
    """Greedy rollout: highest Q-value among currently deliverable stops."""
    env = FleetRouteEnv(ctx, waves)
    env.reset()
    sequences: list[list[int]] = [[] for _ in env.waves]
    terminated = not env.active
    while not terminated:
        obs = torch.as_tensor(env.observation(), device=model.device).unsqueeze(0)
        with torch.no_grad():
            q_values = model.q_net(obs).squeeze(0).cpu().numpy()
        masked = np.full_like(q_values, -np.inf)
        for node in env.active:
            masked[node - 1] = q_values[node - 1]
        node = int(np.argmax(masked)) + 1
        wave_index = env.wave_index
        _, _, terminated, _, _ = env.step(node - 1)
        sequences[wave_index].append(node)
    return sequences
