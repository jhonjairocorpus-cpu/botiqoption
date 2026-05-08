@echo off
python run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --telegram --timeframe 60 --confirmation-timeframe 300 --context-timeframe 900 --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55 --min-score 70
