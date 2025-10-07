###PREDICT FILE

### 🇪🇸 Español

### ¿Cómo funciona el script `predict.py`?

El script `predict.py` es la pieza clave para aplicar tu modelo entrenado a nuevas imágenes y obtener los volúmenes de las células. Funciona en tres etapas principales: predicción, calibración y cálculo.

1.  **Predicción y Visualización** ✨
    El script carga tu modelo entrenado (`model_final.pth`). Cuando le pasas una nueva imagen, el modelo la analiza y te devuelve una lista de objetos detectados (el frasco y cada célula individual), con sus respectivas **máscaras de segmentación** y puntuaciones de confianza. El script también usa una función de visualización para dibujar los contornos de estas máscaras directamente sobre la imagen, lo que te permite verificar visualmente la precisión del modelo.

2.  **Calibración de Escala con el Frasco** 📏
    Para pasar de las mediciones en píxeles a unidades reales (como milímetros), el script utiliza el frasco como referencia. Busca la máscara del frasco en las predicciones, calcula su área en píxeles, y la compara con el área real conocida del frasco (basada en su diámetro). Esto le permite determinar un **factor de conversión** de píxeles a milímetros cuadrados.

3.  **Cálculo del Volumen** 📊
    Finalmente, el script itera sobre cada máscara de célula detectada. Para cada una, hace lo siguiente:
    - Calcula el área de la célula en píxeles.
    - Convierte el área de píxeles a milímetros cuadrados usando el factor de conversión del frasco.
    - Estima el volumen multiplicando el área real por una altura celular predefinida (ej. 0.05 mm), obteniendo un volumen en milímetros cúbicos para cada célula.

---

### 🇺🇸 English

### How the `predict.py` script works

The `predict.py` script is the key component for applying your trained model to new images and getting the cell volumes. It operates in three main stages: prediction, calibration, and calculation.

1.  **Prediction and Visualization** ✨
    The script loads your trained model (`model_final.pth`). When you feed it a new image, the model analyzes it and returns a list of detected objects (the flask and each individual cell), along with their respective **segmentation masks** and confidence scores. The script also uses a visualization function to draw the contours of these masks directly onto the image, allowing you to visually verify the model's accuracy.

2.  **Scale Calibration with the Flask** 📏
    To convert measurements from pixels to real-world units (like millimeters), the script uses the flask as a reference. It finds the flask's mask in the predictions, calculates its area in pixels, and compares it to the flask's known real-world area (based on its diameter). This allows it to determine a **conversion factor** from pixels to square millimeters.

3.  **Volume Calculation** 📊
    Finally, the script iterates over each detected cell mask. For each one, it does the following:
    - Calculates the cell's area in pixels.
    - Converts the pixel area to square millimeters using the flask's conversion factor.
    - Estimates the volume by multiplying the real-world area by a predefined cell height (e.g., 0.05 mm), obtaining a volume in cubic millimeters for each cell.

---

### 🇨🇳 中文

### `predict.py` 脚本的工作原理

`predict.py` 脚本是您的核心组件，用于将训练好的模型应用于新图像并计算细胞体积。它的工作主要分为三个阶段：预测、校准和计算。

1.  **预测与可视化** ✨
    脚本加载您训练好的模型（`model_final.pth`）。当您提供一张新图像时，模型会对其进行分析，并返回一个包含所有检测到对象（培养瓶和每个细胞）的列表，以及它们各自的**分割掩码**和置信度分数。脚本还使用可视化功能，直接在图像上绘制这些掩码的轮廓，让您可以直观地验证模型的准确性。

2.  **使用培养瓶进行比例校准** 📏
    为了将像素测量值转换为现实世界的单位（如毫米），脚本使用培养瓶作为参考。它在预测结果中找到培养瓶的掩码，计算其像素面积，并将其与培养瓶已知的真实面积（基于其直径）进行比较。这使得它能够确定一个从像素到平方毫米的**转换因子**。

3.  **体积计算** 📊
    最后，脚本遍历每个检测到的细胞掩码。对于每一个细胞，它执行以下操作：
    - 计算细胞的像素面积。
    - 使用培养瓶的转换因子将像素面积转换为平方毫米。
    - 通过将实际面积乘以预先定义的细胞高度（例如，0.05 毫米），来估算体积，从而为每个细胞获得以立方毫米为单位的体积。
