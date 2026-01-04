"""
Custom CRF Layer for TensorFlow/Keras
Compatible implementation without tensorflow-addons dependency

Based on: https://github.com/keras-team/keras-contrib/blob/master/keras_contrib/layers/crf.py
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import backend as K
from tensorflow.keras.layers import Layer


class CRF(Layer):
    """
    Conditional Random Field layer for sequence tagging.
    
    This implementation handles variable-length sequences using masking.
    
    Args:
        units: Number of output classes (slot tags)
        
    Input shape:
        (batch_size, sequence_length, input_dim)
        
    Output shape:
        (batch_size, sequence_length, units)
    """
    
    def __init__(self, units, **kwargs):
        super(CRF, self).__init__(**kwargs)
        self.units = units
        self.supports_masking = True
        
    def build(self, input_shape):
        """Build the CRF layer - create transition matrix."""
        # Transition parameters: transitions[i, j] = score of transitioning from tag i to tag j
        self.transitions = self.add_weight(
            name='transitions',
            shape=(self.units, self.units),
            initializer='glorot_uniform',
            trainable=True
        )
        
        # Start and end transitions
        self.start_transitions = self.add_weight(
            name='start_transitions',
            shape=(self.units,),
            initializer='zeros',
            trainable=True
        )
        
        self.end_transitions = self.add_weight(
            name='end_transitions',
            shape=(self.units,),
            initializer='zeros',
            trainable=True
        )
        
        super(CRF, self).build(input_shape)
    
    def call(self, inputs, mask=None, training=None):
        """
        Forward pass.
        
        During training: Return emissions (logits) for loss computation
        During inference: Return Viterbi decoded sequence
        
        Args:
            inputs: Emission scores (batch_size, seq_len, num_tags)
            mask: Mask for variable length sequences
            training: Whether in training mode
            
        Returns:
            During training: emissions (for CRF loss)
            During inference: one-hot decoded sequence
        """
        if mask is None:
            # Create a mask of all ones if not provided
            mask = K.ones_like(inputs[:, :, 0], dtype='bool')
        
        # During training, return emissions for loss computation
        # The loss function will handle the CRF computation
        if training or training is None:
            return inputs
        
        # During inference, do Viterbi decoding
        viterbi_sequence = self.viterbi_decode(inputs, mask)
        
        # Convert to one-hot
        output = K.one_hot(viterbi_sequence, self.units)
        
        return output
    
    def viterbi_decode(self, emissions, mask):
        """
        Viterbi algorithm for finding most likely tag sequence.
        
        Args:
            emissions: (batch_size, seq_len, num_tags)
            mask: (batch_size, seq_len)
            
        Returns:
            best_path: (batch_size, seq_len)
        """
        batch_size = K.shape(emissions)[0]
        seq_len = K.shape(emissions)[1]
        
        # Get sequence lengths from mask
        seq_lengths = K.sum(K.cast(mask, 'int32'), axis=1)
        
        # Initialize with start transitions
        score = emissions[:, 0] + self.start_transitions
        
        # Store backpointers for path reconstruction
        history = []
        
        # Forward pass
        for i in range(1, seq_len):
            # Broadcast score for all possible next tags
            broadcast_score = K.expand_dims(score, 2)  # (batch, num_tags, 1)
            broadcast_emission = K.expand_dims(emissions[:, i], 1)  # (batch, 1, num_tags)
            
            # Compute scores for all transitions
            next_score = broadcast_score + self.transitions + broadcast_emission
            
            # Find best previous tag for each current tag
            best_score = K.max(next_score, axis=1)
            best_path = K.argmax(next_score, axis=1)
            
            # Update score
            score = best_score
            history.append(best_path)
        
        # Add end transitions
        score = score + self.end_transitions
        
        # Backward pass to find best path
        best_last_tag = K.argmax(score, axis=1)
        best_tags = [best_last_tag]
        
        # Reconstruct path
        for hist in reversed(history):
            best_last_tag = K.gather(hist, best_last_tag, batch_dims=1)
            best_tags.append(best_last_tag)
        
        # Reverse to get correct order
        best_tags = K.stack(list(reversed(best_tags)), axis=1)
        
        return best_tags
    
    def loss(self, y_true, y_pred, mask=None):
        """
        CRF loss function (negative log-likelihood).
        
        Args:
            y_true: True labels (batch_size, seq_len)
            y_pred: Emission scores (batch_size, seq_len, num_tags)
            mask: Sequence mask
            
        Returns:
            Loss value
        """
        if mask is None:
            mask = K.ones_like(y_true, dtype='float32')
        else:
            mask = K.cast(mask, 'float32')
        
        # Compute log partition function (normalization)
        log_norm = self._log_norm(y_pred, mask)
        
        # Compute score of true sequence
        log_likelihood = self._score_sequence(y_pred, y_true, mask)
        
        # Loss is negative log-likelihood
        loss = log_norm - log_likelihood
        
        return K.mean(loss)
    
    def _score_sequence(self, emissions, tags, mask):
        """
        Compute score of a given tag sequence.
        
        Args:
            emissions: (batch_size, seq_len, num_tags)
            tags: (batch_size, seq_len)
            mask: (batch_size, seq_len)
            
        Returns:
            score: (batch_size,)
        """
        batch_size = K.shape(emissions)[0]
        seq_len = K.shape(emissions)[1]
        
        # Get emission scores for true tags
        emission_scores = K.sum(
            K.gather(emissions, K.cast(tags, 'int32'), batch_dims=2) * mask,
            axis=1
        )
        
        # Get transition scores
        transition_scores = K.zeros((batch_size,))
        
        # Add start transition
        first_tags = tags[:, 0]
        transition_scores += K.gather(self.start_transitions, first_tags)
        
        # Add intermediate transitions
        for i in range(seq_len - 1):
            current_tags = tags[:, i]
            next_tags = tags[:, i + 1]
            
            # Get transition score
            trans_score = K.gather(
                K.gather(self.transitions, current_tags),
                next_tags,
                batch_dims=1
            )
            
            transition_scores += trans_score * mask[:, i + 1]
        
        # Add end transition
        seq_lengths = K.sum(K.cast(mask, 'int32'), axis=1)
        last_tag_indices = seq_lengths - 1
        last_tags = K.gather(tags, last_tag_indices, batch_dims=1)
        transition_scores += K.gather(self.end_transitions, last_tags)
        
        return emission_scores + transition_scores
    
    def _log_norm(self, emissions, mask):
        """
        Compute log partition function using forward algorithm.
        
        Args:
            emissions: (batch_size, seq_len, num_tags)
            mask: (batch_size, seq_len)
            
        Returns:
            log_norm: (batch_size,)
        """
        seq_len = K.shape(emissions)[1]
        
        # Initialize with start transitions
        score = emissions[:, 0] + self.start_transitions
        
        # Forward pass
        for i in range(1, seq_len):
            # Broadcast for all possible transitions
            broadcast_score = K.expand_dims(score, 2)
            broadcast_emission = K.expand_dims(emissions[:, i], 1)
            
            # Compute all transition scores
            next_score = broadcast_score + self.transitions + broadcast_emission
            
            # Log-sum-exp for numerical stability
            next_score = K.logsumexp(next_score, axis=1)
            
            # Apply mask
            score = next_score * mask[:, i:i+1] + score * (1 - mask[:, i:i+1])
        
        # Add end transitions
        score = score + self.end_transitions
        
        # Final log-sum-exp
        return K.logsumexp(score, axis=1)
    
    def get_config(self):
        """Get layer configuration."""
        config = {
            'units': self.units
        }
        base_config = super(CRF, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


def crf_loss(crf_layer):
    """
    CRF loss function factory.
    
    Returns a loss function that computes CRF negative log-likelihood.
    
    Args:
        crf_layer: The CRF layer instance
        
    Returns:
        Loss function
    """
    def loss(y_true, y_pred):
        """
        Compute CRF loss.
        
        Args:
            y_true: True labels (batch_size, seq_len)
            y_pred: Emissions from CRF layer (batch_size, seq_len, num_tags)
        """
        # Get mask from CRF layer if available
        mask = None
        
        # Compute CRF loss
        return crf_layer.loss(y_true, y_pred, mask)
    
    return loss


# For compatibility with keras
keras.utils.get_custom_objects()['CRF'] = CRF
