import styles from "./Dashboard.module.less";

const latestMeasurements = [
  { cell: "Cell A", date: "2024-03-15", volume: "0.85" },
  { cell: "Cell B", date: "2024-03-14", volume: "0.92" },
  { cell: "Cell C", date: "2024-03-13", volume: "0.78" },
  { cell: "Cell D", date: "2024-03-12", volume: "0.88" },
  { cell: "Cell E", date: "2024-03-11", volume: "0.95" },
];

const LatestMeasurementsTable = ({ darkMode, data }) => {
  const tableHeadClasses = `${styles.tableHead} ${
    darkMode ? styles.tableHeadDark : "bg-gray-50"
  }`;
  const tableBodyClasses = `${styles.tableBody} ${
    darkMode ? styles.tableBodyDark : "bg-white"
  }`;

  return (
    <div className="mt-8 ">
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
        Latest Measurements
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
                {data.map((row, index) => (
                  <tr key={index}>
                    <td
                      className={`${styles.tableCell} font-medium text-gray-900 dark:text-white`}
                    >
                      {row.cell}
                    </td>
                    <td
                      className={`${styles.tableCell} text-gray-500 dark:text-gray-400`}
                    >
                      {row.date}
                    </td>
                    <td
                      className={`${styles.tableCell} text-gray-500 dark:text-gray-400`}
                    >
                      {row.volume}
                    </td>
                    <td className={`${styles.tableCell} font-medium`}>
                      <a className={styles.primaryLink} href="#">
                        View Details
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

const Dashboard = () => {
  const darkMode = true;

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
                125
              </p>
            </div>
            <div className={metricCardClasses}>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Last Measurement Taken
              </p>
              <p className="mt-2 text-4xl font-bold text-gray-900 dark:text-white">
                2024-03-15
              </p>
            </div>
          </div>

          <LatestMeasurementsTable
            darkMode={darkMode}
            data={latestMeasurements}
          />
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
