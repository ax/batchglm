.. automodule:: batchglm.api

API
===


Import batchglm's high-level API as::

   import batchglm.api as glm

Preprocessing
~~~~~~~~~~~~~~~~~~~

:mod:`batchglm.api.data` simplifies loading of mtx files and generating design matrices

.. For visual quality control, see :func:`~scanpy.api.pl.highest_expr_gens` and
.. :func:`~scanpy.api.pl.filter_genes_dispersion` in the :doc:`plotting API <plotting>`.

.. autosummary::
   :toctree: .

   data.design_matrix
   data.design_matrix_from_xarray
   data.design_matrix_from_anndata
   data.sample_description_from_xarray
   data.sample_description_from_anndata
   data.load_mtx_to_adata
   data.load_mtx_to_xarray
   data.load_recursive_mtx

   models.BasicInputData
   models.BasicModel
   models.BasicEstimator
   models.BasicSimulator