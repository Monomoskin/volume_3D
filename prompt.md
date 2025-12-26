**PROMPT LISTO PARA COPIAR**

I am working on a research project focused on estimating the volume and quality of bamboo callus tissue cultivated in Petri dishes. The system currently processes paired images of each sample: a TOP view image and a SIDE view image. We use Detectron2 with Mask R-CNN for instance segmentation, and we work with the following main classes:

- container_top (Petri dish in top view)
- container_side (Petri dish in side view)
- callus (top view segmentation of the callus tissue)
- cell_profile (side view profile of the callus, used to estimate height)

**Current workflow:**

1. From the SIDE image, the model segments the Petri dish (container_side) and the callus profile (cell_profile). Using the known physical height of the Petri dish as reference, we compute a pixel-to-millimeter calibration factor and estimate the real callus height in millimeters.
2. From the TOP image, the model segments the Petri dish (container_top) and the callus region. Using the known diameter of the dish, we compute the real area of the callus in mm².
3. Combining top area and side height, the system estimates callus volume in mm³ (and then converts to mL).
4. The system also predicts categorical callus quality labels such as “poor”, “normal”, and “good”.
5. The system produces visual outputs showing segmentation overlays, class names, and numerical measurements, along with structured CSV outputs.

**Planned improvement:**
We want to enhance the quality analysis. Instead of only classifying the callus as “poor”, “normal”, or “good”, we want the model to:

- Segment defective regions inside the callus explicitly.
- Introduce a new class such as “defective_region” in Mask R-CNN annotations.
- Compute the defective percentage as:
  (area of defective_region / total callus area) \* 100
- Provide a continuous quality score or damage percentage rather than only categorical labels.
- Visually highlight defective regions in the output images.
- Optionally, associate the defective mask with the corresponding callus instance, so the system knows which defect belongs to which callus sample.

Assume Detectron2 + Mask R-CNN continues to be the core framework.
Given this description, propose the best methodology for implementing this improvement, including annotation strategy, model training considerations, quality metric design, and integration workflow with the existing pipeline.
