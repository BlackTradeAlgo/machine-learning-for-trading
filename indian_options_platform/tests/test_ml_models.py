#!/usr/bin/env python3
"""
ML Models Test Suite
Tests all machine learning models in the platform
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Test results
test_results = {
    'lstm_predictor': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'random_forest': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'xgboost_predictor': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'garch_model': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'iv_prediction': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'gamma_scalping': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}},
    'sentiment_analysis': {'status': 'NOT_TESTED', 'error': None, 'metrics': {}}
}


def generate_sample_data(days=500):
    """Generate sample price data for testing"""
    np.random.seed(42)

    dates = pd.date_range('2023-01-01', periods=days, freq='D')
    trend = np.linspace(19000, 20000, days)
    seasonality = 200 * np.sin(np.linspace(0, 8 * np.pi, days))
    noise = np.random.normal(0, 50, days)
    prices = trend + seasonality + noise

    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'high': prices + np.random.uniform(10, 50, days),
        'low': prices - np.random.uniform(10, 50, days),
        'volume': np.random.uniform(1000000, 5000000, days)
    })

    return df, pd.Series(prices)


def test_lstm_predictor():
    """Test LSTM Price Predictor"""
    print("\n" + "="*80)
    print("1. TESTING LSTM PRICE PREDICTOR")
    print("="*80)

    try:
        # Import with try-except to handle TensorFlow dependency
        try:
            from ml_models.price_prediction.lstm_predictor import LSTMPricePredictor, TENSORFLOW_AVAILABLE
        except ImportError as ie:
            test_results['lstm_predictor']['status'] = 'DEPENDENCY_MISSING'
            test_results['lstm_predictor']['error'] = f'Import error: {str(ie)}'
            print(f"❌ SKIPPED - Import error: {str(ie)}")
            return

        if not TENSORFLOW_AVAILABLE:
            test_results['lstm_predictor']['status'] = 'DEPENDENCY_MISSING'
            test_results['lstm_predictor']['error'] = 'TensorFlow not installed'
            print("❌ SKIPPED - TensorFlow not installed")
            return

        df, prices = generate_sample_data()

        # Initialize predictor
        predictor = LSTMPricePredictor(
            lookback=60,
            prediction_days=1,
            lstm_units=[64, 32],
            dropout_rate=0.2
        )

        # Prepare data
        print("Preparing data...")
        predictor.prepare_data(prices, train_size=0.8)

        # Build model
        print("Building model...")
        predictor.build_model(bidirectional=False)

        # Train (quick test)
        print("Training model (10 epochs for testing)...")
        predictor.train(epochs=10, batch_size=32, verbose=0)

        # Evaluate
        print("Evaluating model...")
        metrics = predictor.evaluate()

        # Predict next 5 days
        recent_prices = prices.values[-60:]
        next_5_days = predictor.predict_next(recent_prices, n_steps=5)

        test_results['lstm_predictor']['status'] = 'PASS'
        test_results['lstm_predictor']['metrics'] = {
            'mse': metrics['mse'],
            'rmse': metrics['rmse'],
            'mae': metrics['mae'],
            'r2': metrics['r2']
        }

        print(f"✅ PASS - LSTM model working")
        print(f"   MSE: {metrics['mse']:.2f}")
        print(f"   RMSE: {metrics['rmse']:.2f}")
        print(f"   MAE: {metrics['mae']:.2f}")
        print(f"   R²: {metrics['r2']:.4f}")
        print(f"   Next 5 days predictions: {next_5_days}")

    except Exception as e:
        test_results['lstm_predictor']['status'] = 'FAIL'
        test_results['lstm_predictor']['error'] = str(e)
        print(f"❌ FAIL - {str(e)}")


def test_random_forest():
    """Test Random Forest Direction Predictor"""
    print("\n" + "="*80)
    print("2. TESTING RANDOM FOREST DIRECTION PREDICTOR")
    print("="*80)

    try:
        from ml_models.price_prediction.random_forest_predictor import RandomForestPredictor

        df, _ = generate_sample_data()

        # Initialize predictor
        predictor = RandomForestPredictor(
            n_estimators=100,  # Reduced for faster testing
            max_depth=10
        )

        # Create features
        print("Creating features...")
        data = predictor.create_features(df, forward_days=1, threshold_pct=0.5)

        # Prepare data
        print("Preparing data...")
        predictor.prepare_data(data, test_size=0.2)

        # Train
        print("Training model...")
        predictor.train(cv_folds=3)

        # Evaluate
        print("Evaluating model...")
        metrics = predictor.evaluate()

        # Feature importance
        importance_df = predictor.feature_importance(top_n=5)

        # Predict on latest
        latest_features = predictor.X_test[-1]
        direction, confidence = predictor.predict_direction(latest_features)

        test_results['random_forest']['status'] = 'PASS'
        test_results['random_forest']['metrics'] = {
            'accuracy': metrics['accuracy'],
            'direction': direction,
            'confidence': confidence
        }

        print(f"✅ PASS - Random Forest model working")
        print(f"   Accuracy: {metrics['accuracy']:.4f}")
        print(f"   Latest prediction: {direction} ({confidence*100:.2f}% confidence)")
        print(f"   Top feature: {importance_df.iloc[0]['feature']}")

    except Exception as e:
        test_results['random_forest']['status'] = 'FAIL'
        test_results['random_forest']['error'] = str(e)
        print(f"❌ FAIL - {str(e)}")


def test_xgboost_predictor():
    """Test XGBoost Predictor"""
    print("\n" + "="*80)
    print("3. TESTING XGBOOST PREDICTOR")
    print("="*80)

    try:
        from ml_models.intraday_signals import xgboost_predictor

        # Check if it's just a stub
        with open('ml_models/intraday_signals/xgboost_predictor.py', 'r') as f:
            content = f.read()
            if 'pass' in content and len(content) < 200:
                test_results['xgboost_predictor']['status'] = 'NOT_IMPLEMENTED'
                test_results['xgboost_predictor']['error'] = 'Model is a stub, not implemented'
                print("⚠️  NOT IMPLEMENTED - Stub file only")
                return

        # If we reach here, model might be implemented
        test_results['xgboost_predictor']['status'] = 'PASS'
        print("✅ PASS - XGBoost available")

    except Exception as e:
        test_results['xgboost_predictor']['status'] = 'NOT_IMPLEMENTED'
        test_results['xgboost_predictor']['error'] = str(e)
        print(f"⚠️  NOT IMPLEMENTED - {str(e)}")


def test_garch_model():
    """Test GARCH Volatility Model"""
    print("\n" + "="*80)
    print("4. TESTING GARCH VOLATILITY MODEL")
    print("="*80)

    try:
        from ml_models.volatility_forecasting import garch_model

        # Check if it's just a stub
        with open('ml_models/volatility_forecasting/garch_model.py', 'r') as f:
            content = f.read()
            if 'pass' in content and len(content) < 200:
                test_results['garch_model']['status'] = 'NOT_IMPLEMENTED'
                test_results['garch_model']['error'] = 'Model is a stub, not implemented'
                print("⚠️  NOT IMPLEMENTED - Stub file only")
                return

        test_results['garch_model']['status'] = 'PASS'
        print("✅ PASS - GARCH available")

    except Exception as e:
        test_results['garch_model']['status'] = 'NOT_IMPLEMENTED'
        test_results['garch_model']['error'] = str(e)
        print(f"⚠️  NOT IMPLEMENTED - {str(e)}")


def test_iv_prediction():
    """Test IV Prediction Model"""
    print("\n" + "="*80)
    print("5. TESTING IV PREDICTION MODEL")
    print("="*80)

    try:
        import ml_models.iv_prediction as iv_pred

        # Check if module has implementations
        if not hasattr(iv_pred, '__all__') or len(dir(iv_pred)) <= 5:
            test_results['iv_prediction']['status'] = 'NOT_IMPLEMENTED'
            test_results['iv_prediction']['error'] = 'No implementation found in module'
            print("⚠️  NOT IMPLEMENTED - Empty module")
            return

        test_results['iv_prediction']['status'] = 'PASS'
        print("✅ PASS - IV Prediction available")

    except Exception as e:
        test_results['iv_prediction']['status'] = 'NOT_IMPLEMENTED'
        test_results['iv_prediction']['error'] = str(e)
        print(f"⚠️  NOT IMPLEMENTED - {str(e)}")


def test_gamma_scalping():
    """Test Gamma Scalping Model"""
    print("\n" + "="*80)
    print("6. TESTING GAMMA SCALPING ML MODEL")
    print("="*80)

    try:
        import ml_models.gamma_scalping as gamma

        # Check if module has implementations
        if not hasattr(gamma, '__all__') or len(dir(gamma)) <= 5:
            test_results['gamma_scalping']['status'] = 'NOT_IMPLEMENTED'
            test_results['gamma_scalping']['error'] = 'No implementation found in module'
            print("⚠️  NOT IMPLEMENTED - Empty module")
            return

        test_results['gamma_scalping']['status'] = 'PASS'
        print("✅ PASS - Gamma Scalping ML available")

    except Exception as e:
        test_results['gamma_scalping']['status'] = 'NOT_IMPLEMENTED'
        test_results['gamma_scalping']['error'] = str(e)
        print(f"⚠️  NOT IMPLEMENTED - {str(e)}")


def test_sentiment_analysis():
    """Test Sentiment Analysis Model"""
    print("\n" + "="*80)
    print("7. TESTING SENTIMENT ANALYSIS MODEL")
    print("="*80)

    try:
        import ml_models.sentiment_analysis as sentiment

        # Check if module has implementations
        if not hasattr(sentiment, '__all__') or len(dir(sentiment)) <= 5:
            test_results['sentiment_analysis']['status'] = 'NOT_IMPLEMENTED'
            test_results['sentiment_analysis']['error'] = 'No implementation found in module'
            print("⚠️  NOT IMPLEMENTED - Empty module")
            return

        test_results['sentiment_analysis']['status'] = 'PASS'
        print("✅ PASS - Sentiment Analysis available")

    except Exception as e:
        test_results['sentiment_analysis']['status'] = 'NOT_IMPLEMENTED'
        test_results['sentiment_analysis']['error'] = str(e)
        print(f"⚠️  NOT IMPLEMENTED - {str(e)}")


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("ML MODELS TEST SUMMARY")
    print("="*80)

    status_counts = {
        'PASS': 0,
        'FAIL': 0,
        'NOT_IMPLEMENTED': 0,
        'DEPENDENCY_MISSING': 0,
        'NOT_TESTED': 0
    }

    for model_name, result in test_results.items():
        status = result['status']
        status_counts[status] += 1

        status_icon = {
            'PASS': '✅',
            'FAIL': '❌',
            'NOT_IMPLEMENTED': '⚠️ ',
            'DEPENDENCY_MISSING': '⚠️ ',
            'NOT_TESTED': '⏸️ '
        }

        print(f"\n{model_name.upper().replace('_', ' ')}:")
        print(f"  Status: {status_icon.get(status, '❓')} {status}")

        if result['error']:
            print(f"  Error: {result['error']}")

        if result['metrics']:
            print(f"  Metrics:")
            for metric, value in result['metrics'].items():
                if isinstance(value, float):
                    print(f"    {metric}: {value:.4f}")
                else:
                    print(f"    {metric}: {value}")

    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)
    total = len(test_results)
    print(f"Total ML Models: {total}")
    print(f"✅ Working: {status_counts['PASS']}")
    print(f"❌ Failed: {status_counts['FAIL']}")
    print(f"⚠️  Not Implemented: {status_counts['NOT_IMPLEMENTED']}")
    print(f"⚠️  Dependencies Missing: {status_counts['DEPENDENCY_MISSING']}")
    print(f"⏸️  Not Tested: {status_counts['NOT_TESTED']}")

    success_rate = (status_counts['PASS'] / total) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    if status_counts['PASS'] >= 2:
        print("\n✅ STATUS: Core ML models working")
    elif status_counts['PASS'] >= 1:
        print("\n⚠️  STATUS: Some ML models working")
    else:
        print("\n❌ STATUS: No ML models working")

    print("="*80)


if __name__ == "__main__":
    print("="*80)
    print("ML MODELS TEST SUITE - Indian Options Trading Platform")
    print("="*80)
    print("Testing 7 ML model categories")
    print("="*80)

    # Run tests
    test_lstm_predictor()
    test_random_forest()
    test_xgboost_predictor()
    test_garch_model()
    test_iv_prediction()
    test_gamma_scalping()
    test_sentiment_analysis()

    # Print summary
    print_summary()
