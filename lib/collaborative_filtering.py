#!/usr/bin/env python
"""
Module that provides the main functionalities of collaborative filtering.
"""

import numpy
import random
from numpy.linalg import solve

from lib.abstract_recommender import AbstractRecommender


class CollaborativeFiltering(AbstractRecommender):
    """
    A class that takes in the rating matrix and outputs user and item
    representation in latent space.
    """
    def __init__(self, initializer, evaluator, hyperparameters, options,
                 verbose=False, load_matrices=True, dump_matrices=True, train_more=True):
        """
        Train a matrix factorization model to predict empty
        entries in a matrix. The terminology assumes a ratings matrix which is ~ user x item

        :param ModelInitializer initializer: A model initializer.
        :param Evaluator evaluator: Evaluator of the recommender and holder of the input data.
        :param dict hyperparameters: hyperparameters of the recommender, contains _lambda and n_factors
        :param dict options: Dictionary of the run options.
        :param boolean verbose: A flag if True, tracing will be printed
        :param boolean load_matrices: A flag for reinitializing the matrices.
        :param boolean dump_matrices: A flag for saving the matrices.
        :param boolean train_more: train_more the collaborative filtering after loading matrices.
        """
        # setting input
        self.initializer = initializer
        self.evaluator = evaluator
        self.ratings = evaluator.ratings
        self.n_users, self.n_items = self.ratings.shape
        self.k_folds = None
        self.set_hyperparameters(hyperparameters)
        self.set_options(options)
        # setting flags
        self._verbose = verbose
        self._load_matrices = load_matrices
        self._dump_matrices = dump_matrices
        self._train_more = train_more
        # splitting input
        self.test_indices = {}
        self.naive_split()
        self.fold_train_indices, self.fold_test_indices = self.get_kfold_indices()

    # @overrides(AbstractRecommender)
    def set_options(self, options):
        """
        Set the options of the recommender. Namely n_iterations and k_folds.
        
        :param dict options: A dictionary of the options.
        """
        if 'n_iterations' in options.keys():
            self.n_iter = options['n_iterations']
        if 'k_folds' in options.keys():
            self.k_folds = options['k_folds']
        elif self.k_folds is None:
            self.k_folds = 5
        self.options = options

    # @overrides(AbstractRecommender)
    def set_hyperparameters(self, hyperparameters):
        """
        The function sets the hyperparameters of the uv_decomposition algorithm

        :param dict hyperparameters: hyperparameters of the recommender, contains _lambda and n_factors
        """
        self.n_factors = hyperparameters['n_factors']
        self._lambda = hyperparameters['_lambda']
        self.hyperparameters = hyperparameters

    def naive_split(self, test_percentage=0.2, docs=False):
        """
        Split the ratings into test and train data.

        :param float test_percentage: The ratio of the testing data from all the data.
        :returns: a tuple of train and test data.
        :rtype: tuple
        """
        shape_index = 0
        if docs is True:
            shape_index = 1
        test = numpy.zeros(self.ratings.shape)
        train = self.ratings.copy()
        for user in range(self.ratings.shape[shape_index]):
            non_zeros = self.ratings[user, :].nonzero()[0]
            test_ratings = numpy.random.choice(non_zeros,
                                               size=int(test_percentage * len(non_zeros)))
            train[user, test_ratings] = 0.
            test[user, test_ratings] = self.ratings[user, test_ratings]
            self.test_indices[str(user)] = test_ratings
        assert(numpy.all((train * test) == 0))
        self.train_data = train
        self.test_data = test
        return train, test

    def get_kfold_indices(self):
        """
        returns the indices for rating matrix for each kfold split. Where each test set
        contains ~1/k of the total items a user has in their digital library.

        :returns: a list of all indices of the training set and test set.
        :rtype: list of lists
        """
        train_indices = []
        test_indices = []

        for user in range(self.ratings.shape[0]):

            # Indices for all items in the rating matrix.
            item_indices = numpy.arange(self.ratings.shape[1])

            # Indices of all items in user's digital library.
            rated_items_indices = self.ratings[user].nonzero()[0]
            mask = numpy.ones(len(self.ratings[user]), dtype=bool)
            mask[[rated_items_indices]] = False
            # Indices of all items not in user's digital library.
            non_rated_indices = item_indices[mask]

            # Shuffle all rated items indices
            numpy.random.shuffle(rated_items_indices)

            # Size of 1/k of the total user's ratings
            size_of_test = round((1/self.k_folds) * len(rated_items_indices))

            # 2d List that stores all the indices of each test set for each fold.
            test_ratings = [[] for x in range(self.k_folds)]

            counter = 0
            numpy.random.shuffle(non_rated_indices)
            # List that stores the number of indices to be added to each test set.
            num_to_add = []

            # create k different folds for each user.
            for index in range(self.k_folds):
                if index == self.k_folds - 1:
                    test_ratings[index] = numpy.array(rated_items_indices[counter:len(rated_items_indices)])
                else:
                    test_ratings[index] = numpy.array(rated_items_indices[counter:counter + size_of_test])
                counter += size_of_test

                # adding unique zero ratings to each test set
                num_to_add.append(int((self.ratings.shape[1] / self.k_folds) - len(test_ratings[index])))
                if index > 0 and num_to_add[index] != num_to_add[index - 1]:
                    addition = non_rated_indices[index * (num_to_add[index - 1]):
                                                         (num_to_add[index - 1] * index) + num_to_add[index]]
                else:
                    addition = non_rated_indices[index * (num_to_add[index]):num_to_add[index] * (index + 1)]

                test_ratings[index] = numpy.append(test_ratings[index], addition)
                test_indices.append(test_ratings[index])

                # for each user calculate the training set for each fold.
                train_index = rated_items_indices[~numpy.in1d(rated_items_indices, test_ratings[index])]
                mask = numpy.ones(len(self.ratings[user]), dtype=bool)
                mask[[numpy.append(test_ratings[index], train_index)]] = False

                train_ratings = numpy.append(train_index, item_indices[mask])
                train_indices.append(train_ratings)

        return train_indices, test_indices

    def generate_kfold_matrix(self, train_indices, test_indices):
        """
        Returns a training set and a training set matrix for one fold.
        This method is to be used in conjunction with get_kfold_indices()

        :param int[] train_indices array of train set indices.
        :param int[] test_indices array of test set indices.
        :returns: Training set matrix and Test set matrix.
        :rtype: 2-tuple of 2d numpy arrays
        """
        train_matrix = numpy.zeros(self.ratings.shape)
        test_matrix = numpy.zeros(self.ratings.shape)
        for user in range(train_matrix.shape[0]):
            train_matrix[user, train_indices[user]] = self.ratings[user, train_indices[user]]
            test_matrix[user, test_indices[user]] = self.ratings[user, test_indices[user]]
        return train_matrix, test_matrix

    def get_fold(self, fold_num):
        """
        Returns train and test data for a given fold number

        :param int fold_num the fold index to be returned
        :returns: tuple of training and test data
        :rtype: 2-tuple of 2d numpy arrays
        """
        current_train_fold_indices = []
        current_test_fold_indices = []
        index = fold_num - 1
        ctr = 0
        while ctr < self.ratings.shape[0]:
            current_train_fold_indices.append(self.fold_train_indices[index])
            current_test_fold_indices.append(self.fold_test_indices[index])
            index += self.k_folds
            ctr += 1
        return self.generate_kfold_matrix(current_train_fold_indices, current_test_fold_indices)

    def als_step(self, latent_vectors, fixed_vecs, ratings, _lambda, type='user'):
        """
        The function computes only one step in the ALS algorithm

        :param ndarray latent_vectors: the vector to be optimized
        :param ndarray fixed_vecs: the vector to be fixed
        :param ndarray ratings: ratings that will be used to optimize latent * fixed
        :param float _lambda: reguralization parameter
        :param str type: either user or item.
        """
        if type == 'user':
            # Precompute
            YTY = fixed_vecs.T.dot(fixed_vecs)
            lambdaI = numpy.eye(YTY.shape[0]) * _lambda

            for u in range(latent_vectors.shape[0]):
                latent_vectors[u, :] = solve((YTY + lambdaI),
                                             ratings[u, :].dot(fixed_vecs))
        elif type == 'item':
            # Precompute
            XTX = fixed_vecs.T.dot(fixed_vecs)
            lambdaI = numpy.eye(XTX.shape[0]) * _lambda
            for i in range(latent_vectors.shape[0]):
                latent_vectors[i, :] = solve((XTX + lambdaI),
                                             ratings[:, i].T.dot(fixed_vecs))
        return latent_vectors

    # @overrides(AbstractRecommender)
    def train(self, item_vecs=None):
        """
        Train model for n_iter iterations from scratch.
        """
        matrices_found = False
        if self._load_matrices is False:
            self.user_vecs = numpy.random.random((self.n_users, self.n_factors))
            if item_vecs is None:
                self.item_vecs = numpy.random.random((self.n_items, self.n_factors))
            else:
                self.item_vecs = item_vecs
        else:
            users_found, self.user_vecs = self.initializer.load_matrix(self.hyperparameters,
                                                                       'user_vecs', (self.n_users, self.n_factors))
            if self._verbose and users_found:
                print("User distributions files were found.")
            if item_vecs is None:
                items_found, self.item_vecs = self.initializer.load_matrix(self.hyperparameters, 'item_vecs',
                                                                           (self.n_items, self.n_factors))
                if self._verbose and items_found:
                    print("Document distributions files were found.")
            else:
                items_found = True
                self.item_vecs = item_vecs
            matrices_found = users_found and items_found
        if not matrices_found:
            if self._verbose and self._load_matrices:
                print("User and Document distributions files were not found, will train collaborative.")
            self.partial_train()
        else:
            if self._train_more:
                if self._verbose and self._load_matrices:
                    print("User and Document distributions files found, will train model further.")
                self.partial_train()
            else:
                if self._verbose and self._load_matrices:
                    print("User and Document distributions files found, will not train the model further.")

        if self._dump_matrices:
            self.initializer.set_config(self.hyperparameters, self.n_iter)
            self.initializer.save_matrix(self.user_vecs, 'user_vecs')
            self.initializer.save_matrix(self.item_vecs, 'item_vecs')
        if self._verbose:
            predictions = self.get_predictions()
            rounded_predictions = self.rounded_predictions()
            self.evaluator.load_top_recommendations(200, predictions)
            train_recall = self.evaluator.calculate_recall(self.train_data, rounded_predictions)
            test_recall = self.evaluator.calculate_recall(self.test_data, rounded_predictions)
            recall_at_x = self.evaluator.recall_at_x(200, predictions)
            recommendations = sum(sum(rounded_predictions))
            likes = sum(sum(self.ratings))
            ratio = recommendations / likes
            mrr_at_five = self.evaluator.calculate_mrr(5, predictions)
            ndcg_at_five = self.evaluator.calculate_ndcg(5, predictions)
            mrr_at_ten = self.evaluator.calculate_mrr(10, predictions)
            ndcg_at_ten = self.evaluator.calculate_ndcg(10, predictions)
            print('Final Error %f, train recall %f, test recall %f, recall at 200 %f, ratio %f, mrr @5 %f, ndcg @5 %f, mrr @10 %f,\
                   ndcg @10 %f' % (self.evaluator.get_rmse(predictions, self.ratings), train_recall,
                                   test_recall, recall_at_x, ratio, mrr_at_five, ndcg_at_five,
                                   mrr_at_ten, ndcg_at_ten))

    def partial_train(self):
        """
        Train model for n_iter iterations. Can be called multiple times for further training.
        """
        for ctr in range(1, self.n_iter + 1):
            if self._verbose:
                print('\tcurrent iteration: {}'.format(ctr))
                print('Error %f' % self.evaluator.get_rmse(self.user_vecs.dot(self.item_vecs.T), self.ratings))
            self.user_vecs = self.als_step(self.user_vecs, self.item_vecs, self.train_data, self._lambda, type='user')
            self.item_vecs = self.als_step(self.item_vecs, self.user_vecs, self.train_data, self._lambda, type='item')

    # @overrides(AbstractRecommender)
    def get_predictions(self):
        """
        Predict ratings for every user and item.

        :returns: predictions
        :rtype: ndarray
        """
        return self.user_vecs.dot(self.item_vecs.T)

    # @overrides(AbstractRecommender)
    def predict(self, user, item):
        """
        Single user and item prediction.

        :returns: prediction score
        :rtype: float
        """
        return self.user_vecs[user, :].dot(self.item_vecs[item, :].T)
