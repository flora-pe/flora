# src/04_split.py
"""
Split estratificado 70/15/15 con prefijo Bacteria__/Fungi__ como etiqueta.
Genera data/splits/{train,val,test}/<clase>/*.jpg
"""
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
SPLITS = RAIZ / "data" / "splits"
SEED = 42
PROPORCIONES = (0.70, 0.15, 0.15)
