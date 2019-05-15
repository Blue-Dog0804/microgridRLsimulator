"""
This file defines a class MicrogridEnv that wraps the Simulator in this package, so that it follows the
OpenAI gym (https://github.com/openai/gym) format.

TODO:
    * verify observation_space
"""

import gym
import numpy as np
from gym import spaces
from gym.utils import seeding
from microgridRLsimulator.simulate import Simulator
from datetime import datetime
from datetime import timedelta
import pandas as pd

class MicrogridEnv(gym.Env):

    def __init__(self, start_date='2016-01-01 00:00:00', end_date='2017-07-31 23:55:00', data_file='elespino',
                 results_folder=None, results_file=None):
        """
        :param start_date: datetime for the start of the simulation
        :param end_date: datetime for the end of the simulation
        :param case: case name (string)
        :param results_folder: if None, set to default location
        :param results_file: if None, set to default file
        """

        self.simulator = Simulator(start_date,
                                   end_date,
                                   data_file,
                                   results_folder=results_folder,
                                   results_file=results_file)
        self.state = None
        self.action_space = spaces.Discrete(len(self.simulator.high_level_actions))

        # Observation space
        high = 1e3*np.ones(2 + len(self.simulator.grid.storages))
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)

        self.np_random = None
        self.seed()
        self.reset()

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def reset(self, state=None):
        if state is None:
            self.state = self.state_refactoring(self.simulator.reset())
        else:
            self.state = state
        return np.array(self.state)

    def step(self, action, state=None):
        """
        Step function, as in gym.
        May also accept a state as input (useful for MCTS, for instance).
        """
        assert self.action_space.contains(action), "%r (%s) invalid" % (action, type(action))

        if state is None:
            state = self.state
        state_formatted = self.state_formatting(state)
        next_state, reward, done = self.simulator.step(state_formatted, action)
        self.state = self.state_refactoring(next_state)

        print(self.state)

        return np.array(self.state), reward, done, {}

    def state_refactoring(self, state):
        """
        Convenience function that flattens the received state into an array

        :param state: State of the agent as a list
        :return: Flattened representation of the state as an array
        """
        time = state[-1]

        diff = time - self.simulator.start_date
        diff_minutes = diff.days*24*60 + diff.seconds/60

        state_array = np.concatenate((np.array([state[0]]), np.array(state[1]).reshape(-1), np.array([state[2]])),
                                     axis=0)
        state_array = np.hstack((state_array, diff_minutes))
        return state_array

    def state_formatting(self, state_array):
        """
        Inverse of state_refactoring
        """
        n = len(self.simulator.grid.storages)

        diff_minutes = state_array[-1]
        delta_t = timedelta(minutes=diff_minutes)
        time = pd.Timestamp(self.simulator.start_date + delta_t)

        state = [state_array[0],  state_array[1:1+n].tolist(),  state_array[-1], time]
        return state