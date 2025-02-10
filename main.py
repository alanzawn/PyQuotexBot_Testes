import datetime

import pandas as pd
import asyncio
import time

from pyquotex.quotexapi.config import email, password
from pyquotex.quotexapi.stable_api import Quotex
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side


# Função para calcular as bandas de Bollinger
def calculate_bands(df, window=20, num_std=2):
    df['sma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upperBand'] = df['sma'] + (df['std'] * num_std)
    df['lowerBand'] = df['sma'] - (df['std'] * num_std)
    return df


# Função para fazer a operação de compra ou venda
async def buy_and_check_win(client, asset, direction, amount=55, duration=60):
    #check_connect, message = await client.connect()
    #if check_connect:
    #print("Current Balance: ", await client.get_balance())
    asset_name, asset_data = await client.get_available_asset(asset, force_open=True)
    if asset_data[2]:
        #print("OK: Asset is open.")
        print("Realizando operação")
        hj = datetime.datetime.now()
        segundo_atual = hj.second
        duration = round((60 - segundo_atual) / 5, None) * 5
        print("Duração: ", duration)
        status, buy_info = await client.buy(amount, asset_name, direction, duration)
        if status:
            print("Waiting for result...")
            if await client.check_win(buy_info["id"]):
                print(f"\nWin!!! \nWe won, buddy!!!")#\nProfit: R$ {await client.get_profit()}")
            else:
                print(f"\nLoss!!! \nWe lost, buddy!!!")#\nLoss: R$ {await client.get_profit()}")
        else:
            print("Operation failed!!!")
    else:
        print("ERRO: Asset is closed.")
    print("Current Balance: ", await client.get_balance())


# Função para monitorar cada ativo em tempo real
async def monitor_assets(client):
    offset = 3600  # em segundos
    period = 60  # em segundos
    codes_asset = await client.get_all_assets()

    # Loop para monitorar cada ativo
    for asset in codes_asset.keys():
        asset_name, asset_data = await client.get_available_asset(asset)
        if asset_data[2] and '/' in asset_data[1] and not 'BRL' in asset_data[1] and 'OTC' in asset_data[1]:
            print(f"Processando o ativo: {asset_name}...", end='\r', flush=True)

            # Coletar os candles em tempo real
            candles = await client.get_candles(asset, time.time(), offset, period)
            rates_frame = pd.DataFrame(candles)

            # Calcular as bandas de Bollinger e adicionar aos dados
            rates_frame = calculate_bands(rates_frame)

            # Análise de vela para identificar sinais de compra/venda
            latest_candle = rates_frame.iloc[-1]
            prev_candles = rates_frame.iloc[-5:-1]

            tick_volumes = prev_candles['ticks'].values

            # Condições para a compra
            if (latest_candle['low'] <= latest_candle['lowerBand'] and
                    latest_candle['close'] > latest_candle['open'] and
                    latest_candle['close'] > latest_candle['lowerBand'] and
                    latest_candle['ticks'] > tick_volumes[:3].mean()):
                await buy_and_check_win(client, asset, direction="call")
                break

            # Condições para a venda
            elif (latest_candle['high'] >= latest_candle['upperBand'] and
                  latest_candle['close'] < latest_candle['open'] and
                  latest_candle['close'] < latest_candle['upperBand'] and
                  latest_candle['ticks'] > tick_volumes[:3].mean()):
                await buy_and_check_win(client, asset, direction="put")
                break

        # Intervalo de tempo entre a verificação dos ativos
        #await asyncio.sleep(5)


# Função principal
async def main():
    client = Quotex(email=email, password=password)
    check_connect, message = await client.connect()
    if check_connect:
        print('Client conectado')
        print('iniciando monitoramento\n')
        # Monitorar os ativos em tempo real
        while True:
            hj = datetime.datetime.now()
            second = hj.second
            if second in [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 00]:
                await monitor_assets(client)
            #await asyncio.sleep(60)  # Intervalo entre os ciclos


# Executa a função assíncrona
asyncio.run(main())
