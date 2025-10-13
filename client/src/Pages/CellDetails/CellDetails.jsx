import {
  Layout,
  Card,
  Descriptions,
  Table,
  Typography,
  Button,
  Tag,
} from "antd";
import dayjs from "dayjs";
import VolumeAreaChart from "./Chart";
import { useState } from "react";
import ImageViewerModal from "../../components/ImageViewerModal/ImageViewerModal";

const { Title, Text } = Typography;
const { Content } = Layout;

const MOCK_CELL_DATA = {
  cellName: "Cell A1",
  idCode: "20240722-A1",
  registrationDate: "2024-07-22",
  history: [
    {
      id: "1",
      date: "2024-07-08",
      volume: 0.8,
      height: 2.1,
      area: 1.4,
      precision: "90%",
      key: 1,
    },
    {
      id: "6",
      date: "2024-07-15",
      volume: 1.0,
      height: 2.3,
      area: 1.6,
      precision: "92%",
      key: 2,
    },
    {
      id: "7",
      date: "2024-07-22",
      volume: 1.2,
      height: 2.5,
      area: 1.8,
      precision: "95%",
      key: 3,
    },
    {
      id: "8",
      date: "2024-07-29",
      volume: 1.5,
      height: 2.8,
      area: 2.1,
      precision: "94%",
      key: 4,
    },
    {
      id: "9",
      date: "2024-08-05",
      volume: 1.9,
      height: 3.1,
      area: 2.5,
      precision: "96%",
      key: 5,
    },
    {
      id: "10",
      date: "2024-08-12",
      volume: 2.4,
      height: 3.5,
      area: 3.0,
      precision: "97%",
      key: 6,
    },
  ],
};

const CellDetails = () => {
  const { cellName, idCode, registrationDate, history } = MOCK_CELL_DATA;
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentImageData, setCurrentImageData] = useState(null);
  const openModal = (measurementData) => {
    setCurrentImageData(measurementData);
    setIsModalOpen(true);
  };

  const handleClose = () => {
    setIsModalOpen(false);
    setCurrentImageData(null);
  };
  const historyColumns = [
    {
      title: "Measurement Date",
      dataIndex: "date",
      key: "date",
      // Formatear la fecha para que sea legible
      render: (date) => dayjs(date).format("MMM D, YYYY"),
      sorter: (a, b) => dayjs(a.date).valueOf() - dayjs(b.date).valueOf(),
    },
    {
      title: "Estimated Volume (mL)",
      dataIndex: "volume",
      key: "volume",
      sorter: (a, b) => a.volume - b.volume,
      render: (volume) => <Text strong>{volume.toFixed(2)}</Text>,
    },
    {
      title: "Height (mm)",
      dataIndex: "height",
      key: "height",
    },
    {
      title: "Area (mm²)",
      dataIndex: "area",
      key: "area",
    },
    {
      title: "Precision",
      dataIndex: "precision",
      key: "precision",
      render: (precision) => (
        <Tag color={parseFloat(precision) >= 95 ? "blue" : "orange"}>
          {precision}
        </Tag>
      ),
    },
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
  return (
    <Content style={{ padding: "0 24px", minHeight: "100vh" }}>
      <div className="max-w-7xl mx-auto py-8 space-y-8 flex flex-col gap-3">
        <h1 className="text-gray-800 text-3xl p-2 dark:text-white">
          Cell Details: {idCode}
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
              Growth Chart
            </Title>
          }
          className="shadow-lg border border-primary/20 dark:border-primary/30"
        >
          <div style={{ margin: "50px auto" }}>
            <VolumeAreaChart history={MOCK_CELL_DATA.history} />
          </div>
        </Card>

        {/* Card del Historial de Medidas */}
        <Card
          title={
            <Title level={3} className="mb-0">
              Measurement History
            </Title>
          }
          className="shadow-lg border border-primary/20 dark:border-primary/30"
          bodyStyle={{ padding: 0 }} // Para que la tabla ocupe todo el ancho sin padding extra
        >
          <Table
            columns={historyColumns}
            dataSource={history.slice().reverse()}
            pagination={{ pageSize: 5 }}
            scroll={{ x: "max-content" }}
            rowClassName="bg-background-light dark:bg-background-dark/50 hover:bg-primary/5 dark:hover:bg-primary/10"
          />
        </Card>
      </div>
      <ImageViewerModal
        isVisible={isModalOpen}
        onClose={handleClose}
        // data={currentImageData}
      />
    </Content>
  );
};

export default CellDetails;
