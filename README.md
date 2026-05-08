# Bot cuantitativo para IQ Option

Base en Python para investigar estrategias antes de operar dinero real. Incluye:

- Bandas de Bollinger.
- MACD.
- EMA de 200 periodos como filtro de tendencia.
- Backtest sobre archivos CSV.
- Entrenamiento simple con regresion logistica para estimar la probabilidad de la siguiente vela.
- Descarga historica opcional desde IQ Option si instalas `iqoptionapi`.

> Nota: IQ Option no ofrece una API publica oficial estable para retail. Este proyecto deja la conexion real aislada para que primero puedas probar con datos historicos y cuenta demo.

## Estructura del CSV

El bot espera columnas:

```csv
timestamp,open,high,low,close,volume
```

`timestamp` puede ser Unix epoch o texto tipo `2026-05-08 10:00:00`.

## Uso rapido

Generar datos de muestra:

```powershell
python .\run_bot.py generate-sample --output data\sample_candles.csv --rows 600
```

Backtest:

```powershell
python .\run_bot.py backtest --csv data\sample_candles.csv
```

Entrenar modelo:

```powershell
python .\run_bot.py train --csv data\sample_candles.csv --model models\trend_model.json
```

Backtest usando el filtro del modelo:

```powershell
python .\run_bot.py backtest --csv data\sample_candles.csv --model models\trend_model.json
```

Modo en vivo sin enviar ordenes:

```powershell
python .\run_bot.py live --asset EURUSD --model models\EURUSD_1m_model.json
```

Modo demo enviando ordenes a IQ Option:

```powershell
python .\run_bot.py live --asset EURUSD --model models\EURUSD_1m_model.json --balance PRACTICE --execute --amount 1 --max-trades 3
```

No uses `--balance REAL` hasta validar la estrategia con muchos datos y varias sesiones demo.

Modo senales por consola y CSV:

```powershell
python .\run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55
```

Modo senales con Telegram:

1. Crea un bot hablando con `@BotFather` en Telegram.
2. Copia el token en `.env` como `TELEGRAM_BOT_TOKEN`.
3. Agrega tu chat id como `TELEGRAM_CHAT_ID`.
4. Ejecuta:

```powershell
python .\run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --telegram --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55
```

Las senales se guardan en `logs/signals.csv`. Puedes completar la columna `manual_result` con `WIN`, `LOSS` o `SKIP` para evaluar tus entradas manuales.

Por defecto el bot de senales usa analisis multi temporalidad:

- `--timeframe 60`: entrada en 1 minuto.
- `--confirmation-timeframe 300`: confirmacion en 5 minutos.
- `--context-timeframe 900`: contexto en 15 minutos.
- `--min-score 70`: solo envia senales moderadas o fuertes.

Ejemplo mas explicito:

```powershell
python .\run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --telegram --timeframe 60 --confirmation-timeframe 300 --context-timeframe 900 --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55 --min-score 70
```

Atajo en Windows:

```powershell
.\signals_eurusd_otc.bat
```

Atajo Python:

```powershell
python main.py
```

## Descargar historico de IQ Option

Instala dependencias opcionales:

```powershell
pip install -r requirements.txt
```

Configura credenciales copiando `.env.example` a `.env`:

```powershell
Copy-Item .env.example .env
```

Luego edita `.env`:

```env
IQOPTION_EMAIL=tu@email.com
IQOPTION_PASSWORD=tu_password
TELEGRAM_BOT_TOKEN=token_de_botfather
TELEGRAM_CHAT_ID=tu_chat_id
```

`.env` esta ignorado por Git para no versionar tus credenciales.

Descarga velas:

```powershell
python .\run_bot.py fetch-iq --asset EURUSD --timeframe 60 --count 1000 --output data\EURUSD_1m.csv
```

## Logica inicial

Compra/CALL:

- Precio sobre EMA 200.
- MACD cruza hacia arriba su senal.
- Precio toca o rompe la banda inferior de Bollinger.

Venta/PUT:

- Precio bajo EMA 200.
- MACD cruza hacia abajo su senal.
- Precio toca o rompe la banda superior de Bollinger.

Si se usa modelo entrenado, la senal debe superar la probabilidad minima configurada.
