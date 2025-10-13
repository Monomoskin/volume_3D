import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";

/**
 * Componente que muestra el gráfico de volumen de crecimiento celular
 * @param {Array<Object>} history - Array de objetos con las mediciones de historial.
 * @param {string} title - Título del gráfico.
 */
const VolumeAreaChart = ({
  history,
  title = "Volume (mL) vs Measurement Date",
}) => {
  // 1. Preparación de Datos con useMemo
  // Usamos useMemo para asegurar que los datos solo se reprocesen cuando 'history' cambie.
  const { dates, volumes } = useMemo(() => {
    // Mapeamos el array de historial a dos arrays separados para ECharts
    const dates = history.map((item) => item.date);
    const volumes = history.map((item) => item.volume);
    return { dates, volumes };
  }, [history]);

  // 2. Opciones de Configuración de ECharts
  const option = {
    // Título del gráfico
    title: {
      text: title,
      left: "left",
      textStyle: {
        color: "#fff", // Color del texto
        fontWeight: "bold",
        fontSize: 18,
      },
      padding: [10, 0, 0, 0],
    },

    // 3. Tooltip: Activo con el eje como disparador
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      // Formato que muestra la fecha (X) y el volumen (Y)
      formatter: function (params) {
        const data = params[0];
        return `${data.name}<br/>${data.seriesName}: <b>${data.value} mL</b>`;
      },
      backgroundColor: "rgba(50,50,50,0.7)",
      textStyle: {
        color: "#fff",
      },
    },

    // 4. Grid: Ocultamos la cuadrícula
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      containLabel: false,
      show: false,
    },

    // 5. Ejes X e Y: Ocultamos los ejes para el estilo limpio
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dates, // Usamos las fechas del historial
      show: false,
    },
    yAxis: {
      type: "value",
      min: 0,
      show: false,
    },

    // 6. Serie de Datos: Configuración del gráfico de área
    series: [
      {
        name: "Volume (mL)",
        type: "line",
        data: volumes, // Usamos los volúmenes del historial
        smooth: true,

        // Estilo de línea y color
        lineStyle: {
          color: "#1193d4", // Color azul ('primary')
          width: 2,
        },

        // Estilo del área sombreada (gradiente azul)
        areaStyle: {
          opacity: 0.8,
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "#1193d4" },
              { offset: 1, color: "rgba(255, 255, 255, 0)" },
            ],
          },
        },

        // Ocultamos los puntos de datos y configuramos el foco
        showSymbol: false,
        emphasis: {
          focus: "series",
        },
      },
    ],
  };

  // 7. Renderizado
  return (
    <div
      style={{
        padding: "10px",
        borderRadius: "8px",
      }}
    >
      <ReactECharts
        option={option}
        style={{ height: "300px", width: "100%" }}
      />
    </div>
  );
};

export default VolumeAreaChart;

// --- Ejemplo de Uso (En otro componente, como App.js) ---
/* import VolumeAreaChart from './VolumeAreaChart';
import { MOCK_CELL_DATA } from './data'; // Suponiendo que el mock está aquí

const App = () => (
    <div style={{ width: '600px', margin: '50px auto' }}>
        
    </div>
);
*/
