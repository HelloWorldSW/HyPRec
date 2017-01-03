"""
A module that provides functionalities for grid search
will be used for hyperparameter optimization
"""

import sys
import os
import numpy
import itertools as it
from lib.evaluator import Evaluator


class GridSearch(object):

    def __init__(self, recommender, hyperparameters):
        """
        Train number of recommenders using UV decomposition
        using different parameters.
        @param (object) recommender
        @param (dict) hyperparameters, list of the hyperparameters
        """
        self.recommender = recommender
        self.hyperparameters = hyperparameters
        self.evaluator = Evaluator(recommender.get_ratings())

    def get_all_combinations(self):
        """
        the method retuns all possible combinations of the hyperparameters
        Example: hyperparameters = {'_lambda': [0, 0.1], 'n_factors': [20, 40]}
        Output: [{'n_factors': 20, '_lambda': 0}, {'n_factors': 40, '_lambda': 0},
        {'n_factors': 20, '_lambda': 0.1}, {'n_factors': 40, '_lambda': 0.1}]
        @returns (dict[]) array of dicts containing all combinations
        """
        names = sorted(self.hyperparameters)
        return [dict(zip(names, prod)) for prod in it.product(
            *(self.hyperparameters[name] for name in names))]

    def train(self):
        """
        The method loops on all  possible combinations of hyperparameters and calls
        the train and split method on the recommender. the train and test errors are
        saved and the hyperparameters that produced the best test error are returned
        """
        best_error = numpy.inf
        best_params = dict()
        train, test = self.recommender.split()
        for config in self.get_all_combinations():
            print("running config ")
            print(config)
            self.recommender.set_config(config)
            self.recommender.train()
            rounded_predictions = ALS.rounded_predictions()
            test_error = self.evaluator.calculate_recall(test, rounded_predictions)
            train_error = self.evaluator.calculate_recall(self.recommender.get_ratings(), rounded_predictions)
            print('Train error: %f, Test error: %f' % (train_error, test_error))
            if 1 - test_error < best_error:
                best_params = config
                best_error = 1 - test_error
            current_key = self.get_key(config)
            self.all_errors[current_key] = dict()
            self.all_errors[current_key]['train_error'] = train_error
            self.all_errors[current_key]['test_error'] = test_error
        return best_params

    def get_key(self, config):
        """
        Given a dict (config) the function generates a key that uniquely represents
        this config to be used to store all errors
        @param (dict) config given configuration
        @returns (str) string reperesenting the unique key of the configuration
        """
        generated_key = ''
        keys_array = sorted(config)
        print(config)
        for key in keys_array:
            print(key)
            print(config[key])
            generated_key += key + ':'
            generated_key += str(config[key]) + ','
        return generated_key.strip(',')

    def get_all_errors(self):
        """
        The method returns all errors calculated for every configuration.
        @returns (dict) containing every single computed test error.
        """
        return self.all_errors
