import React, { useState, useEffect } from "react";
import {
  Table,
  Card,
  Input,
  Typography,
  Button,
  Space,
  Layout,
  Spin,
  Alert,
  Empty,
} from "antd";
import { SearchOutlined, LoadingOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";
import { getEstimationsSummary } from "../../service/api";

const { Title } = Typography;
const { Content } = Layout;

const CellList = () => {
  const [searchText, setSearchText] = useState("");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  const pageSize = 8;

  useEffect(() => {
    const fetchSummaryData = async () => {
      try {
        setLoading(true);
        setError(null);

        const apiData = await getEstimationsSummary();

        const transformedData = apiData.map((item, index) => ({
          key: item["Last Measurement ID"] || index,
          idCode: item["Cell Name"].toUpperCase().replace(/\s/g, "-"),
          name: item["Cell Name"],
          measurements: item["Estimated Count"],
          lastVolume: parseFloat(item["Last Estimated Volume (mL)"]),
          lastDate: item["Last Estimation Date"].split(" ")[0],
        }));

        setData(transformedData);
      } catch (err) {
        console.error("Failed to fetch cell summary data:", err);
        setError(
          "Failed to load cell data. Please check the Flask server status."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchSummaryData();
  }, []); // Se ejecuta solo al montar

  // -------------------------------------------------------------------
  // 2. FILTRACIÓN Y PAGINACIÓN LOCAL (para simular paginación)
  // -------------------------------------------------------------------

  const filteredData = data.filter(
    (cell) =>
      cell.name.toLowerCase().includes(searchText.toLowerCase()) ||
      cell.idCode.toLowerCase().includes(searchText.toLowerCase())
  );

  const paginatedData = filteredData.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const totalCount = filteredData.length; // El conteo total ahora es el de los datos filtrados

  const columns = [
    {
      title: "Identification Code",
      dataIndex: "idCode",
      key: "idCode",
      sorter: (a, b) => a.idCode.localeCompare(b.idCode),
    },
    {
      title: "Cell Name",
      dataIndex: "name",
      key: "name",
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: "Measurements",
      dataIndex: "measurements",
      key: "measurements",
      align: "center",
      sorter: (a, b) => a.measurements - b.measurements,
    },
    {
      title: "Last Volume (mL)",
      dataIndex: "lastVolume",
      key: "lastVolume",
      sorter: (a, b) => a.lastVolume - b.lastVolume,
      render: (volume) => `${volume.toFixed(2)} mL`,
    },
    {
      title: "Last Date",
      dataIndex: "lastDate",
      key: "lastDate",
      sorter: (a, b) =>
        dayjs(a.lastDate).valueOf() - dayjs(b.lastDate).valueOf(),
    },
    {
      title: "Actions",
      key: "actions",
      align: "center",
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => navigate(`/cells/${encodeURIComponent(record.name)}`)}
          className="text-primary hover:text-primary/80"
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <Content
      style={{
        padding: "0 24px",
        minHeight: 280,
        backgroundColor: "var(--background-light)",
      }}
    >
      <div className="max-w-7xl mx-auto py-8">
        <div className="mb-6">
          <Title level={2} className="text-slate-900 dark:text-white">
            Registered Cells
          </Title>
        </div>

        {loading ? (
          <div className="text-center p-10">
            <Spin
              indicator={
                <LoadingOutlined
                  style={{ fontSize: 36, color: "#1890ff" }}
                  spin
                />
              }
              tip="Loading registered cells..."
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
          <Card className="shadow-lg rounded-lg">
            <div className="mb-4">
              <Input
                prefix={<SearchOutlined style={{ color: "rgba(0,0,0,.45)" }} />}
                placeholder="Search by Name or Identification Code"
                size="large"
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value);
                  setCurrentPage(1); // Resetear la página al buscar
                }}
                className="w-full md:w-1/2"
              />
            </div>

            {/* Tabla */}
            <Table
              columns={columns}
              dataSource={paginatedData}
              pagination={false}
              className="w-full"
              rowClassName="hover:bg-background-light/50 dark:hover:bg-slate-800/50"
              bordered={false}
              // Mostrar texto si no hay resultados después de la carga/filtro
              locale={{
                emptyText: (
                  <Empty
                    description={
                      totalCount === 0
                        ? "No registered cells found."
                        : "No results found for your current search."
                    }
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ),
              }}
            />

            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-slate-500 dark:text-slate-400">
                Showing{" "}
                <span className="font-semibold text-slate-900 dark:text-white">
                  {(currentPage - 1) * pageSize + 1}-
                  {Math.min(currentPage * pageSize, totalCount)}
                </span>{" "}
                of{" "}
                <span className="font-semibold text-slate-900 dark:text-white">
                  {totalCount}
                </span>{" "}
                results
              </span>

              <Space>
                <Button
                  onClick={() =>
                    setCurrentPage((prev) => Math.max(prev - 1, 1))
                  }
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setCurrentPage((prev) => prev + 1)}
                  disabled={currentPage * pageSize >= totalCount}
                >
                  Next
                </Button>
              </Space>
            </div>
          </Card>
        )}
      </div>
    </Content>
  );
};

export default CellList;
