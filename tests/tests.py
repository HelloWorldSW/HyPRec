#!/usr/bin/env python
import json
import numpy
import os
import unittest
from lib.content_based import ContentBased
from lib.evaluator import Evaluator
from lib.recommender_system import RecommenderSystem
from util.data_parser import DataParser
from util.recommender_configuer import RecommenderConfiguration


class TestcaseBase(unittest.TestCase):
    def setUp(self):
        """
        Setup method that is called at the beginning of each test.
        """
        articles_cnt = 4
        users_cnt = 10

        def mock_process(self=None):
            pass

        def mock_get_abstracts(self=None):
            return {'1': 'hell world berlin dna evolution', '2': 'freiburg is green',
                    '3': 'the best dna is the dna of dinasours', '4': 'truth is absolute',
                    '5': 'berlin is not that green', '6': 'truth manifests',
                    '7': 'plato said truth is beautiful', '8': 'freiburg has dna'}

        def mock_get_ratings_matrix(self=None):
            return [[int(not bool((article + user) % 3)) for article in range(articles_cnt)]
                    for user in range(users_cnt)]

        self.abstracts = mock_get_abstracts()
        setattr(DataParser, "get_abstracts", mock_get_abstracts)
        setattr(DataParser, "process", mock_process)
        setattr(DataParser, "get_ratings_matrix", mock_get_ratings_matrix)


class TestRecommenderConfiguration(TestcaseBase):
    def runTest(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(os.path.dirname(base_dir), 'config/recommender.json')) as data_file:
            json_config = json.load(data_file)
        config = RecommenderConfiguration()
        self.assertEqual(config.get_content_based(), json_config['recommender']['content-based'])
        self.assertEqual(config.get_collaborative_filtering(), json_config['recommender']['collaborative-filtering'])
        self.assertEqual(config.get_error_metric(), json_config['recommender']['error-metric'])
        self.assertEqual(config.get_options(), json_config['recommender']['options'])
        self.assertEqual(config.get_hyperparameters(), json_config['recommender']['hyperparameters'])


class TestContentBased(TestcaseBase):
    def runTest(self):
        content_based = ContentBased(self.abstracts.values(), 5, 10)
        self.assertEqual(content_based.n_factors, 5)
        self.assertEqual(content_based.n_items, 8)
        content_based.train()
        self.assertEqual(content_based.get_word_distribution().shape, (8, 5))


class TestRecommenderSystem(TestcaseBase):
    def runTest(self):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(os.path.dirname(base_dir), 'config/recommender.json')) as data_file:
            json_config = json.load(data_file)
        rec_system = RecommenderSystem()
        self.assertEqual(rec_system.hyperparameters, json_config['recommender']['hyperparameters'])
        self.assertEqual(rec_system.config.config_dict, json_config['recommender'])
        self.assertTrue(isinstance(rec_system.evaluator, Evaluator))
        self.assertTrue(isinstance(rec_system.content_based, ContentBased))
        rec_system.content_based.n_factors = 5
        self.assertEqual(rec_system.content_based.n_items, 8)
        self.assertEqual(rec_system.content_based.n_factors, 5)
        rec_system.content_based.train()
        self.assertEqual(rec_system.content_based.get_word_distribution().shape, (8, 5))
