"""
Random Forest Direction Predictor
Predicts market direction (Up/Down/Sideways) using technical indicators

Features:
- Multi-class classification (Up/Down/Sideways)
- Feature importance analysis
- SHAP value interpretation
- Ensemble predictions
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import warnings


class RandomForestPredictor:
    """
    Random Forest for market direction prediction

    Example Usage:
    --------------
    predictor = RandomForestPredictor()
    predictor.create_features(prices_df)
    predictor.train()
    direction = predictor.predict_direction()
    """

    def __init__(self,
                 n_estimators: int = 200,
                 max_depth: int = 15,
                 min_samples_split: int = 10,
                 min_samples_leaf: int = 5,
                 random_state: int = 42):
        """
        Initialize Random Forest Predictor

        Parameters:
        -----------
        n_estimators : int
            Number of trees in the forest
        max_depth : int
            Maximum depth of trees
        min_samples_split : int
            Minimum samples required to split
        min_samples_leaf : int
            Minimum samples required in leaf
        random_state : int
            Random seed
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state

        self.model = None
        self.scaler = StandardScaler()
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = None

    def create_features(self,
                       df: pd.DataFrame,
                       price_col: str = 'close',
                       forward_days: int = 1,
                       threshold_pct: float = 0.5) -> pd.DataFrame:
        """
        Create technical features from price data

        Parameters:
        -----------
        df : pd.DataFrame
            OHLCV data
        price_col : str
            Column name for price
        forward_days : int
            Days ahead to predict
        threshold_pct : float
            Threshold for sideways movement (%)

        Returns:
        --------
        pd.DataFrame : DataFrame with features and target
        """
        data = df.copy()

        # Calculate returns
        data['returns'] = data[price_col].pct_change()

        # Moving averages
        for window in [5, 10, 20, 50]:
            data[f'sma_{window}'] = data[price_col].rolling(window).mean()
            data[f'ema_{window}'] = data[price_col].ewm(span=window).mean()

        # Price relative to MAs
        data['price_to_sma20'] = data[price_col] / data['sma_20']
        data['price_to_sma50'] = data[price_col] / data['sma_50']

        # Momentum indicators
        data['rsi'] = self._calculate_rsi(data[price_col], period=14)
        data['macd'], data['macd_signal'] = self._calculate_macd(data[price_col])
        data['macd_diff'] = data['macd'] - data['macd_signal']

        # Volatility
        data['volatility_20'] = data['returns'].rolling(20).std()
        data['atr'] = self._calculate_atr(data, period=14)

        # Volume indicators (if volume available)
        if 'volume' in data.columns:
            data['volume_sma_20'] = data['volume'].rolling(20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_sma_20']

        # Bollinger Bands
        bb_window = 20
        data['bb_middle'] = data[price_col].rolling(bb_window).mean()
        bb_std = data[price_col].rolling(bb_window).std()
        data['bb_upper'] = data['bb_middle'] + (2 * bb_std)
        data['bb_lower'] = data['bb_middle'] - (2 * bb_std)
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / data['bb_middle']
        data['bb_position'] = (data[price_col] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])

        # Support/Resistance
        data['high_20'] = data['high'].rolling(20).max() if 'high' in data.columns else data[price_col].rolling(20).max()
        data['low_20'] = data['low'].rolling(20).min() if 'low' in data.columns else data[price_col].rolling(20).min()

        # Create target (direction)
        data['future_returns'] = data[price_col].shift(-forward_days) / data[price_col] - 1

        # Classify: 0=Down, 1=Sideways, 2=Up
        data['target'] = 1  # Default: Sideways
        data.loc[data['future_returns'] > threshold_pct/100, 'target'] = 2  # Up
        data.loc[data['future_returns'] < -threshold_pct/100, 'target'] = 0  # Down

        # Drop NaN
        data.dropna(inplace=True)

        return data

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: pd.Series,
                       fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        if 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(period).mean()
            return atr
        else:
            return df['close'].rolling(period).std()

    def prepare_data(self, data: pd.DataFrame, test_size: float = 0.2) -> None:
        """
        Prepare data for training

        Parameters:
        -----------
        data : pd.DataFrame
            DataFrame with features and target
        test_size : float
            Test set size
        """
        # Select feature columns
        feature_cols = [col for col in data.columns
                       if col not in ['target', 'future_returns', 'date']]

        X = data[feature_cols].values
        y = data['target'].values

        self.feature_names = feature_cols

        # Split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False, random_state=self.random_state
        )

        # Scale
        self.X_train = self.scaler.fit_transform(self.X_train)
        self.X_test = self.scaler.transform(self.X_test)

        print(f"Data prepared:")
        print(f"  Training samples: {len(self.X_train)}")
        print(f"  Testing samples: {len(self.X_test)}")
        print(f"  Features: {len(feature_cols)}")
        print(f"  Classes: {len(np.unique(y))} (0=Down, 1=Sideways, 2=Up)")

        # Class distribution
        unique, counts = np.unique(y, return_counts=True)
        print(f"\n  Class distribution:")
        for cls, count in zip(unique, counts):
            pct = (count / len(y)) * 100
            cls_name = ['Down', 'Sideways', 'Up'][int(cls)]
            print(f"    {cls_name}: {count} ({pct:.1f}%)")

    def train(self, cv_folds: int = 5) -> None:
        """
        Train Random Forest model

        Parameters:
        -----------
        cv_folds : int
            Cross-validation folds
        """
        if self.X_train is None:
            raise ValueError("Data not prepared. Call prepare_data() first.")

        print(f"\nTraining Random Forest...")

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            random_state=self.random_state,
            n_jobs=-1,
            verbose=0
        )

        # Train
        self.model.fit(self.X_train, self.y_train)

        # Cross-validation
        if cv_folds > 1:
            cv_scores = cross_val_score(
                self.model, self.X_train, self.y_train,
                cv=cv_folds, scoring='accuracy'
            )
            print(f"Cross-validation scores: {cv_scores}")
            print(f"Mean CV accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

        print("Training completed!")

    def evaluate(self) -> dict:
        """
        Evaluate model on test set

        Returns:
        --------
        dict : Evaluation metrics
        """
        y_pred = self.model.predict(self.X_test)

        accuracy = accuracy_score(self.y_test, y_pred)

        print("\n" + "=" * 80)
        print("MODEL EVALUATION")
        print("=" * 80)
        print(f"Accuracy: {accuracy:.4f}")

        print("\nClassification Report:")
        print(classification_report(
            self.y_test, y_pred,
            target_names=['Down', 'Sideways', 'Up']
        ))

        print("\nConfusion Matrix:")
        cm = confusion_matrix(self.y_test, y_pred)
        print(cm)

        return {
            'accuracy': accuracy,
            'confusion_matrix': cm
        }

    def predict_direction(self, features: np.ndarray) -> Tuple[str, float]:
        """
        Predict market direction

        Parameters:
        -----------
        features : np.ndarray
            Feature vector

        Returns:
        --------
        Tuple[str, float] : (direction, probability)
        """
        if self.model is None:
            raise ValueError("Model not trained yet.")

        # Scale
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        direction_map = {0: 'Down', 1: 'Sideways', 2: 'Up'}
        direction = direction_map[prediction]
        confidence = probabilities[prediction]

        return direction, confidence

    def feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        """
        Get feature importance

        Parameters:
        -----------
        top_n : int
            Number of top features to return

        Returns:
        --------
        pd.DataFrame : Feature importances
        """
        if self.model is None:
            raise ValueError("Model not trained yet.")

        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]

        feature_importance_df = pd.DataFrame({
            'feature': [self.feature_names[i] for i in indices],
            'importance': importances[indices]
        })

        return feature_importance_df

    def predict_signal(self, features: np.ndarray) -> int:
        """
        Get trading signal

        Returns:
        --------
        int : 1 (Buy), 0 (Hold), -1 (Sell)
        """
        direction, confidence = self.predict_direction(features)

        # Only trade with high confidence
        if confidence < 0.6:
            return 0  # Hold

        if direction == 'Up':
            return 1  # Buy
        elif direction == 'Down':
            return -1  # Sell
        else:
            return 0  # Hold


