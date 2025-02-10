import datetime
import pandas as pd
import asyncio
import time

from pyquotex.quotexapi.config import password, email
from pyquotex.quotexapi.stable_api import Quotex


# Função para calcular as bandas de Bollinger
def calculate_bands(df, window=20, num_std=2):
    df['sma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upperBand'] = df['sma'] + (df['std'] * num_std)
    df['lowerBand'] = df['sma'] - (df['std'] * num_std)
    return df


# Função para operar
async def buy_and_check_win(client, asset, direction, amount=55, duration=60):
    try:
        asset_name, asset_data = await client.get_available_asset(asset, force_open=True)
        if asset_data[2]:
            print(f"📊 Operação em {asset} - Direção: {direction.upper()}")
            hj = datetime.datetime.now()
            segundo_atual = hj.second
            duration = round((60 - segundo_atual) / 5, None) * 5
            print(f"⏳ Duração: {duration}")

            status, buy_info = await client.buy(amount, asset_name, direction, duration)
            if status:
                print("✅ Aguardando resultado...")
                win = await client.check_win(buy_info["id"])
                print("🏆 WIN!" if win else "❌ LOSS!")
            else:
                print("⚠️ Falha ao executar operação")
        else:
            print(f"❌ {asset} está fechado.")
    except Exception as e:
        print(f"⚠️ ERRO em buy_and_check_win para {asset}: {e}")


# Função que monitora um único ativo em loop infinito
async def monitor_single_asset(client, asset):
    offset = 3600  # Tempo de análise
    period = 60  # Período das velas

    while True:
        try:
            asset_name, asset_data = await client.get_available_asset(asset)
            if asset_data[2] and '/' in asset_data[1] and 'BRL' not in asset_data[1] and 'OTC' in asset_data[1]:
                print(f"🔍 Monitorando {asset_name}...")

                # Coletar candles
                candles = await client.get_candles(asset, time.time(), offset, period)
                rates_frame = pd.DataFrame(candles)
                rates_frame = calculate_bands(rates_frame)

                # Análise de vela para identificar sinais
                latest_candle = rates_frame.iloc[-1]
                prev_candles = rates_frame.iloc[-5:-1]
                tick_volumes = prev_candles['ticks'].values

                if (latest_candle['low'] <= latest_candle['lowerBand'] and
                        latest_candle['close'] > latest_candle['open'] and
                        latest_candle['close'] > latest_candle['lowerBand'] and
                        latest_candle['ticks'] > tick_volumes[:3].mean()):
                    await buy_and_check_win(client, asset, direction="call")

                elif (latest_candle['high'] >= latest_candle['upperBand'] and
                      latest_candle['close'] < latest_candle['open'] and
                      latest_candle['close'] < latest_candle['upperBand'] and
                      latest_candle['ticks'] > tick_volumes[:3].mean()):
                    await buy_and_check_win(client, asset, direction="put")

        except Exception as e:
            print(f"⚠️ Erro no monitoramento do ativo {asset}: {e}")

        await asyncio.sleep(5)  # Pequena pausa para evitar sobrecarga


# Criar tarefas para monitorar todos os ativos
async def monitor_assets(client):
    codes_asset = await client.get_all_assets()
    tasks = []

    for asset in codes_asset.keys():
        task = asyncio.create_task(monitor_single_asset(client, asset))  # Criar uma tarefa independente para cada ativo
        tasks.append(task)

    await asyncio.gather(*tasks)  # Roda todas as tarefas de forma assíncrona e contínua


# Função principal
async def main():
    client = Quotex(email=email, password=password)
    check_connect, message = await client.connect()
    if check_connect:
        print('✅ Cliente conectado\n🚀 Iniciando monitoramento...')
        await monitor_assets(client)  # Agora os ativos são monitorados continuamente


# Executa a função assíncrona
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🚪 Encerrando monitoramento...")
