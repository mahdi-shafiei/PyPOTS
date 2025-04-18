"""

"""

# Created by Wenjie Du <wenjay.du@gmail.com>
# License: BSD-3-Clause

from typing import Optional, Tuple, Union

import torch
import torch.nn as nn

from .attention import ScaledDotProductAttention
from .layers import TransformerEncoderLayer, TransformerDecoderLayer


class TransformerEncoder(nn.Module):
    """Transformer encoder.

    Parameters
    ----------
    n_layers:
        The number of layers in the encoder.

    d_model:
        The dimension of the module manipulation space.
        The input tensor will be projected to a space with d_model dimensions.

    n_heads:
        The number of heads in multi-head attention.

    d_k:
        The dimension of the key and query tensor.

    d_v:
        The dimension of the value tensor.

    d_ffn:
        The dimension of the hidden layer in the feed-forward network.

    dropout:
        The dropout rate.

    attn_dropout:
        The dropout rate for the attention map.

    """

    def __init__(
        self,
        n_layers: int,
        d_model: int,
        n_heads: int,
        d_k: int,
        d_v: int,
        d_ffn: int,
        dropout: float,
        attn_dropout: float,
    ):
        super().__init__()

        self.enc_layer_stack = nn.ModuleList(
            [
                TransformerEncoderLayer(
                    ScaledDotProductAttention(d_k**0.5, attn_dropout),
                    d_model,
                    n_heads,
                    d_k,
                    d_v,
                    d_ffn,
                    dropout,
                )
                for _ in range(n_layers)
            ]
        )

    def forward(
        self,
        x: torch.Tensor,
        src_mask: Optional[torch.Tensor] = None,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, list]]:
        """Forward processing of the encoder.

        Parameters
        ----------
        x:
            Input tensor.

        src_mask:
            Masking tensor for the attention map. The shape should be [batch_size, n_heads, n_steps, n_steps].

        Returns
        -------
        enc_output:
            Output tensor.

        attn_weights_collector:
            A list containing the attention map from each encoder layer.

        """
        attn_weights_collector = []
        enc_output = x

        for layer in self.enc_layer_stack:
            enc_output, attn_weights = layer(enc_output, src_mask)
            attn_weights_collector.append(attn_weights)

        return enc_output, attn_weights_collector


class TransformerDecoder(nn.Module):
    """Transformer decoder.

    Parameters
    ----------
    n_layers:
        The number of layers in the decoder.

    d_model:
        The dimension of the module manipulation space.
        The input tensor will be projected to a space with d_model dimensions.

    n_heads:
        The number of heads in multi-head attention.

    d_k:
        The dimension of the key and query tensor.

    d_v:
        The dimension of the value tensor.

    d_ffn:
        The dimension of the hidden layer in the feed-forward network.

    dropout:
        The dropout rate.

    attn_dropout:
        The dropout rate for the attention map.

    """

    def __init__(
        self,
        n_layers: int,
        d_model: int,
        n_heads: int,
        d_k: int,
        d_v: int,
        d_ffn: int,
        dropout: float,
        attn_dropout: float,
    ):
        super().__init__()
        self.layer_stack = nn.ModuleList(
            [
                TransformerDecoderLayer(
                    ScaledDotProductAttention(d_k**0.5, attn_dropout),
                    ScaledDotProductAttention(d_k**0.5, attn_dropout),
                    d_model,
                    n_heads,
                    d_k,
                    d_v,
                    d_ffn,
                    dropout,
                )
                for _ in range(n_layers)
            ]
        )

    def forward(
        self,
        trg_seq: torch.Tensor,
        enc_output: torch.Tensor,
        trg_mask: Optional[torch.Tensor] = None,
        src_mask: Optional[torch.Tensor] = None,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, list, list]]:
        """Forward processing of the decoder.

        Parameters
        ----------
        trg_seq:
            Input tensor.

        enc_output:
            Output tensor from the encoder.

        trg_mask:
            Masking tensor for the self-attention module.

        src_mask:
            Masking tensor for the encoding attention module.

        Returns
        -------
        dec_output:
            Output tensor.

        dec_slf_attn_collector:
            A list containing the self-attention map from each decoder layer.

        dec_enc_attn_collector:
            A list containing the encoding attention map from each decoder layer.

        """

        dec_slf_attn_collector = []
        dec_enc_attn_collector = []

        for layer in self.layer_stack:
            trg_seq, dec_slf_attn, dec_enc_attn = layer(
                trg_seq,
                enc_output,
                slf_attn_mask=trg_mask,
                dec_enc_attn_mask=src_mask,
            )
            dec_slf_attn_collector.append(dec_slf_attn)
            dec_enc_attn_collector.append(dec_enc_attn)

        return trg_seq, dec_slf_attn_collector, dec_enc_attn_collector
