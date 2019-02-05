import abc
import logging
from typing import Union

import tensorflow as tf
import numpy as np

from .external import AbstractEstimator, ProcessModelBase

logger = logging.getLogger(__name__)

ESTIMATOR_PARAMS = AbstractEstimator.param_shapes().copy()
ESTIMATOR_PARAMS.update({
    "batch_probs": ("batch_observations", "features"),
    "batch_log_probs": ("batch_observations", "features"),
    "batch_log_likelihood": (),
    "full_loss": (),
    "full_gradient": ("features",),
})


class ProcessModelGLM(ProcessModelBase):

    @abc.abstractmethod
    def param_bounds(self, dtype: str):
        pass


class ModelVarsGLM(ProcessModelGLM):
    """ Build tf.Variables to be optimzed and their constraints.

    a_var and b_var slices of the tf.Variable params which contains
    all parameters to be optimized during model estimation.
    Params is defined across both location and scale model so that 
    the hessian can be computed for the entire model.
    a and b are the clipped parameter values which also contain
    constraints and constrained dependent coefficients which are not
    directly optimized.
    """

    a: tf.Tensor
    b: tf.Tensor
    a_var: tf.Variable
    b_var: tf.Variable
    params: tf.Variable
    converged: np.ndarray

    def __init__(
            self,
            dtype: str,
            init_a: np.ndarray,
            init_b: np.ndarray,
            constraints_loc: tf.Tensor,
            constraints_scale: tf.Tensor
    ):
        """

        :param dtype: Precision used in tensorflow.
        :param init_a: nd.array (mean model size x features)
            Initialisation for all parameters of mean model.
        :param init_b: nd.array (dispersion model size x features)
            Initialisation for all parameters of dispersion model.
        :param constraints_loc: tensor (all parameters x dependent parameters)
            Tensor that encodes how complete parameter set which includes dependent
            parameters arises from indepedent parameters: all = <constraints, indep>.
            This tensor describes this relation for the mean model.
            This form of constraints is used in vector generalized linear models (VGLMs).
        :param constraints_scale: tensor (all parameters x dependent parameters)
            Tensor that encodes how complete parameter set which includes dependent
            parameters arises from indepedent parameters: all = <constraints, indep>.
            This tensor describes this relation for the dispersion model.
            This form of constraints is used in vector generalized linear models (VGLMs).
        """
        self.init_a = tf.convert_to_tensor(init_a, dtype=dtype)
        self.init_b = tf.convert_to_tensor(init_b, dtype=dtype)

        init_a_clipped = self.tf_clip_param(self.init_a, "a_var")
        init_b_clipped = self.tf_clip_param(self.init_b, "b_var")

        # Param is the only tf.Variable in the graph.
        # a_var and b_var have to be slices of params.
        self.params = tf.Variable(tf.concat(
            [
                init_a_clipped,
                init_b_clipped,
            ],
            axis=0
        ), name="params")

        # Feature batching code for future:
        #idx_featurebatch = tf.random_uniform([100], minval=0, maxval=self.params.shape[1]-1, dtype=tf.int32)
        #params_featurebatch = tf.gather(self.params, indi [:,idx_featurebatch]

        #params_by_gene = [tf.expand_dims(params[:, i], axis=-1) for i in range(params.shape[1])]
        #a_by_gene = [x[0:init_a.shape[0],:] for x in params_by_gene]
        #b_by_gene = [x[init_a.shape[0]:, :] for x in params_by_gene]
        #a_var = tf.concat(a_by_gene, axis=1)
        #b_var = tf.concat(b_by_gene, axis=1)
        a_var = self.params[0:init_a.shape[0]]
        b_var = self.params[init_a.shape[0]:]

        self.a_var = self.tf_clip_param(a_var, "a_var")
        self.b_var = self.tf_clip_param(b_var, "b_var")

        if constraints_loc is not None:
            self.a = tf.matmul(constraints_loc,  self.a_var)
        else:
            self.a = self.a_var

        if constraints_scale is not None:
            self.b = tf.matmul(constraints_scale,  self.b_var)
        else:
            self.b = self.b_var

        # Properties to follow gene-wise convergence.
        self.converged = np.repeat(a=False, repeats=self.params.shape[1])  # Initialise to non-converged.
        self.updated_a = tf.Variable(np.repeat(a=True, repeats=self.params.shape[1]))  # Initialise to is updated.
        self.updated_b = tf.Variable(np.repeat(a=True, repeats=self.params.shape[1]))  # Initialise to is updated.
        self.updated = tf.logical_not(tf.logical_or(self.updated_a, self.updated_b))
        #self.params_by_gene = params_by_gene
        #self.a_by_gene = a_by_gene
        #self.b_by_gene = b_by_gene

        self.dtype = dtype
        self.constraints_loc = constraints_loc
        self.constraints_scale = constraints_scale
        self.n_features = self.params.shape[1]
        self.idx_train_loc = np.arange(0, init_a.shape[0])
        self.idx_train_scale = np.arange(init_a.shape[0], init_a.shape[0]+init_b.shape[0])

    @abc.abstractmethod
    def param_bounds(self, dtype):
        pass


