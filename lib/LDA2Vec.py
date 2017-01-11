#!/usr/bin/env python
"""
A module that contains the content-based recommender LDA2VecRecommender that
uses the LDA2Vec library.
"""
import chainer
import numpy
from chainer import optimizers
from lib.lda2vec_model import LDA2Vec
from lib.content_based import ContentBased


class LDA2VecRecommender(ContentBased):
    """
    LDA2Vec recommender, a content based recommender that uses LDA2Vec.
    """
    def __init__(self, abstracts_preprocessor, evaluator, config, verbose=False):
        """
        Constructor of ContentBased processor.

        :param AbstractsProprocessor abstracts_preprocessor: Abstracts preprocessor
        :param Evaluator evaluator: An evaluator object.
        :param dict config: A dictionary of the hyperparameters.
        :param boolean verbose: A flag for printing while computing.
        """
        super(LDA2VecRecommender, self).__init__(abstracts_preprocessor, evaluator, config, verbose)

    def train(self, n_iter=5):
        """
        Train the LDA2Vec model, and store the document_distribution matrix.

        :param int n_iter: The number of iterations of training the model.
        """
        n_units = self.abstracts_preprocessor.get_num_units()
        # 2 lists which correspond to pairs ('doc_id', 'word_id') of all the words
        # in each document, 'word_id' according to the computed dictionary 'vocab'
        doc_ids, flattened = zip(*self.abstracts_preprocessor.get_article_to_words())
        flattened = numpy.array(flattened, dtype='int32')
        doc_ids = numpy.array(doc_ids, dtype='int32')

        # Word frequencies, for lda2vec_model
        n_vocab = self.abstracts_preprocessor.get_num_vocab()
        term_frequency = self.abstracts_preprocessor.get_term_frequencies()
        if self._v:
            print('...')
            print(list(filter(lambda x: x[1] != 0, zip(range(len(term_frequency)), term_frequency))))
            print(list(zip(list(doc_ids), list(flattened))))
            print('...')

        # Assuming that doc_ids are in the set {0, 1, ..., n - 1}
        assert doc_ids.max() + 1 == self.n_items
        if self._v:
            print(self.n_items, self.n_factors, n_units, n_vocab)
        # Initialize lda2vec model
        lda2v_model = LDA2Vec(n_documents=self.n_items, n_document_topics=self.n_factors,
                              n_units=n_units, n_vocab=n_vocab, counts=term_frequency)
        if self._v:
            print("Initialize LDA2Vec model..., Training LDA2Vec...")

        # Initialize optimizers
        optimizer = optimizers.Adam()
        optimizer.setup(lda2v_model)
        clip = chainer.optimizer.GradientClipping(5.0)
        optimizer.add_hook(clip)

        if self._v:
            print("Optimizer Initialized...")
        iterations = 0
        for epoch in range(n_iter):
            optimizer.zero_grads()
            # TODO(mostafa-mahmoud): Check how to batch (doc_ids, flattened)
            l = lda2v_model.fit_partial(doc_ids.copy(), flattened.copy())
            prior = lda2v_model.prior()
            loss = prior
            loss.backward()
            optimizer.update()
            if self._v:
                msg = ("IT:{it:05d} E:{epoch:05d} L:{loss:1.3e} P:{prior:1.3e}")
                logs = dict(loss=float(l), epoch=epoch, it=iterations, prior=float(prior.data))
                print(msg.format(**logs))
            iterations += 1

        # Get document distribution matrix.
        self.document_distribution = lda2v_model.mixture.proportions(numpy.unique(doc_ids), True).data
        if self._v:
            print("LDA2Vec trained...")


    def set_config(self, config):
        """
        set the hyperparamenters of the algorithm.

        :param dict config: A dictionary of the hyperparameters.
        """
        super(LDA2VecRecommender, self).set_config(config)

    def get_document_topic_distribution(self):
        """
        Get the matrix of document X topics distribution.

        :returns: A matrix of documents X topics distribution.
        :rtype: ndarray
        """
        return self.document_distribution
