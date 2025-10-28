import React, { useMemo } from "react";
import ReactECharts from "echarts-for-react";
import moment from "moment"; // Usaremos moment.js para un manejo fácil de fechas y ordenamiento

/**
 * Componente que renderiza el gráfico de área ondulada para el volumen vs. fecha.
 * Adaptado a los estilos de las imágenes de referencia.
 * @param {Array} data - Los datos de volumen y fecha provenientes del backend.
 * @param {string} cellName - Opcional. Nombre de la célula para el título del gráfico.
 */
const CallusGrowthChart = ({ data }) => {
  const options = useMemo(() => {
    if (!data || data.length === 0) {
      return {};
    }

    // a) Ordenar los datos por fecha de subida para asegurar que la línea sea correcta
    const sortedData = [...data].sort(
      (a, b) =>
        moment(a["Upload Date"]).valueOf() - moment(b["Upload Date"]).valueOf()
    );

    // b) Extraer las fechas (eje X) y los volúmenes (eje Y)
    const dates = sortedData.map((item) =>
      // Formato de fecha simplificado para el eje X, si es necesario, ejemplo: 'MM-DD HH:mm'
      // O 'YYYY-MM-DD' si solo quieres la fecha
      moment(item["Upload Date"]).format("MM-DD HH:mm")
    );
    const volumes = sortedData.map((item) => item["Estimated Volume (mL)"]);

    // c) Opciones de ECharts adaptadas a los estilos de la imagen
    return {
      tooltip: {
        trigger: "axis",
        formatter: function (params) {
          const dataPoint = params[0];
          return `
                        **Date:** ${moment(
                          dataPoint.name,
                          "MM-DD HH:mm"
                        ).format("YYYY-MM-DD HH:mm")}<br/>
                        **Volume:** ${dataPoint.value.toFixed(4)} mL
                    `;
        },
        axisPointer: {
          type: "shadow",
        },
        // Estilos del tooltip para que coincidan con la estética del cuadro
        backgroundColor: "rgba(0, 0, 1, 1)",
        borderColor: "#ccc",
        borderWidth: 1,
        textStyle: {
          color: "#fff",
        },
        extraCssText: "box-shadow: 0 0 8px rgba(0, 0, 0, 0.2);",
      },
      grid: {
        left: "8%", // Espacio izquierdo para el label del eje Y
        right: "4%", // Espacio derecho para la gráfica
        bottom: "8%", // Más espacio en la parte inferior para las fechas no rotadas
        top: "20%", // Más espacio en la parte superior para el título
        containLabel: true, // Asegura que las etiquetas estén dentro del grid
      },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: dates,
        axisLabel: {
          interval: "auto", // Deja que ECharts decida el intervalo automáticamente
          rotate: 0, // Sin rotación
          showMaxLabel: true, // Asegura que la última etiqueta se muestre si hay espacio
          showMinLabel: true, // Asegura que la primera etiqueta se muestre si hay espacio
          color: "#666", // Color de las etiquetas del eje X
          fontSize: 11,
        },
        axisTick: {
          show: false, // Ocultar los pequeños "ticks" si el estilo lo requiere
        },
        axisLine: {
          show: false, // Ocultar la línea del eje X si el estilo lo requiere
        },
        splitLine: {
          show: false, // Ocultar las líneas de división verticales
        },
      },
      yAxis: {
        type: "value",
        name: "Volumen (mL)",
        nameLocation: "middle", // Centra el nombre del eje Y
        nameGap: 40, // Espacio entre el nombre del eje y las etiquetas
        axisLabel: {
          color: "#666", // Color de las etiquetas del eje Y
          fontSize: 11,
        },
        axisLine: {
          show: false, // Ocultar la línea del eje Y
        },
        axisTick: {
          show: false, // Ocultar los ticks del eje Y
        },
        splitLine: {
          lineStyle: {
            color: ["gray"], // Color de las líneas de división horizontales
            type: "dotted",
          },
        },
      },
      series: [
        {
          name: "Volumen",
          type: "line",
          data: volumes,
          smooth: true,
          showSymbol: false,
          lineStyle: {
            color: "#6699EE", // Un azul más claro para que coincida con la imagen
            width: 2,
          },
          areaStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                {
                  offset: 0,
                  color: "rgba(102, 153, 238, 0.7)", // Azul claro más tenue
                },
                {
                  offset: 1,
                  color: "rgba(102, 153, 238, 0)", // Transparente
                },
              ],
              global: false,
            },
          },
          itemStyle: {
            // Solo para los puntos, aunque showSymbol: false los oculta
            color: "#6699EE",
          },
        },
      ],
    };
  }, [data]);

  return (
    <div
      style={{
        width: "100%",
        height: "400px",
        // Elimina el padding y shadow si el contenedor padre ya los tiene o quieres que ECharts ocupe todo
        // backgroundColor: '#fff',
        // borderRadius: '8px',
        // boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}
    >
      <ReactECharts
        option={options}
        style={{ height: "100%", width: "100%" }} // Asegura que ocupe todo el espacio disponible
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};

export default CallusGrowthChart;
