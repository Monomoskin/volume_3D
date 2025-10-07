### 📄 Documentación del Proyecto: Estimación de Volumen Celular Automático

### 1. Objetivo del Proyecto

El objetivo principal de este proyecto es **automatizar la estimación del volumen de células** a partir de imágenes microscópicas de frascos de cultivo. Esto se logra mediante el uso de la visión por computadora y el aprendizaje profundo para reemplazar el tedioso y propenso a errores proceso de medición manual.

---

### 2. Componentes Clave

El proyecto se basa en tres scripts principales que trabajan de forma secuencial:

- **`xml_to_coco.py`**: Este script actúa como un **conversor de datos**. Transforma las anotaciones manuales del formato XML de CVAT al formato estándar **COCO JSON**. Esto es crucial porque los modelos de IA requieren datos en un formato estructurado y uniforme para poder entrenarse.

- **`train.py`**: Este script es el **motor del proyecto**. Se encarga de **entrenar un modelo de inteligencia artificial**. Utiliza la arquitectura **Mask R-CNN**, que es ideal para la segmentación de instancias. El entrenamiento se realiza a través de un proceso llamado **aprendizaje por transferencia**, que consiste en usar un modelo pre-entrenado (una red **ResNet-50** que ya conoce patrones básicos) y ajustarlo con nuestras propias imágenes de células y frascos. Esto nos permite lograr alta precisión con un conjunto de datos limitado y en un tiempo reducido.

- **`predict.py`**: Este script es la **herramienta de aplicación**. Utiliza el modelo entrenado para procesar nuevas imágenes y realizar las dos tareas principales del proyecto:
  1.  **Detección y Visualización**: Genera una máscara de segmentación precisa para cada frasco y cada célula, lo cual es la base para las mediciones. Además, visualiza estas detecciones en la imagen original para una validación instantánea.
  2.  **Calibración y Cálculo**: Utiliza el área en píxeles del frasco (cuya dimensión real es conocida) para calibrar la escala de la imagen. Con este factor de conversión, calcula el área real de cada célula en milímetros cuadrados y, asumiendo una altura promedio, estima su volumen final.

---

### 3. Flujo de Trabajo

El proceso se puede resumir en los siguientes pasos:

1.  **Anotación de Datos**: Anotaciones manuales de los frascos (elipses) y las células (polígonos) en CVAT.
2.  **Conversión**: Ejecución de `xml_to_coco.py` para generar el archivo `coco_annotations.json`.
3.  **Entrenamiento**: Ejecución de `train.py` para entrenar el modelo, que crea el archivo `model_final.pth`. Este paso requiere una conexión a internet para descargar el modelo base.
4.  **Predicción**: Ejecución de `predict.py` en una nueva imagen para obtener las máscaras, la visualización y el cálculo de volumen de cada célula.

---

### 4. Tecnologías y Herramientas

- **Python**: El lenguaje de programación utilizado.
- **PyTorch**: Un framework de aprendizaje automático que actúa como la base de todo el sistema.
- **Detectron2**: Una librería de Facebook AI Research construida sobre PyTorch, que simplifica el desarrollo de proyectos de visión por computadora.
- **Mask R-CNN**: La arquitectura de la red neuronal empleada para la segmentación.
- **ResNet-50**: La red neuronal que forma el "esqueleto" de Mask R-CNN, pre-entrenada para una mayor eficiencia.
- **CVAT**: La herramienta de software utilizada para la anotación manual de imágenes.

Este enfoque automatizado no solo ofrece resultados consistentes y replicables, sino que también libera tiempo y recursos que pueden ser invertidos en tareas más complejas.
