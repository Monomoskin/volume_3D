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
 * @param {object} payload - Datos mínimos: { cell_name: string, [test_date]: string (opcional) }
 * @param {File} topFile - Archivo de imagen de la vista TOP.
 * @param {File} sideFile - Archivo de imagen de la vista SIDE.
 * @returns {Promise<object>} Objeto de respuesta JSON del backend (volumen, altura, URLs múltiples, etc.)
 */
export const analyzeSample = async (payload, topFile, sideFile) => {
  const endpoint = "/analyze";
  const formData = new FormData();

  // 1. Campo obligatorio: cell_name
  if (!payload.cell_name) {
    throw new Error("cell_name es requerido");
  }
  formData.append("cell_name", payload.cell_name);

  // 2. Campo opcional: test_date (solo si existe)
  if (payload.test_date) {
    // Acepta formato "YYYY-MM-DD" o "YYYY-MM-DD HH:mm:ss"
    formData.append("test_date", payload.test_date);
    console.log("[DEBUG analyzeSample] Enviando test_date:", payload.test_date);
  }

  // 3. Archivos obligatorios
  if (!topFile || !sideFile) {
    throw new Error("Faltan archivos de imagen (top y/o side)");
  }
  formData.append("image_top", topFile);
  formData.append("image_side", sideFile);

  try {
    const response = await api.post(endpoint, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    console.log("[DEBUG analyzeSample] Respuesta exitosa:", response.data);
    return response.data;
  } catch (error) {
    // Manejo mejorado de errores
    let errorMessage = "Error desconocido al analizar la muestra.";

    if (error.response) {
      // El backend devolvió un error (400, 500, etc.)
      errorMessage =
        error.response.data?.error ||
        error.response.data?.message ||
        `Error ${error.response.status}: ${error.response.statusText}`;
    } else if (error.request) {
      // No hubo respuesta del servidor (timeout, CORS, offline, etc.)
      errorMessage =
        "No se pudo conectar con el servidor. Verifica si el backend está corriendo.";
    } else {
      // Error al preparar la petición
      errorMessage = error.message;
    }

    console.error("[ERROR analyzeSample]:", errorMessage, error);
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
