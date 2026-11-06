# EDA Potato Leaf Disease (AgML)
Imágenes: 3076 | corruptas: 0 | clases: 7
Desbalance (máx/mín): 748/68 = 11.0x
Duplicados exactos: 110 imágenes en 55 grupos | con clase distinta: 6
Casi idénticas (mismo dHash, incluye exactas): 118 imágenes en 58 grupos | con clase distinta: 6
Lista para revisar a mano: reports/casi_duplicados_potato.csv

## Por clase (medianas de tamaño y peso; medias de brillo y verdor)
```
               n  ancho_med  alto_med  kb_med  brillo  verde   pct
clase                                                             
Bacteria     569     1500.0    1500.0   201.6   124.3   21.1  18.5
Fungi        748     1500.0    1500.0   236.4   116.7   26.2  24.3
Healthy      201     1500.0    1500.0   268.5   120.2   30.4   6.5
Nematode      68     1500.0    1500.0   196.6   111.8   33.4   2.2
Pest         611     1500.0    1500.0   231.4   120.5   27.0  19.9
Phytopthora  347     1500.0    1500.0   253.3   127.1   19.8  11.3
Virus        532     1500.0    1500.0   237.2   121.8   34.2  17.3
```

## Tamaños más comunes (px)
```
ancho  alto
1500   1500    3076
```

## Modos de color
```
modo
RGB    3076
```

## Extensiones
```
ext
.jpg    3076
```