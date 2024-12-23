import os
import gymnasium as gym
import numpy as np
import matplotlib.pyplot as plt
import pickle
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque
import random
from torch.utils.tensorboard import SummaryWriter

class DoubleDQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.99  # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.eval_model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()

    def _build_model(self):
        model = nn.Sequential(
            nn.Linear(self.state_size, 24),
            nn.ReLU(),
            nn.Linear(24, 24),
            nn.ReLU(),
            nn.Linear(24, self.action_size)
        )
        return model

    def update_target_model(self):
        self.target_model.load_state_dict(self.eval_model.state_dict())

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return np.random.randint(self.action_size)
        state = torch.tensor(state, dtype=torch.float).unsqueeze(0)
        act_values = self.eval_model(state)
        return torch.argmax(act_values).item()

    def replay(self, batch_size):
        if len(self.memory) < batch_size:
            return
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            state = torch.tensor(state, dtype=torch.float)
            next_state = torch.tensor(next_state, dtype=torch.float)
            target = self.eval_model(state).detach().clone()
            if done:
                target[action] = reward
            else:
                next_action = torch.argmax(self.eval_model(next_state)).item()
                target[action] = reward + self.gamma * self.target_model(next_state)[next_action].item()
            self.eval_model.zero_grad()
            criterion = nn.MSELoss()
            loss = criterion(self.eval_model(state), target)
            loss.backward()
            optimizer = torch.optim.Adam(self.eval_model.parameters(), lr=self.learning_rate)
            optimizer.step()
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

def run_ddqn(is_training=True, render=False):
    env = gym.make('CartPole-v1', render_mode='human' if render else None)
    state_size = env.observation_space.shape[0]
    action_size = env.action_space.n
    agent = DoubleDQNAgent(state_size, action_size)
    episodes = 1000
    batch_size = 32

    rewards_per_episode = []

    # Initialize TensorBoard writer
    writer = SummaryWriter(log_dir='./tensorboard_logs/ddqn')

    for e in range(episodes):
        state, _ = env.reset()
        total_reward = 0
        done = False
        while not done:
            action = agent.act(state)
            next_state, reward, done, truncated, _ = env.step(action)
            reward = reward if not done else -10
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward
            if done:
                rewards_per_episode.append(total_reward)
                mean_rewards = np.mean(rewards_per_episode[-100:])
                print(f"Episode {e}/{episodes}, Reward: {total_reward}, Mean Reward: {mean_rewards:.2f}, Epsilon: {agent.epsilon:.2f}")
                writer.add_scalar('Reward', total_reward, e)  # Log reward to TensorBoard
                break
        if is_training:
            agent.replay(batch_size)
        if e % 10 == 0:
            agent.update_target_model()
        if np.mean(rewards_per_episode[-100:]) > 195:
            print("Environment solved!")
            break

    writer.close()  # Close TensorBoard writer

    if is_training:
        with open('../Models/cartpole_double_dqn.pkl', 'wb') as f:
            pickle.dump(agent.eval_model.state_dict(), f)

    plt.plot(rewards_per_episode)
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.title('Double DQN Training Rewards')
    plt.savefig('../Results/cartpole_double_dqn.png')
    env.close()

if __name__ == '__main__':
    # Training phase for Double DQN
    # run_ddqn(is_training=True, render=False)

    # Testing phase for Double DQN
    run_ddqn(is_training=False, render=True)