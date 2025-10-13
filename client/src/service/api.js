import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000, // 30 segundos
});

// Función de utilidad para manejar la respuesta del servidor
const handleResponse = (response) => {
  // Flask devuelve un mensaje si la lista está vacía.
  if (
    response.data &&
    response.data.message &&
    response.data.message.includes("No hay estimaciones")
  ) {
    return [];
  }
  return response.data;
};

// -------------------------------------------------------------------
// 1. ENDPOINT DE PROCESAMIENTO (analyzeSample)
// -------------------------------------------------------------------

/**
 * Realiza la petición POST al backend de Flask para analizar la muestra.
 * * @param {object} data - Datos del formulario (cellName, idCode, photoDate).
 * @param {File} topFile - Archivo de imagen de la vista TOP.
 * @param {File} sideFile - Archivo de imagen de la vista SIDE.
 * @returns {Promise<object>} Objeto de respuesta JSON del backend con volumen y URLs.
 */
export const analyzeSample = async (data, topFile, sideFile) => {
  const endpoint = "/analyze";
  const formData = new FormData();

  // Datos del formulario
  formData.append("cell_name", data.cellName);
  formData.append("id_code", data.idCode);
  formData.append("photo_date", data.photoDate.format("YYYY-MM-DD"));

  // Archivos de imagen
  formData.append("image_top", topFile);
  formData.append("image_side", sideFile);

  try {
    // Axios maneja automáticamente el 'Content-Type': 'multipart/form-data' con FormData.
    const response = await api.post(endpoint, formData);
    return response.data;
  } catch (error) {
    // Axios centraliza la respuesta de error en error.response
    const errorMessage =
      error.response?.data?.error ||
      error.message ||
      "Unknown error during analysis.";

    console.error("Error during API call analyzeSample:", error);
    // Lanzar el mensaje de error para que el componente lo maneje
    throw new Error(errorMessage);
  }
};

// -------------------------------------------------------------------
// 2. ENDPOINTS DE LECTURA DE DATOS (Estimations)
// -------------------------------------------------------------------

/**
 * Obtiene la lista de todas las estimaciones registradas.
 * * @returns {Promise<Array<object>>} Lista de todas las estimaciones (ordenadas de más reciente a más antigua).
 */
export const getAllEstimations = async () => {
  const endpoint = "/estimations";
  try {
    const response = await api.get(endpoint);
    return handleResponse(response);
  } catch (error) {
    console.error("Error fetching all estimations:", error);
    // Si hay un error 404 de Flask por endpoint no encontrado, etc.
    throw new Error(error.response?.data?.message || error.message);
  }
};

/**
 * Obtiene las 10 últimas estimaciones registradas.
 * * @returns {Promise<Array<object>>} Lista de las 10 estimaciones más recientes.
 */
export const getLatestEstimations = async () => {
  const endpoint = "/estimations/latest";
  try {
    const response = await api.get(endpoint);
    return handleResponse(response);
  } catch (error) {
    console.error("Error fetching latest estimations:", error);
    throw new Error(error.response?.data?.message || error.message);
  }
};

/**
 * Obtiene el historial de mediciones para una célula específica.
 * * @param {string} cellName - El nombre exacto de la célula (Ej: 'Cell Alpha').
 * @returns {Promise<Array<object>>} Historial de mediciones de la célula.
 */
export const getCellHistory = async (cellName) => {
  // Codificación automática del nombre de la célula para la URL
  const endpoint = `/estimations/${encodeURIComponent(cellName)}`;

  try {
    const response = await api.get(endpoint);
    return handleResponse(response);
  } catch (error) {
    // Manejo específico del 404 (célula no encontrada)
    if (error.response && error.response.status === 404) {
      return []; // Devolver array vacío en lugar de lanzar error
    }
    console.error(`Error fetching history for cell ${cellName}:`, error);
    throw new Error(error.response?.data?.message || error.message);
  }
};

// -------------------------------------------------------------------
// 3. NUEVO ENDPOINT DE RESUMEN POR CÉLULA
// -------------------------------------------------------------------

/**
 * Obtiene un resumen de las métricas clave para cada célula registrada.
 * Incluye: última estimación, conteo y fecha.
 * @returns {Promise<Array<object>>} Lista de objetos de resumen por célula.
 */
export const getEstimationsSummary = async () => {
  const endpoint = "/estimations/summary";
  try {
    const response = await api.get(endpoint);
    // No usamos handleResponse porque el endpoint devuelve [] si está vacío
    return response.data;
  } catch (error) {
    console.error("Error fetching estimations summary:", error);
    throw new Error(error.response?.data?.message || error.message);
  }
};
