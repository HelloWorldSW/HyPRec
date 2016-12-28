#!/usr/bin/env python
"""
This module provides the functionalities of content-based analysis of the tests.
"""
import numpy


class ContentBased(object):
    """
    An abstract class that will take the parsed data, and returns a distribution of the content-based information.
    """
    def __init__(self, abstracts, n_factors, n_iterations=5):
        """
        Constructor of ContentBased processor.
        """
        self.n_factors = n_factors
        self.n_items = len(abstracts)
        self.abstracts = abstracts
        self.n_iterations = n_iterations

    def train(self):
        """
        Train the content-based.
        """
        self.word_distribution = numpy.random.random((self.n_items, self.n_factors))
        for _ in range(self.n_iterations):
            pass

    def get_word_distribution(self):
        """
        @returns A matrix of the words x topics distribution.
        """
        return self.word_distribution
