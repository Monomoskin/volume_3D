¡Excelente idea! La descripción actual del `predict.py` es la de un proyecto 2D. Necesitas actualizar esta documentación crucial para que refleje la **estrategia 3D de doble imagen** y la **calibración dinámica dual** que hemos implementado.

Aquí tienes la versión revisada de tu documentación, destacando los cambios metodológicos clave.

---

# Documentación Revisada: El Script `predict.py`

### 🇪🇸 Español

### ¿Cómo funciona el script `predict.py`?

El script `predict.py` ha sido refactorizado para implementar la estrategia de **Visión 3D por Doble Imagen**, eliminando las suposiciones de altura fija y proporcionando mediciones de volumen reales.

El flujo de trabajo opera sobre **pares de imágenes vinculadas** (`*_TOP.jpg` y `*_SIDE.jpg`) y se divide en cuatro etapas principales:

---

### 1. Extracción de Datos y Calibración $Z$ (Vista de Perfil - `*_SIDE.jpg`) 📏

Esta etapa establece la **escala vertical** de la escena:

- **Detección y Calibración:** El script procesa la imagen `_SIDE.jpg` y detecta la máscara del contenedor. Utiliza la **Altura Real del Frasco (constante)** y la **Altura Detectada en Píxeles** para calcular un **Factor de Conversión $Z$** ($\frac{\text{mm}}{\text{píxel}}$).
- **Medición de la Altura Real:** Detecta la máscara de la muestra (`cell_profile`) en la vista lateral. Mide la altura de esta máscara en píxeles y la convierte a la **Altura Real ($\text{Altura } Z$) en milímetros** utilizando el Factor $Z$ calculado dinámicamente.

### 2. Extracción de Datos y Calibración $XY$ (Vista Superior - `*_TOP.jpg`) 📐

Esta etapa establece la **escala horizontal** de la escena:

- **Detección y Calibración:** El script procesa la imagen `_TOP.jpg` y detecta la máscara del contenedor. Utiliza el **Diámetro Real del Frasco (constante)** y el **Ancho Detectado en Píxeles** para calcular un **Factor de Conversión $XY$** ($\frac{\text{mm}^2}{\text{píxel}^2}$).
- **Medición del Área:** Detecta la máscara de la muestra (`cell`) en la vista superior, calcula su área en píxeles y la convierte al **Área Base Real ($\text{Área } XY$) en $\text{mm}^2$** utilizando el Factor $XY$ calculado dinámicamente.

### 3. Cálculo del Volumen 3D Real 📊

Con ambas mediciones reales en mano, el volumen se calcula de forma precisa para cada célula:

- **Fórmula:** Multiplica el **Área Base Real ($\text{Área } XY$)** obtenida de la vista superior por la **Altura Real ($\text{Altura } Z$)** obtenida de la vista de perfil.
  $$\text{Volumen} = \text{Área } XY \times \text{Altura } Z$$
- **Resultados:** Genera una tabla con el volumen final en $\text{mL}$, junto con las componentes de $\text{Área}$ y $\text{Altura}$ para la trazabilidad de la medición.

### 4. Consolidación y Visualización ✨

- **Visualización:** Dibuja los contornos de las células y muestra el volumen calculado (`X.XXX mL`) en la imagen **TOP** (la imagen principal para el reporte).
- **Reporte:** Guarda los resultados de la muestra en un archivo CSV individual y luego **consolida** todos los resultados en un archivo maestro (`all_volumes_summary.csv`) para el análisis final.

---

### 🇺🇸 English

### How the `predict.py` script works

The `predict.py` script has been refactored to implement the **3D Dual-Image Vision strategy**, eliminating fixed height assumptions and providing real, accurate volume measurements.

The workflow operates on **linked image pairs** (`*_TOP.jpg` and `*_SIDE.jpg`) and is divided into four main stages:

---

### 1. Data Extraction and $Z$ Calibration (Side View - `*_SIDE.jpg`) 📏

This stage establishes the **vertical scale** of the scene:

- **Detection and Calibration:** The script processes the `_SIDE.jpg` image and detects the container mask. It uses the **Real Flask Height (constant)** and the **Detected Height in Pixels** to calculate a **$Z$ Conversion Factor** ($\frac{\text{mm}}{\text{pixel}}$).
- **Real Height Measurement:** It detects the sample mask (`cell_profile`) in the side view. It measures the height of this mask in pixels and converts it to the **Real Height ($\text{Height } Z$) in millimeters** using the dynamically calculated $Z$ Factor.

### 2. Data Extraction and $XY$ Calibration (Top View - `*_TOP.jpg`) 📐

This stage establishes the **horizontal scale** of the scene:

- **Detection and Calibration:** The script processes the `_TOP.jpg` image and detects the container mask. It uses the **Real Flask Diameter (constant)** and the **Detected Width in Pixels** to calculate an **$XY$ Conversion Factor** ($\frac{\text{mm}^2}{\text{pixel}^2}$).
- **Area Measurement:** It detects the sample mask (`cell`) in the top view, calculates its area in pixels, and converts it to the **Real Base Area ($\text{Area } XY$) in $\text{mm}^2$** using the dynamically calculated $XY$ Factor.

### 3. Real 3D Volume Calculation 📊

With both real-world measurements in hand, the volume is precisely calculated for each cell:

- **Formula:** It multiplies the **Real Base Area ($\text{Area } XY$)** obtained from the top view by the **Real Height ($\text{Height } Z$)** obtained from the side view.
  $$\text{Volume} = \text{Area } XY \times \text{Height } Z$$
- **Results:** It generates a table with the final volume in $\text{mL}$, along with the $\text{Area}$ and $\text{Height}$ components for measurement traceability.

### 4. Consolidation and Visualization ✨

- **Visualization:** It draws the cell contours and displays the calculated volume (`X.XXX mL`) on the **TOP** image (the main image for the report).
- **Reporting:** It saves the sample results in an individual CSV file and then **consolidates** all results into a master file (`all_volumes_summary.csv`) for final analysis.
