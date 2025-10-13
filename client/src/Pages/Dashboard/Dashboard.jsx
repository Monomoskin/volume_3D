import React, { useState, useEffect } from "react";
import { Spin, Alert } from "antd"; // Usamos componentes de Ant Design para el feedback
import { LoadingOutlined } from "@ant-design/icons";
import styles from "./Dashboard.module.less";
import { getLatestEstimations, getEstimationsSummary } from "../../service/api";

const LatestMeasurementsTable = ({ darkMode, data }) => {
  const tableHeadClasses = `${styles.tableHead} ${
    darkMode ? styles.tableHeadDark : "bg-gray-50"
  }`;
  const tableBodyClasses = `${styles.tableBody} ${
    darkMode ? styles.tableBodyDark : "bg-white"
  }`;
  console.log(data);
  return (
    <div className="mt-8 ">
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
        Latest Measurements (Last 10)
      </h3>
      <div className="mt-4 overflow-x-auto">
        <div className="inline-block min-w-full align-middle">
          <div className={styles.tableContainer}>
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
              <thead className={tableHeadClasses}>
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300"
                    scope="col"
                  >
                    Cell
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300"
                    scope="col"
                  >
                    Measurement Date
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300"
                    scope="col"
                  >
                    Estimated Volume (mL)
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-300"
                    scope="col"
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className={tableBodyClasses}>
                {data?.map((row, index) => (
                  <tr key={row["Measurement ID"] || index}>
                    <td
                      className={`${styles.tableCell} font-medium text-gray-900 dark:text-white`}
                    >
                      {row["Cell Name"]}
                    </td>
                    <td
                      className={`${styles.tableCell} text-gray-500 dark:text-gray-400`}
                    >
                      {row["Upload Date"].split(" ")[0]}
                    </td>
                    <td
                      className={`${styles.tableCell} text-gray-500 dark:text-gray-400`}
                    >
                      {parseFloat(row["Estimated Volume (mL)"]).toFixed(3)}
                    </td>
                    <td className={`${styles.tableCell} font-medium`}>
                      <a
                        className={styles.primaryLink}
                        href={`/details/${row["Cell Name"]}`}
                      >
                        View Details
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length === 0 && (
              <p className="p-6 text-center text-gray-500 dark:text-gray-400">
                No recent measurements found. Start a new analysis!
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const darkMode = true; // Mantener la variable de modo oscuro

  // 💡 Estados para datos, carga y error
  const [latestMeasurements, setLatestMeasurements] = useState([]);
  const [estimationData, setEstimationData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // 💡 Metricas estáticas (las mantendremos hasta que se creen APIs para ellas)
  const [lastMeasurementDate, setLastMeasurementDate] = useState("N/A");

  useEffect(() => {
    const fetchEsimatorData = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await getEstimationsSummary();

        setEstimationData(data.length ? data.length : 0);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
        setEstimationData("N/A");
        setError(
          "Failed to load data. Please check if the Flask server is running."
        );
      } finally {
        setLoading(false);
      }
    };
    const fetchLatestData = async () => {
      try {
        setLoading(true);
        setError(null);

        // 🔴 Llama a la API de Flask
        const data = await getLatestEstimations();

        setLatestMeasurements(data);

        // 🔴 Actualiza la métrica de última medición
        if (data.length > 0) {
          // La fecha más reciente es el primer elemento (ya viene ordenado por Flask)
          setLastMeasurementDate(data[0]["Upload Date"].split(" ")[0]);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
        setError(
          "Failed to load data. Please check if the Flask server is running."
        );
      } finally {
        setLoading(false);
      }
    };

    Promise.all([fetchEsimatorData(), fetchLatestData()]);
  }, []);

  const metricCardClasses = `${styles.metricCard} ${
    darkMode ? styles.metricCardDark : "bg-white "
  } shadow border-2 corder-gray-200 dark:border-gray-800 p-6 rounded-lg h-40 text-left`;

  return (
    <div className={styles.mainLayout}>
      <main className={styles.mainContent}>
        <div className={styles.contentWrapper}>
          <h2 className="text-4xl text-left mt-0 p-0 font-bold text-gray-900 dark:text-white">
            Dashboard
          </h2>

          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className={metricCardClasses}>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Total Registered Cells
              </p>
              <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white">
                {estimationData}
              </p>
            </div>
            <div className={metricCardClasses}>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Last Measurement Taken
              </p>
              <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white">
                {lastMeasurementDate}
              </p>
            </div>
          </div>

          <div className="mt-6">
            {loading ? (
              <div className="text-center p-10">
                <Spin
                  indicator={
                    <LoadingOutlined
                      style={{ fontSize: 36, color: "#1890ff" }}
                      spin
                    />
                  }
                  tip="Loading latest measurements..."
                />
              </div>
            ) : error ? (
              <Alert
                message="Error loading data"
                description={error}
                type="error"
                showIcon
              />
            ) : (
              <LatestMeasurementsTable
                darkMode={darkMode}
                data={latestMeasurements}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