class BasicModelGraphGLM(ProcessModelGLM):
    """

    """
    X: Union[tf.Tensor, tf.SparseTensor]
    design_loc: tf.Tensor
    design_scale: tf.Tensor
    constraints_loc: tf.Tensor
    constraints_scale: tf.Tensor

    probs: tf.Tensor
    log_likelihood: tf.Tensor
    norm_log_likelihood: tf.Tensor
    norm_neg_log_likelihood: tf.Tensor
    loss: tf.Tensor

    def __init__(
            self,
            X,
            design_loc: tf.Tensor,
            design_scale: tf.Tensor,
            constraints_loc: tf.Tensor,
            constraints_scale: tf.Tensor,
            a_var: Union[tf.Variable, tf.Tensor],
            b_var: Union[tf.Variable, tf.Tensor],
            dtype: str,
            size_factors: Union[None, tf.Tensor] = None
    ):
        """

        :param X: tensor (observations x features)
            The input data.
        :param design_loc: Some matrix format (observations x mean model parameters)
            The location design model. Optional if already specified in `data`
        :param design_scale: Some matrix format (observations x dispersion model parameters)
            The scale design model. Optional if already specified in `data`
        :param constraints_loc: tensor (all parameters x dependent parameters)
            Tensor that encodes how complete parameter set which includes dependent
            parameters arises from indepedent parameters: all = <constraints, indep>.
            This tensor describes this relation for the mean model.
            This form of constraints is used in vector generalized linear models (VGLMs).
        :param constraints_scale: tensor (all parameters x dependent parameters)
            Tensor that encodes how complete parameter set which includes dependent
            parameters arises from indepedent parameters: all = <constraints, indep>.
            This tensor describes this relation for the dispersion model.
            This form of constraints is used in vector generalized linear models (VGLMs).
        :param a_var: tf.Variable or tensor (mean model size x features)
            Mean model variables.
        :param b_var: tf.Variable or tensor (dispersion model size x features)
            Dispersion model variables.
        :param dtype: Precision used in tensorflow.
        :param size_factors: tensor (observations x features)
            Constant scaling factors for mean model, such as library size factors.
        """
        a_var = self.tf_clip_param(a_var, "a_var")
        b_var = self.tf_clip_param(b_var, "a_var")

        if constraints_loc is not None:
            eta_loc = tf.matmul(design_loc, tf.matmul(constraints_loc, a_var))
        else:
            eta_loc = tf.matmul(design_loc, a_var)

        if size_factors is not None:
            eta_loc = tf.add(eta_loc, size_factors)

        eta_loc = self.tf_clip_param(eta_loc, "eta_loc")

        if constraints_loc is not None:
            eta_scale = tf.matmul(design_scale, tf.matmul(constraints_scale, b_var))
        else:
            eta_scale = tf.matmul(design_scale, b_var)

        eta_scale = self.tf_clip_param(eta_scale, "eta_scale")

        self.X = X
        self.design_loc = design_loc
        self.design_scale = design_scale
        self.constraints_loc = constraints_loc
        self.constraints_scale = constraints_scale
        self.a_var = a_var
        self.b_var = b_var
        self.size_factors = size_factors
        self.dtype = dtype

        self.eta_loc = eta_loc
        self.eta_scale = eta_scale

    @property
    def probs(self):
        probs = tf.exp(self.log_probs)
        return self.tf_clip_param(probs, "probs")

    @property
    def log_likelihood(self):
        return tf.reduce_sum(self.log_probs, axis=0, name="log_likelihood")

    @property
    def norm_log_likelihood(self):
        return tf.reduce_mean(self.log_probs, axis=0, name="log_likelihood")

    @property
    def norm_neg_log_likelihood(self):
        return - self.norm_log_likelihood

    @property
    def loss(self):
        return tf.reduce_sum(self.norm_neg_log_likelihood)

    @abc.abstractmethod
    def param_bounds(self, dtype):
        pass
