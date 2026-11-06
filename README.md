# Flora 🌱

Detección de enfermedades y plagas en hojas de papa para aplicar pesticidas solo donde se necesita.

## Datos

Las imágenes no se versionan. Para descargarlas:

    pip install -r requirements.txt
    ./scripts/download_data.sh

Quedan en `data/raw/potato_agml/`, una carpeta por clase.

**Dataset:** [Potato Leaf Disease Classification](https://huggingface.co/datasets/Project-AgML/potato_leaf_disease_classification) (AgML), licencia CC-BY-4.0. 3,076 fotos de campo (1500×1500 px) tomadas con celular en cultivos de Java Central, Indonesia.

| Clase | Imágenes |
|---|---|
| Bacteria | 569 |
| Fungi | 748 |
| Healthy | 201 |
| Nematode | 68 |
| Pest | 611 |
| Phytopthora | 347 |
| Virus | 532 |

Viene en un solo split, así que el train/val/test lo armamos nosotros (estratificado). Está desbalanceado: Nematode tiene solo 68 imágenes.

Cita: Shabrina et al. (2024), *A novel dataset of potato leaf disease in uncontrolled environment*, Data in Brief 52, 109955.

Los datasets evaluados y descartados están documentados en [`archive/`](archive/).

## Limpieza y split

`python scripts/make_splits.py` genera `splits/potato_splits.csv` (train/val/test 70/15/15, estratificado, semilla 42). Excluye 66 imágenes: 54 duplicados exactos y 12 con la misma foto en dos clases distintas (ver `splits/excluidas.csv`). Todos entrenamos con este CSV, no con splits propios. Detalle del análisis en `reports/eda_potato_agml.md`.
