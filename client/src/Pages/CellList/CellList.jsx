import React, { useState } from "react";
import { Table, Card, Input, Typography, Button, Space, Layout } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";

const { Title } = Typography;
const { Content } = Layout;

// -------------------------------------------------------------------
// MOCK DATA (Simula datos que vendrían de la API de FastAPI)
// -------------------------------------------------------------------

const MOCK_CELLS_DATA = [
  {
    key: "1",
    idCode: "ID-12345",
    name: "Cell Alpha",
    measurements: 5,
    lastVolume: 2.5,
    lastDate: "2024-01-15",
  },
  {
    key: "2",
    idCode: "ID-67890",
    name: "Cell Beta",
    measurements: 3,
    lastVolume: 1.8,
    lastDate: "2024-02-20",
  },
  {
    key: "3",
    idCode: "ID-11223",
    name: "Cell C-Delta",
    measurements: 7,
    lastVolume: 3.2,
    lastDate: "2024-03-10",
  },
  {
    key: "4",
    idCode: "ID-44556",
    name: "Cell D-Gamma",
    measurements: 2,
    lastVolume: 1.5,
    lastDate: "2024-04-05",
  },
  {
    key: "5",
    idCode: "ID-77889",
    name: "Cell Epsilon",
    measurements: 4,
    lastVolume: 2.0,
    lastDate: "2024-05-12",
  },
  {
    key: "6",
    idCode: "ID-99001",
    name: "Cell F-Zeta",
    measurements: 6,
    lastVolume: 2.8,
    lastDate: "2024-06-18",
  },
  {
    key: "7",
    idCode: "ID-22334",
    name: "Cell G-Eta",
    measurements: 1,
    lastVolume: 1.2,
    lastDate: "2024-07-22",
  },
  {
    key: "8",
    idCode: "ID-55667",
    name: "Cell H-Theta",
    measurements: 8,
    lastVolume: 3.5,
    lastDate: "2024-08-30",
  },
  {
    key: "9",
    idCode: "ID-88990",
    name: "Cell I-Iota",
    measurements: 3,
    lastVolume: 1.9,
    lastDate: "2024-09-15",
  },
  {
    key: "10",
    idCode: "ID-33445",
    name: "Cell J-Kappa",
    measurements: 5,
    lastVolume: 2.3,
    lastDate: "2024-10-20",
  },
  // Añadir más datos mock para la paginación simulada
  {
    key: "11",
    idCode: "ID-90123",
    name: "Cell K-Lambda",
    measurements: 10,
    lastVolume: 4.0,
    lastDate: "2024-11-01",
  },
  {
    key: "12",
    idCode: "ID-34567",
    name: "Cell L-Mu",
    measurements: 1,
    lastVolume: 0.9,
    lastDate: "2024-11-15",
  },
];

const totalRecords = 1000; // Simular el total de registros en el sistema

// -------------------------------------------------------------------
// 2. Definición de Columnas de la Tabla
// -------------------------------------------------------------------

const CellList = () => {
  const [searchText, setSearchText] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  const pageSize = 8;

  // Simular la filtración de datos localmente (en un entorno real, la API haría esto)
  const filteredData = MOCK_CELLS_DATA.filter(
    (cell) =>
      cell.name.toLowerCase().includes(searchText.toLowerCase()) ||
      cell.idCode.toLowerCase().includes(searchText.toLowerCase())
  );

  // Simular la paginación (en un entorno real, la API devolvería solo la página actual)
  const paginatedData = filteredData.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const totalCount =
    filteredData.length > 0 ? filteredData.length : totalRecords;
  const columns = [
    {
      title: "Identification Code",
      dataIndex: "idCode",
      key: "idCode",
      // Esto permite ordenar la columna alfabéticamente
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
          onClick={() => navigate(`/cells/${record.idCode}`)}
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
        {/* Título */}
        <div className="mb-6">
          <Title level={2} className="text-slate-900 dark:text-white">
            Registered Cells 🧬
          </Title>
        </div>

        {/* Contenedor de la Tabla */}
        <Card className="shadow-lg rounded-lg">
          {/* Barra de Búsqueda */}
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

          <Table
            columns={columns}
            dataSource={paginatedData}
            pagination={false}
            className="w-full"
            rowClassName="hover:bg-background-light/50 dark:hover:bg-slate-800/50"
            bordered={false}
          />

          {/* Paginación Manual */}
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
              {/* Botones de paginación simple (emulando el mockup) */}
              <Button
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
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
      </div>
    </Content>
  );
};

export default CellList;
