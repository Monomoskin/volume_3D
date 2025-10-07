`train.py` es el script que enseña a tu modelo a reconocer y segmentar los objetos en las imágenes. Es el proceso de **entrenamiento del modelo**. Lo que hace es tomar tus datos anotados (el `coco_annotations.json` y las imágenes) y le permite al modelo "aprender" a identificar patrones para detectar el frasco y las células por sí mismo.

### 🇪🇸 Español

### ¿Qué hace el script `train.py`?

El script `train.py` es el motor del proyecto, encargado de entrenar el modelo de inteligencia artificial. Su función principal es enseñar a una red neuronal a reconocer los objetos de interés (`frasco` y `célula`) basándose en las anotaciones que tú creaste.

El proceso se puede resumir en los siguientes pasos:

1.  **Registro del Dataset**: Primero, el script le indica a Detectron2 dónde se encuentran tus datos. Le dice que el conjunto de imágenes se llama `celulas_frascos` y que sus anotaciones están en el archivo `coco_annotations.json`.
2.  **Configuración del Modelo**: Carga una arquitectura de modelo pre-entrenada, como **Mask R-CNN**, que es ideal para la segmentación de instancias. Luego, ajusta los parámetros de configuración para tu tarea, como el número de clases (`frasco` y `célula`), la tasa de aprendizaje y el número de iteraciones de entrenamiento.
3.  **Entrenamiento**: El script inicia el proceso de entrenamiento. La red neuronal comienza a procesar tus imágenes, ajustando sus "pesos" internos para minimizar el error entre lo que predice y las anotaciones reales que le proporcionaste.
4.  **Guardado del Modelo**: Una vez que el entrenamiento termina (después de 300 iteraciones en este caso), el script guarda el modelo final entrenado como un archivo llamado `model_final.pth` en la carpeta `output`. Este archivo es el "cerebro" que usarás más tarde en el script `predict.py` para hacer las detecciones automáticas.

---

### 🇺🇸 English

### What does the `train.py` script do?

The `train.py` script is the engine of the project, responsible for training the artificial intelligence model. Its main function is to teach a neural network to recognize objects of interest (`flask` and `cell`) based on the annotations you created.

The process can be summarized in the following steps:

1.  **Dataset Registration**: First, the script tells Detectron2 where your data is located. It tells it that the image set is called `celulas_frascos` and that its annotations are in the `coco_annotations.json` file.
2.  **Model Configuration**: It loads a pre-trained model architecture, such as **Mask R-CNN**, which is ideal for instance segmentation. It then adjusts the configuration parameters for your task, such as the number of classes (`flask` and `cell`), the learning rate, and the number of training iterations.
3.  **Training**: The script begins the training process. The neural network starts processing your images, adjusting its internal "weights" to minimize the error between what it predicts and the actual annotations you provided.
4.  **Saving the Model**: Once training is complete (after 300 iterations in this case), the script saves the final trained model as a file named `model_final.pth` in the `output` folder. This file is the "brain" you will later use in the `predict.py` script to perform automatic detections.

---

### 🇨🇳 中文

### `train.py` 脚本的作用是什么？

`train.py` 脚本是该项目的核心，负责训练人工智能模型。它的主要功能是基于您创建的注释，教神经网络识别感兴趣的对象（`flask` 和 `cell`）。

整个过程可以概括为以下步骤：

1.  **数据集注册**：首先，脚本告诉 Detectron2 您的数据在哪里。它指定图像集名为 `celulas_frascos`，其注释位于 `coco_annotations.json` 文件中。
2.  **模型配置**：它加载一个预训练的模型架构，例如 **Mask R-CNN**，这非常适合实例分割任务。然后，它根据您的任务调整配置参数，例如类的数量（`flask` 和 `cell`）、学习率和训练迭代次数。
3.  **训练**：脚本启动训练过程。神经网络开始处理您的图像，调整其内部的“权重”，以最小化其预测结果与您提供的真实注释之间的误差。
4.  **保存模型**：训练完成后（本例中为 300 次迭代），脚本会将训练好的最终模型保存为 `output` 文件夹中的 `model_final.pth` 文件。该文件是您稍后在 `predict.py` 脚本中用于执行自动检测的“大脑”。
