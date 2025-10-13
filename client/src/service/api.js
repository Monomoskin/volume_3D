const BACKEND_URL = "http://localhost:5000/api/analyze";

/**
 * Realiza la petición POST al backend de Flask para analizar la muestra.
 * @param {object} data - Datos del formulario (código, nombre, fecha).
 * @param {File} topFile - Archivo de imagen de la vista TOP.
 * @param {File} sideFile - Archivo de imagen de la vista SIDE.
 * @returns {Promise<object>} El objeto de respuesta JSON del backend.
 */
export const analyzeSample = async (data, topFile, sideFile) => {
  const formData = new FormData();

  // 1. Datos del formulario
  formData.append("cell_name", data.cellName);
  formData.append("id_code", data.idCode); // Opcional, pero se envía
  formData.append("photo_date", data.photoDate.format("YYYY-MM-DD")); // Formatear díajs

  // 2. Archivos de imagen
  // Los nombres deben coincidir con lo que espera Flask (request.files['image_top'])
  formData.append("image_top", topFile);
  formData.append("image_side", sideFile);

  try {
    const response = await fetch(BACKEND_URL, {
      method: "POST",
      // No necesitamos establecer 'Content-Type': 'multipart/form-data',
      // ya que FormData lo maneja automáticamente.
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || `HTTP error! Status: ${response.status}`
      );
    }

    return response.json();
  } catch (error) {
    console.error("Error during API call to analyzeSample:", error);
    throw error;
  }
};
