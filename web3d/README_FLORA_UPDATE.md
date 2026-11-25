# FLORA Vision 3D — refinamiento y despliegue

- Actualiza el favicon y los iconos instalables con el isotipo FLORA.
- Quita el indicador de desarrollo de Next.js, sin alterar el renderizado Three.js.
- Evita recortes del logo lateral y adapta el layout a escritorio, tablet y móvil.
- Cambia «Acerca de FLORA» por una explicación orientada a usuarios finales.
- Incluye Dockerfile web3d multietapa y script de despliegue guardado en `web3d/scripts/`.
- **No** altera las rutas `src/app/api/*` ni el modelo Keras, ni modifica GCP al instalar.

El script `scripts/deploy-web3d.sh` **no despliega** sin `--deploy`, requiere commit previo,
y valida la API mediante `/api/ready`, con intento de rollback si falla.

Probar por pantalla a 375/390/430/768/1024/1440 px antes de hacer commit.
La confianza del modelo no es severidad. El control del visor es una intensidad gráfica.
