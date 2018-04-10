from .base import Model, InputData, AbstractEstimator
from .base import Model as NegativeBinomialWithLinearBiasModel  # Alias for Model
from .base import InputData as NegativeBinomialWithLinearBiasInputData  # Alias for InputData

from .simulator import Simulator
from .simulator import Simulator as NegativeBinomialWithLinearBiasSimulator  # Alias for Simulator

# from .estimator import Estimator
# from .estimator import Estimator as NegativeBinomialWithLinearBiasEstimator

__all__ = ['NegativeBinomialWithLinearBiasSimulator',
           'NegativeBinomialWithLinearBiasInputData',
           'NegativeBinomialWithLinearBiasModel',
           # 'NegativeBinomialWithLinearBiasEstimator'
           ]
