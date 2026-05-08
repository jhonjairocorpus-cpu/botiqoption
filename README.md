# Bot cuantitativo para IQ Option

Bot en Python para evaluar estrategias antes de operar dinero real. Incluye:

- Indicadores técnicos: Bandas de Bollinger, MACD y EMA 200.
- Filtro de tendencia con EMA de 200 periodos.
- Backtest con datos CSV.
- Señales y modo live/demo.
- Opcional: integración con Telegram y descarga histórica.

> Este proyecto está pensado para pruebas y desarrollo. No es una garantía de resultados y no debe usarse con capital real sin una validación exhaustiva.

## Características

- Solo toma operaciones en la dirección de la tendencia general (EMA 200).
- Usa cruces de MACD y toques de bandas de Bollinger para confirmar entrada.
- Permite análisis multi-temporalidad para señales más robustas.
- Genera logs de señales y respaldo de datos.
- Incluye un archivo `.gitignore` que evita subir credenciales, datos históricos y artefactos generados.

## Requisitos

- Python 3.10 o superior.
- Dependencias en `requirements.txt`.

Instalación:

```powershell
python -m pip install -r requirements.txt
```

## Estructura del proyecto

- `bot/` — código principal del bot.
- `data/` — datos históricos y CSV de velas.
- `models/` — modelos JSON generados.
- `run_bot.py`, `main.py` — entradas para ejecutar funciones del bot.
- `.env.example` — ejemplo de variables de entorno.

## Configuración

Copia el archivo de ejemplo y actualiza tus credenciales locales:

```powershell
Copy-Item .env.example .env
```

Edita `.env` con tus datos:

```env
IQOPTION_EMAIL=tu@email.com
IQOPTION_PASSWORD=tu_password
TELEGRAM_BOT_TOKEN=token_de_botfather
TELEGRAM_CHAT_ID=tu_chat_id
```

## Uso rápido

### Backtest con datos históricos

```powershell
python .\run_bot.py backtest --csv data\sample_candles.csv
```

### Entrenar un modelo

```powershell
python .\run_bot.py train --csv data\sample_candles.csv --model models\trend_model.json
```

### Backtest con modelo

```powershell
python .\run_bot.py backtest --csv data\sample_candles.csv --model models\trend_model.json
```

### Modo en vivo (demo)

```powershell
python .\run_bot.py live --asset EURUSD --model models\EURUSD_1m_model.json
```

### Señales por consola o CSV

```powershell
python .\run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55
```

### Señales con Telegram

```powershell
python .\run_bot.py signals --asset EURUSD-OTC --model models\EURUSD_OTC_1m_5000_model.json --telegram --signal-lookback 15 --expiry-candles 2 --min-model-probability 0.55
```

### Descargar datos de IQ Option (opcional)

```powershell
python .\run_bot.py fetch-iq --asset EURUSD --timeframe 60 --count 1000 --output data\EURUSD_1m.csv
```

## Formato CSV esperado

El bot lee archivos CSV con columnas:

```csv
timestamp,open,high,low,close,volume
```

`timestamp` puede ser un Unix epoch o una fecha como `2026-05-08 10:00:00`.

## Lógica de trading

### Compra/CALL

- El precio está por encima de la EMA 200.
- El MACD cruza hacia arriba su señal.
- El precio toca o rompe la banda inferior de Bollinger.

### Venta/PUT

- El precio está por debajo de la EMA 200.
- El MACD cruza hacia abajo su señal.
- El precio toca o rompe la banda superior de Bollinger.

Si se usa un modelo entrenado, la señal debe superar la probabilidad mínima configurada.

## Advertencia

- Este repositorio es para investigación y pruebas.
- Usa primero datos históricos y cuenta demo.
- Nunca operes en real sin validar completamente tu estrategia.
- No es consejo financiero.
