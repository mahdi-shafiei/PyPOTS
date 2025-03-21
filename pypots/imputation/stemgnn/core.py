"""
The core wrapper assembles the submodules of StemGNN imputation model
and takes over the forward progress of the algorithm.
"""

# Created by Wenjie Du <wenjay.du@gmail.com>
# License: BSD-3-Clause

from typing import Union

import torch.nn as nn

from ...nn.modules.loss import Criterion, MAE
from ...nn.modules.saits import SaitsLoss, SaitsEmbedding
from ...nn.modules.stemgnn import BackboneStemGNN


class _StemGNN(nn.Module):
    def __init__(
        self,
        n_steps,
        n_features,
        n_layers,
        n_stacks,
        d_model,
        dropout_rate=0.5,
        leaky_rate=0.2,
        ORT_weight: float = 1,
        MIT_weight: float = 1,
        training_loss: Union[Criterion, type] = MAE,
    ):
        super().__init__()

        self.n_steps = n_steps

        self.saits_embedding = SaitsEmbedding(
            n_features * 2,
            d_model,
            with_pos=False,
        )
        self.backbone = BackboneStemGNN(
            units=d_model,
            stack_cnt=n_stacks,
            time_step=n_steps,
            multi_layer=n_layers,
            horizon=n_steps,
            dropout_rate=dropout_rate,
            leaky_rate=leaky_rate,
        )

        # for the imputation task, the output dim is the same as input dim
        self.output_projection = nn.Linear(d_model, n_features)
        self.saits_training_loss = SaitsLoss(ORT_weight, MIT_weight, training_loss)

    def forward(self, inputs: dict) -> dict:
        X, missing_mask = inputs["X"], inputs["missing_mask"]

        # WDU: the original StemGNN paper isn't proposed for imputation task. Hence the model doesn't take
        # the missing mask into account, which means, in the process, the model doesn't know which part of
        # the input data is missing, and this may hurt the model's imputation performance. Therefore, I apply the
        # SAITS embedding method to project the concatenation of features and masks into a hidden space, as well as
        # the output layers to project back from the hidden space to the original space.
        enc_out = self.saits_embedding(X, missing_mask)

        # StemGNN encoder processing
        enc_out, _ = self.backbone(enc_out)
        # project back the original data space
        reconstruction = self.output_projection(enc_out)

        imputed_data = missing_mask * X + (1 - missing_mask) * reconstruction
        results = {
            "imputed_data": imputed_data,
        }

        # if in training mode, return results with losses
        if self.training:
            X_ori, indicating_mask = inputs["X_ori"], inputs["indicating_mask"]
            loss, ORT_loss, MIT_loss = self.saits_training_loss(reconstruction, X_ori, missing_mask, indicating_mask)
            results["ORT_loss"] = ORT_loss
            results["MIT_loss"] = MIT_loss
            # `loss` is always the item for backward propagating to update the model
            results["loss"] = loss

        return results
