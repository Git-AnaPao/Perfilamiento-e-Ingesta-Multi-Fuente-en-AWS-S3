"""Práctica 1: Perfilamiento e Ingesta Multi-Fuente en AWS S3 con Python.

Descarga archivos CSV y JSON desde un bucket de AWS S3 directamente a memoria
(io.BytesIO, sin escribir a disco) y genera un perfilamiento básico con pandas.

Credenciales: este script NO contiene claves. boto3 las toma de las variables de
entorno AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y AWS_SESSION_TOKEN, o del archivo
~/.aws/credentials (credenciales temporales de AWS Academy).
"""
import io
import json
import os
import random
from datetime import datetime, timedelta

import boto3
import pandas as pd

# 1. Cliente Boto3 (las credenciales se resuelven con la cadena predeterminada de boto3)
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'aws-academy-datacenter-bucket-23-02-004')
s3_client = boto3.client('s3', region_name='us-east-1')


def generar_y_subir_logs_json(file_key='raw/logs_m2m.json', num_registros=300):
    """Genera logs sintéticos M2M (Machine to Machine) en formato JSON y los sube a S3."""
    print(f'=== Generando datos sintéticos para {file_key} ===')
    random.seed(101)

    niveles = ['INFO', 'WARNING', 'ERROR', 'SUCCESS']
    eventos = ['DEVICE_HEARTBEAT', 'DATA_SYNC', 'CONNECTION_FAILED', 'FIRMWARE_UPDATE', 'SENSOR_READ']
    dispositivos = [f'DEV-M2M-{i:03d}' for i in range(1, 21)]

    fecha_base = datetime.now() - timedelta(days=7)
    logs = []

    for i in range(1, num_registros + 1):
        timestamp = fecha_base + timedelta(seconds=random.randint(0, 7 * 24 * 3600))
        logs.append({
            'log_id': f'LOG-{10000 + i}',
            'timestamp': timestamp.isoformat(),
            'device_id': random.choice(dispositivos),
            'ip_address': f'192.168.1.{random.randint(10, 250)}',
            'level': random.choice(niveles),
            'event': random.choice(eventos),
            'metrics': {
                'cpu_usage_pct': round(random.uniform(5.0, 99.0), 2),
                'latency_ms': random.randint(10, 450),
                'bytes_sent': random.randint(128, 65536),
            },
        })

    json_bytes = json.dumps(logs, indent=2).encode('utf-8')

    print(f'Subiendo {num_registros} logs M2M a s3://{BUCKET_NAME}/{file_key}...')
    s3_client.put_object(Bucket=BUCKET_NAME, Key=file_key, Body=json_bytes)
    print('¡Archivo JSON generado y subido correctamente!\n')


def cargar_y_perfilar_s3(file_key, is_json=False):
    """Descarga archivos desde S3 y genera un perfilamiento básico de tipos de datos."""
    print(f'=== Procesando objeto S3: {file_key} ===')
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
        body = response['Body'].read()  # bytes en memoria

        if is_json:
            data_json = json.loads(body.decode('utf-8'))
            df = pd.json_normalize(data_json)  # aplana el objeto anidado "metrics"
        else:
            df = pd.read_csv(io.BytesIO(body))  # sin guardar a disco

        print(f'Dimensiones del dataset: {df.shape[0]} filas x {df.shape[1]} columnas')
        print('\nPerfil de Tipos de Datos e Identificación de Tipos:')
        print(df.dtypes)
        print('\nResumen de Estadísticos Descriptivos (Cuantitativos):')
        print(df.describe().T)
        print('-' * 60 + '\n')
        return df

    except s3_client.exceptions.NoSuchKey:
        print(f"ERROR: El archivo '{file_key}' no fue encontrado en el bucket '{BUCKET_NAME}'.\n")
        return None
    except Exception as e:
        print(f'ERROR al procesar {file_key}: {str(e)}\n')
        return None


if __name__ == '__main__':
    # 1. Crear y subir el archivo raw/logs_m2m.json faltante
    generar_y_subir_logs_json(file_key='raw/logs_m2m.json', num_registros=300)

    # 2. Cargar y perfilar ambos archivos desde S3
    df_transacciones = cargar_y_perfilar_s3('raw/transacciones.csv')
    df_logs = cargar_y_perfilar_s3('raw/logs_m2m.json', is_json=True)