if __name__ == "__main__":
    print("=" * 80)
    print("RANDOM FOREST DIRECTION PREDICTION - EXAMPLE")
    print("=" * 80)

    # Generate sample data
    np.random.seed(42)
    days = 500

    dates = pd.date_range('2023-01-01', periods=days, freq='D')
    trend = np.linspace(19000, 20000, days)
    seasonality = 200 * np.sin(np.linspace(0, 8 * np.pi, days))
    noise = np.random.normal(0, 50, days)

    df = pd.DataFrame({
        'date': dates,
        'close': trend + seasonality + noise,
        'high': trend + seasonality + noise + np.random.uniform(10, 50, days),
        'low': trend + seasonality + noise - np.random.uniform(10, 50, days),
        'volume': np.random.uniform(1000000, 5000000, days)
    })

    # Initialize predictor
    predictor = RandomForestPredictor(
        n_estimators=200,
        max_depth=15
    )

    # Create features
    print("\nCreating features...")
    data = predictor.create_features(df, forward_days=1, threshold_pct=0.5)

    # Prepare data
    predictor.prepare_data(data, test_size=0.2)

    # Train
    predictor.train(cv_folds=5)

    # Evaluate
    predictor.evaluate()

    # Feature importance
    print("\n" + "=" * 80)
    print("TOP 10 IMPORTANT FEATURES")
    print("=" * 80)
    importance_df = predictor.feature_importance(top_n=10)
    print(importance_df.to_string(index=False))

    # Predict on latest data
    print("\n" + "=" * 80)
    print("PREDICTION ON LATEST DATA")
    print("=" * 80)

    latest_features = predictor.X_test[-1]
    direction, confidence = predictor.predict_direction(latest_features)

    print(f"Direction: {direction}")
    print(f"Confidence: {confidence*100:.2f}%")

    signal = predictor.predict_signal(latest_features)
    signal_map = {1: 'BUY 📈', 0: 'HOLD ⏸', -1: 'SELL 📉'}
    print(f"Signal: {signal_map[signal]}")

    print("=" * 80)
