import React, { useState, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";
import {
  Layout,
  Card,
  Descriptions,
  Table,
  Typography,
  Button,
  Tag,
  Spin,
  Alert,
} from "antd";
import dayjs from "dayjs";
import VolumeAreaChart from "./Chart";
import ImageViewerModal from "../../components/ImageViewerModal/ImageViewerModal";
import { getCellHistory } from "../../service/api";

const { Title, Text } = Typography;
const { Content } = Layout;

const CellDetails = () => {
  const { id } = useParams();
  const cellName = id; // Asumimos que el parámetro de la URL es el nombre de la célula
  const [cellData, setCellData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentImageData, setCurrentImageData] = useState(null);

  useEffect(() => {
    const loadHistory = async () => {
      if (!cellName) return;

      setLoading(true);
      setError(null);

      try {
        const historyData = await getCellHistory(cellName);

        if (historyData && historyData.length > 0) {
          const firstRecord = historyData[0];

          setCellData({
            cellName: cellName,
            idCode: cellName,
            registrationDate: firstRecord["Upload Date"].split(" ")[0],
            history: historyData,
          });
        } else {
          setError(`No se encontraron datos para: ${cellName}.`);
          setCellData(null);
        }
      } catch (err) {
        console.log(err);
        setError("Error al cargar los detalles de la célula.");
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [cellName]);

  const openModal = (record) => {
    setCurrentImageData(record);
    setIsModalOpen(true);
  };

  const handleClose = () => {
    setIsModalOpen(false);
    setCurrentImageData(null);
  };

  const historyColumns = [
    {
      title: "Measurement Date",
      dataIndex: "Upload Date",
      key: "date",
      render: (date) => dayjs(date).format("MMM D, YYYY HH:mm"),
      sorter: (a, b) =>
        dayjs(a["Upload Date"]).valueOf() - dayjs(b["Upload Date"]).valueOf(),
    },
    {
      title: "Estimated Volume (mL)",
      dataIndex: "Estimated Volume (mL)",
      key: "volume",
      sorter: (a, b) => a["Estimated Volume (mL)"] - b["Estimated Volume (mL)"],
      render: (volume) => <Text strong>{parseFloat(volume).toFixed(3)}</Text>,
    },
    {
      title: "Measurement ID",
      dataIndex: "Measurement ID",
      key: "id",
    },
    // NOTA: 'Precision', 'Height', y 'Area' no vienen del backend actual.
    // Si los necesitas, deben añadirse al log.csv en Flask.
    {
      title: "Actions",
      key: "actions",
      align: "center",
      render: (_, record) => (
        <Button
          type="link"
          onClick={() => openModal(record)}
          className="text-primary hover:text-primary/80"
        >
          View Photos
        </Button>
      ),
    },
  ];

  const sortedHistory = useMemo(() => {
    if (!cellData) return [];
    // Ordenar por fecha de subida (más reciente primero)
    return cellData.history
      .slice()
      .sort(
        (a, b) =>
          dayjs(b["Upload Date"]).valueOf() - dayjs(a["Upload Date"]).valueOf()
      );
  }, [cellData]);

  // --- Renderizado de Carga y Error ---
  if (loading) {
    return (
      <Content
        style={{
          padding: "0 24px",
          minHeight: "100vh",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Spin size="large" tip="Loading Cell Data..." />
      </Content>
    );
  }

  if (error) {
    return (
      <Content style={{ padding: "0 24px", minHeight: "100vh" }}>
        <Alert
          message="Data Error"
          description={error}
          type="error"
          showIcon
          style={{ marginTop: 50 }}
        />
      </Content>
    );
  }

  if (!cellData || sortedHistory.length === 0) {
    return (
      <Content style={{ padding: "0 24px", minHeight: "100vh" }}>
        <Alert
          message="No Data"
          description={`No hay mediciones registradas para la célula ${cellName}.`}
          type="info"
          showIcon
          style={{ marginTop: 50 }}
        />
      </Content>
    );
  }

  const { idCode, registrationDate } = cellData;
  const historyForChart = cellData.history;

  // --- Renderizado Principal ---
  return (
    <Content style={{ padding: "0 24px", minHeight: "100vh" }}>
      <div className="max-w-7xl mx-auto py-8 space-y-8 flex flex-col gap-3">
        <h1 className="text-gray-800 text-3xl p-2 dark:text-white">
          Cell Details: {cellName} ({idCode})
        </h1>

        <Card
          title={
            <Title level={3} className="mb-0">
              Basic Information
            </Title>
          }
          className="shadow-lg border border-primary/20 dark:border-primary/30"
        >
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }} bordered>
            <Descriptions.Item label="Cell Name">
              <Text strong>{cellName}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Identification Code">
              <Text strong>{idCode}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Registration Date">
              <Text strong>
                {dayjs(registrationDate).format("MMMM D, YYYY")}
              </Text>
            </Descriptions.Item>
          </Descriptions>
        </Card>

        <Card
          title={
            <Title level={3} className="mb-0">
              Growth Chart (Volume vs. Time)
            </Title>
          }
          className="shadow-lg border border-primary/20 dark:border-primary/30"
        >
          <div style={{ margin: "50px auto" }}>
            <VolumeAreaChart history={historyForChart} />
          </div>
        </Card>

        <Card
          title={
            <Title level={3} className="mb-0">
              Measurement History
            </Title>
          }
          className="shadow-lg border border-primary/20 dark:border-primary/30"
          bodyStyle={{ padding: 0 }}
        >
          <Table
            columns={historyColumns}
            dataSource={sortedHistory}
            pagination={{ pageSize: 5 }}
            scroll={{ x: "max-content" }}
            rowKey="Measurement ID"
            rowClassName="bg-background-light dark:bg-background-dark/50 hover:bg-primary/5 dark:hover:bg-primary/10"
          />
        </Card>
      </div>

      {currentImageData && (
        <ImageViewerModal
          isVisible={isModalOpen}
          onClose={handleClose}
          data={currentImageData}
        />
      )}
    </Content>
  );
};

export default CellDetails;
