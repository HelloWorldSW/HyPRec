#!/usr/bin/env python3
"""
A module to run different recommenders.
"""
import numpy
import sys
from optparse import OptionParser
from lib.evaluator import Evaluator
from lib.collaborative_filtering import CollaborativeFiltering
from lib.grid_search import GridSearch
from lib.LDA import LDARecommender
from lib.LDA2Vec import LDA2VecRecommender
from lib.recommender_system import RecommenderSystem
from util.data_parser import DataParser
from util.recommender_configuer import RecommenderConfiguration


class RunnableRecommenders(object):
    """
    A class that is used to run recommenders.
    """
    def __init__(self, use_database=True, config=None):
        """
        Setup the data and configuration for the recommenders.
        """
        if use_database:
            self.abstracts = DataParser.get_abstracts().values()
            self.ratings = numpy.array(DataParser.get_ratings_matrix())
            self.documents, self.users = self.ratings.shape
        else:
            self.documents, self.users = 8, 10
            self.abstracts = ({'1': 'hell world berlin dna evolution', '2': 'freiburg is green',
                               '3': 'the best dna is the dna of dinasours', '4': 'truth is absolute',
                               '5': 'berlin is not that green', '6': 'truth manifests itself',
                               '7': 'plato said truth is beautiful', '8': 'freiburg has dna'}).values()
            self.ratings = numpy.array([[int(not bool((article + user) % 3))
                                         for article in range(self.documents)]
                                        for user in range(self.users)])

        self.evaluator = Evaluator(self.ratings, self.abstracts)
        if not config:
            self.config = RecommenderConfiguration()
        else:
            self.config = config
        self.hyperparameters = self.config.get_hyperparameters()
        self.n_iterations = self.config.get_options()['n_iterations']

    def run_lda(self):
        """
        Run LDA recommender.
        """
        lda_recommender = LDARecommender(self.abstracts, self.evaluator, self.hyperparameters)
        lda_recommender.train(self.n_iterations)
        return lda_recommender.get_document_topic_distribution()

    def run_lda2vec(self):
        """
        Runs LDA2Vec recommender.
        """
        lda2vec_recommender = LDA2VecRecommender(self.abstracts, self.evaluator, self.hyperparameters, True)
        lda2vec_recommender.train(self.n_iterations)
        print(lda2vec_recommender.get_document_topic_distribution().shape)
        return lda2vec_recommender.get_document_topic_distribution()

    def run_collaborative(self):
        """
        Runs ccollaborative filtering
        """
        ALS = CollaborativeFiltering(self.ratings, self.evaluator, self.config.get_hyperparameters(), True)
        train, test = ALS.split()
        ALS.train()
        print(ALS.evaluator.calculate_recall(ALS.ratings, ALS.rounded_predictions()))
        return ALS.evaluator.recall_at_x(50, ALS.get_predictions())

    def run_grid_search(self):
        """
        runs grid search
        """
        hyperparameters = {
            '_lambda': [0, 0.01, 0.1, 0.5, 10, 100],
            'n_factors': [20, 40, 100, 200, 300]
        }
        print(type(self.ratings))
        ALS = CollaborativeFiltering(self.ratings, self.evaluator, self.config.get_hyperparameters(), True)
        GS = GridSearch(ALS, hyperparameters)
        best_params = GS.train()
        return best_params

    def run_recommender(self):
        recommender = RecommenderSystem(abstracts=self.abstracts, ratings=self.ratings, verbose=True)
        error = recommender.train()
        print(recommender.content_based.get_document_topic_distribution().shape)
        return error

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--use-database", dest="db", action='store_true',
                  help="use database to run the recommender", metavar="DB")
    options, args = parser.parse_args()
    use_database = options.db != None
    runnable = RunnableRecommenders(use_database)
    found_runnable = False
    for arg in args:
        if arg == 'recommender':
            print(runnable.run_recommender())
            found_runnable = True
        elif arg == 'collaborative':
            print(runnable.run_collaborative())
            found_runnable = True
        elif arg == 'grid_search':
            print(runnable.run_grid_search())
            found_runnable = True
        elif arg == 'lda':
            print(runnable.run_lda())
            found_runnable = True
        elif arg == 'lda2vec':
            print(runnable.run_lda2vec())
            found_runnable = True
        else:
            print("'%s' option is not valid, please use one of ['recommender', 'collaborative', 'grid_search', 'lda', 'lda2vec']" % arg)
    if found_runnable == False:
        print("Didn't find any valid option, running recommender instead.")
        print(runnable.run_recommender())
