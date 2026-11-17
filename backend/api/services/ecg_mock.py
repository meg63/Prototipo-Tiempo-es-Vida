import time
import random

def procesar_ecg_simulado(archivo_path):
    """
    Simula el tiempo de procesamiento de la IA (meta: < 3 minutos) y 
    devuelve probabilidades mockeadas por superclase PTB-XL.
    """
    time.sleep(3) # Simulación de procesamiento
    
    return {
        "NORM": round(random.uniform(0.1, 0.9), 2),
        "MI": round(random.uniform(0.01, 0.5), 2),
        "STTC": round(random.uniform(0.01, 0.4), 2),
        "CD": round(random.uniform(0.01, 0.3), 2),
        "HYP": round(random.uniform(0.01, 0.3), 2)
    }