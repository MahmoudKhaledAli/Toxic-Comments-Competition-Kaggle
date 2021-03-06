from base.base_model import BaseModel
import os
import numpy as np
from tensorflow.python.keras.models import Model
from tensorflow.python.keras.layers import Input, Dense, Conv2D, MaxPool2D, Flatten, Concatenate, Reshape, Embedding


class MultiLabelConvModel(BaseModel):
    def __init__(self, config, word_index):
        super(MultiLabelConvModel, self).__init__(config)
        self.max_sequence_length = config.max_sequence_length
        self.embedding_model_name = config.embedding_model_name
        self.embedding_dim = config.embedding_dim
        self.vocab_size = self.config.vocab_size
        self.word_index = word_index
        self.build_model()

    def get_embedding_matrix(self):
        embeddings_index = {}
        
        with open(os.path.join('datasets', self.embedding_model_name), encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                    values = line.split()
                    word = values[0]
                    coefs = np.asarray(values[1:], dtype='float32')
                    embeddings_index[word] = coefs

        embedding_matrix = np.zeros((self.config.vocab_size + 1, self.embedding_dim))
        for word, i in self.word_index.items():
                embedding_vector = embeddings_index.get(word)
                if embedding_vector is not None:
                        # words not found in embedding index will be all-zeros.
                        embedding_matrix[i] = embedding_vector
        
        return embedding_matrix

    def embedding_layer(self):
        embedding_matrix = self.get_embedding_matrix()
        
        return Embedding(
            input_dim=self.vocab_size + 1,
            output_dim=self.embedding_dim,
            weights=[embedding_matrix],
            input_length=self.max_sequence_length,
            trainable=False
            )
        
    def n_grams_channel(self, inputs, n):
        channel = Conv2D(1, kernel_size=(n, self.embedding_dim), activation='relu')(inputs)
        channel_mp = MaxPool2D(pool_size=(channel.shape[1], 1))(channel)
        channel_final = Flatten()(channel_mp)        
        return channel_final
        
    def build_model(self):
        self.inputs = Input(shape=(self.max_sequence_length,))
        self.embedding = self.embedding_layer()(self.inputs)
        self.channel_inputs = Reshape(target_shape=(self.max_sequence_length, self.embedding_dim, 1))(self.embedding)
        self.channel1_final = self.n_grams_channel(self.channel_inputs, 3)
        self.channel2_final = self.n_grams_channel(self.channel_inputs, 4)
        self.channel3_final = self.n_grams_channel(self.channel_inputs, 5)
        self.channels_final = Concatenate()([self.channel1_final, self.channel2_final, self.channel3_final])
        self.predictions = Dense(6, 'sigmoid')(self.channels_final)
        
        self.model = Model(inputs=self.inputs, outputs=self.predictions)
        
        self.model.compile(
            loss='binary_crossentropy',
            optimizer=self.config.optimizer,
            metrics=['acc'],
        )
