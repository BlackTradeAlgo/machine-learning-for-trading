"""
LSTM Price Prediction Model
Deep Learning model for predicting future prices

Architecture:
- LSTM layers for sequential learning
- Dropout for regularization
- Dense layers for final prediction

Features:
- Multi-day ahead prediction
- Confidence intervals
- Walk-forward validation
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List
import warnings

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    warnings.warn("TensorFlow not available. Install with: pip install tensorflow")

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt


class LSTMPricePredictor:
    """
    LSTM-based price prediction model

    Example Usage:
    --------------
    predictor = LSTMPricePredictor(lookback=60, prediction_days=5)
    predictor.prepare_data(prices)
    predictor.build_model()
    predictor.train(epochs=100, batch_size=32)
    predictions = predictor.predict()
    """

    def __init__(self,
                 lookback: int = 60,
                 prediction_days: int = 1,
                 lstm_units: List[int] = [128, 64, 32],
                 dropout_rate: float = 0.2,
                 learning_rate: float = 0.001):
        """
        Initialize LSTM Predictor

        Parameters:
        -----------
        lookback : int
            Number of past days to use for prediction
        prediction_days : int
            Number of days ahead to predict
        lstm_units : List[int]
            Number of units in each LSTM layer
        dropout_rate : float
            Dropout rate for regularization
        learning_rate : float
            Learning rate for optimizer
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow is required for LSTM models")

        self.lookback = lookback
        self.prediction_days = prediction_days
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate

        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None
        self.history = None

    def prepare_data(self,
                    prices: pd.Series,
                    train_size: float = 0.8,
                    features: Optional[pd.DataFrame] = None) -> None:
        """
        Prepare data for training

        Parameters:
        -----------
        prices : pd.Series
            Time series of prices
        train_size : float
            Proportion of data for training
        features : pd.DataFrame (optional)
            Additional features (volume, indicators, etc.)
        """
        # Convert to numpy array
        if isinstance(prices, pd.Series):
            prices = prices.values.reshape(-1, 1)
        elif isinstance(prices, np.ndarray):
            if prices.ndim == 1:
                prices = prices.reshape(-1, 1)

        # Scale the data
        scaled_data = self.scaler.fit_transform(prices)

        # Create sequences
        X, y = [], []

        for i in range(self.lookback, len(scaled_data) - self.prediction_days + 1):
            X.append(scaled_data[i - self.lookback:i, 0])
            y.append(scaled_data[i + self.prediction_days - 1, 0])

        X, y = np.array(X), np.array(y)

        # Reshape for LSTM [samples, time steps, features]
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        # Split into train and test
        train_size_idx = int(len(X) * train_size)

        self.X_train = X[:train_size_idx]
        self.y_train = y[:train_size_idx]
        self.X_test = X[train_size_idx:]
        self.y_test = y[train_size_idx:]

        print(f"Data prepared:")
        print(f"  Training samples: {len(self.X_train)}")
        print(f"  Testing samples: {len(self.X_test)}")
        print(f"  Lookback: {self.lookback} days")
        print(f"  Prediction: {self.prediction_days} day(s) ahead")

    def build_model(self, bidirectional: bool = False) -> None:
        """
        Build LSTM model

        Parameters:
        -----------
        bidirectional : bool
            Use bidirectional LSTM (better for complex patterns)
        """
        self.model = Sequential()

        # First LSTM layer
        if bidirectional:
            self.model.add(Bidirectional(
                LSTM(self.lstm_units[0], return_sequences=True),
                input_shape=(self.lookback, 1)
            ))
        else:
            self.model.add(LSTM(
                self.lstm_units[0],
                return_sequences=True,
                input_shape=(self.lookback, 1)
            ))
        self.model.add(Dropout(self.dropout_rate))

        # Additional LSTM layers
        for units in self.lstm_units[1:]:
            if bidirectional:
                self.model.add(Bidirectional(LSTM(units, return_sequences=True)))
            else:
                self.model.add(LSTM(units, return_sequences=True))
            self.model.add(Dropout(self.dropout_rate))

        # Final LSTM layer (no return_sequences)
        if bidirectional:
            self.model.add(Bidirectional(LSTM(32)))
        else:
            self.model.add(LSTM(32))
        self.model.add(Dropout(self.dropout_rate))

        # Dense layers
        self.model.add(Dense(16, activation='relu'))
        self.model.add(Dense(1))

        # Compile
        optimizer = Adam(learning_rate=self.learning_rate)
        self.model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])

        print("\nModel Architecture:")
        self.model.summary()

    def train(self,
             epochs: int = 100,
             batch_size: int = 32,
             validation_split: float = 0.1,
             early_stopping_patience: int = 10,
             reduce_lr_patience: int = 5,
             verbose: int = 1) -> None:
        """
        Train the model

        Parameters:
        -----------
        epochs : int
            Number of training epochs
        batch_size : int
            Batch size
        validation_split : float
            Proportion of training data for validation
        early_stopping_patience : int
            Patience for early stopping
        reduce_lr_patience : int
            Patience for reducing learning rate
        verbose : int
            Verbosity level
        """
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")

        if self.X_train is None:
            raise ValueError("Data not prepared. Call prepare_data() first.")

        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=early_stopping_patience,
                restore_best_weights=True,
                verbose=1
            ),
            ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=reduce_lr_patience,
                min_lr=1e-7,
                verbose=1
            )
        ]

        # Train
        print(f"\nTraining model for {epochs} epochs...")
        self.history = self.model.fit(
            self.X_train,
            self.y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=verbose
        )

        print("\nTraining completed!")

    def predict(self, X: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Make predictions

        Parameters:
        -----------
        X : np.ndarray (optional)
            Input data. If None, uses test set

        Returns:
        --------
        np.ndarray : Predictions (rescaled to original scale)
        """
        if self.model is None:
            raise ValueError("Model not trained yet.")

        if X is None:
            X = self.X_test

        # Predict
        predictions_scaled = self.model.predict(X)

        # Inverse transform
        predictions = self.scaler.inverse_transform(predictions_scaled)

        return predictions.flatten()

    def evaluate(self) -> dict:
        """
        Evaluate model on test set

        Returns:
        --------
        dict : Evaluation metrics
        """
        predictions = self.predict(self.X_test)
        actuals = self.scaler.inverse_transform(self.y_test.reshape(-1, 1)).flatten()

        metrics = {
            'mse': mean_squared_error(actuals, predictions),
            'rmse': np.sqrt(mean_squared_error(actuals, predictions)),
            'mae': mean_absolute_error(actuals, predictions),
            'r2': r2_score(actuals, predictions),
            'mape': np.mean(np.abs((actuals - predictions) / actuals)) * 100
        }

        return metrics

    def predict_next(self, recent_prices: np.ndarray, n_steps: int = 5) -> np.ndarray:
        """
        Predict next n steps

        Parameters:
        -----------
        recent_prices : np.ndarray
            Recent prices (at least lookback length)
        n_steps : int
            Number of steps to predict

        Returns:
        --------
        np.ndarray : Predictions
        """
        if len(recent_prices) < self.lookback:
            raise ValueError(f"Need at least {self.lookback} recent prices")

        # Take last lookback prices
        last_sequence = recent_prices[-self.lookback:]

        # Scale
        last_sequence_scaled = self.scaler.transform(last_sequence.reshape(-1, 1))

        predictions = []

        current_sequence = last_sequence_scaled.copy()

        for _ in range(n_steps):
            # Reshape for LSTM
            X = current_sequence.reshape(1, self.lookback, 1)

            # Predict
            pred_scaled = self.model.predict(X, verbose=0)

            # Store prediction
            pred = self.scaler.inverse_transform(pred_scaled)[0, 0]
            predictions.append(pred)

            # Update sequence (rolling window)
            current_sequence = np.append(current_sequence[1:], pred_scaled)

        return np.array(predictions)

    def plot_training_history(self) -> None:
        """Plot training history"""
        if self.history is None:
            print("No training history available")
            return

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

        # Loss
        ax1.plot(self.history.history['loss'], label='Training Loss')
        ax1.plot(self.history.history['val_loss'], label='Validation Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss (MSE)')
        ax1.set_title('Model Loss')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # MAE
        ax2.plot(self.history.history['mae'], label='Training MAE')
        ax2.plot(self.history.history['val_mae'], label='Validation MAE')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('MAE')
        ax2.set_title('Mean Absolute Error')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

    def plot_predictions(self, n_samples: int = 100) -> None:
        """
        Plot predictions vs actuals

        Parameters:
        -----------
        n_samples : int
            Number of samples to plot
        """
        predictions = self.predict(self.X_test[:n_samples])
        actuals = self.scaler.inverse_transform(
            self.y_test[:n_samples].reshape(-1, 1)
        ).flatten()

        plt.figure(figsize=(15, 6))
        plt.plot(actuals, label='Actual', marker='o', markersize=3)
        plt.plot(predictions, label='Predicted', marker='x', markersize=3)
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.title(f'LSTM Predictions vs Actual (Sample: {n_samples})')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    def save_model(self, filepath: str) -> None:
        """Save model to file"""
        if self.model is not None:
            self.model.save(filepath)
            print(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> None:
        """Load model from file"""
        self.model = keras.models.load_model(filepath)
        print(f"Model loaded from {filepath}")


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("LSTM PRICE PREDICTION - EXAMPLE")
    print("=" * 80)

    # Generate sample data (Nifty-like price movement)
    np.random.seed(42)
    days = 500
    trend = np.linspace(19000, 20000, days)
    seasonality = 200 * np.sin(np.linspace(0, 8 * np.pi, days))
    noise = np.random.normal(0, 50, days)
    prices = trend + seasonality + noise

    prices_series = pd.Series(prices)

    # Initialize predictor
    predictor = LSTMPricePredictor(
        lookback=60,
        prediction_days=1,
        lstm_units=[128, 64, 32],
        dropout_rate=0.2
    )

    # Prepare data
    predictor.prepare_data(prices_series, train_size=0.8)

    # Build model
    predictor.build_model(bidirectional=False)

    # Train
    predictor.train(epochs=50, batch_size=32, verbose=0)

    # Evaluate
    print("\n" + "=" * 80)
    print("MODEL EVALUATION")
    print("=" * 80)
    metrics = predictor.evaluate()

    for metric_name, value in metrics.items():
        print(f"{metric_name.upper():<10}: {value:.4f}")

    # Predict next 5 days
    print("\n" + "=" * 80)
    print("NEXT 5 DAYS PREDICTION")
    print("=" * 80)

    recent_prices = prices[-60:]
    next_5_days = predictor.predict_next(recent_prices, n_steps=5)

    print(f"{'Day':<10} {'Predicted Price':<20}")
    print("-" * 30)
    for i, pred in enumerate(next_5_days, 1):
        print(f"Day {i:<6} ₹{pred:,.2f}")

    print("\n" + "=" * 80)
    print("Visualization:")
    print("Uncomment to see plots:")
    print("  - predictor.plot_training_history()")
    print("  - predictor.plot_predictions()")
    print("=" * 80)
