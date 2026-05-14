@echo off
cd /d "%~dp0"
python run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --telegram --timeframe 60 --confirmation-timeframe 300 --context-timeframe 900 --signal-lookback 10 --expiry-candles 2 --min-model-probability 0.5 --min-score 60
