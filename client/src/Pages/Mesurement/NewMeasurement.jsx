import React, { useState } from "react";
import {
  Layout,
  Menu,
  Form,
  Select,
  Input,
  DatePicker,
  Upload,
  Button,
  Card,
  Row,
  Col,
  Typography,
  Spin,
  Progress, // Mantener Progress por si se usa más tarde
  message,
} from "antd";
import {
  UploadOutlined,
  CloudUploadOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { analyzeSample } from "../../service/api";

const { Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

// Datos de celulas mock
const MOCK_CELLS = [
  { code: "C-12345", name: "Cell Alpha" },
  { code: "C-67890", name: "Cell Beta" },
];

const NewMeasurement = () => {
  const [form] = Form.useForm();
  const [selectedCell, setSelectedCell] = useState(null);
  const [topFile, setTopFile] = useState([]);
  const [sideFile, setSideFile] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  // Eliminamos el estado 'progress' de la simulación
  const [results, setResults] = useState(null);

  // Determina si el botón de Análisis debe estar activo
  const canAnalyze =
    ((selectedCell && selectedCell !== "new") ||
      (selectedCell === "new" &&
        form.getFieldValue("cellName") &&
        form.getFieldValue("idCode"))) &&
    topFile.length > 0 &&
    sideFile.length > 0;

  const onFinish = async (values) => {
    if (!canAnalyze || isProcessing) return;

    setIsProcessing(true);
    setResults(null);
    message.info("Starting 3D analysis. Waiting for backend response...");

    try {
      // 1. Obtener los archivos de imagen reales (no el array de Antd)
      const actualTopFile = topFile[0].originFileObj || topFile[0];
      const actualSideFile = sideFile[0].originFileObj || sideFile[0];

      // 2. 🔴 Llamada real a la API
      const response = await analyzeSample(
        values,
        actualTopFile,
        actualSideFile
      );

      // 3. Almacenar la respuesta del backend
      setResults({
        sample_key: response.cell_name,
        volume_ml: response.estimated_volume,
        // 🔴 Usamos las URLs proporcionadas por Flask
        top_image_url: response.predicted_image_top_url,
        side_image_url: response.predicted_image_side_url,
      });

      message.success(
        `Analysis completed for ${
          response.cell_name
        }. Volume: ${response.estimated_volume.toFixed(3)} mL`
      );
    } catch (error) {
      const errorMessage = error.message.includes("HTTP")
        ? "Failed to communicate with the Backend. Is the Flask server running on http://localhost:5000?"
        : error.message;

      message.error(`Analysis Failed: ${errorMessage}`);
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Props para el componente Upload (configura el manejo de archivos)
  const fileUploadProps = (fileListState, setFileListState) => ({
    accept: ".jpg,.jpeg,.png",
    onRemove: () => setFileListState([]),
    beforeUpload: (file) => {
      setFileListState([file]); // Solo permite 1 archivo
      return false; // Previene la subida automática de Antd
    },
    fileList: fileListState.map((file) => ({
      ...file,
      uid: file.uid || file.name, // Asegurar uid para Antd
      name: file.name,
      status: "done", // Mostrar como ya cargado localmente
    })),
    maxCount: 1,
  });

  // Maneja el cambio en el selector de Célula
  const handleCellChange = (value) => {
    setSelectedCell(value);
    if (value !== "new") {
      const cell = MOCK_CELLS.find((c) => c.code === value);
      form.setFieldsValue({
        cellName: cell ? cell.name : "",
        idCode: value,
      });
    } else {
      form.setFieldsValue({ cellName: "", idCode: "" });
    }
  };

  return (
    <div className="min-h-screen font-sans">
      <Content
        style={{
          padding: "0 24px",
          minHeight: 280,
          backgroundColor: "var(--background-light)",
        }}
      >
        <div className="p-3">
          <h2 className="text-3xl text-white font-bold text-left">
            New Measurement
          </h2>

          <Row gutter={[32, 32]} className="mt-8">
            <Col xs={24} md={12}>
              <Card title="Sample Data" className="shadow-lg ">
                <Form
                  form={form}
                  layout="vertical"
                  onFinish={onFinish}
                  initialValues={{ photoDate: dayjs() }}
                >
                  {/* Selector de Célula */}
                  <Form.Item
                    label="Select Cell"
                    name="cellSelector"
                    rules={[
                      { required: true, message: "Please select a cell." },
                    ]}
                  >
                    <Select
                      placeholder="Select an existing cell or register a new one"
                      onChange={handleCellChange}
                    >
                      <Option value="new">➕ Register New Cell</Option>
                      {MOCK_CELLS.map((cell) => (
                        <Option key={cell.code} value={cell.code}>
                          {cell.name} ({cell.code})
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  {/* Nombre y Código */}
                  <Form.Item
                    label="Cell Name"
                    name="cellName"
                    rules={[
                      {
                        required: true,
                        message: "The cell name is required.",
                      },
                    ]}
                  >
                    <Input placeholder="e.g., Callus_A_Type_1" />
                  </Form.Item>
                  <Form.Item
                    label="Identification Code"
                    name="idCode"
                    rules={[
                      {
                        required: true,
                        message: "The identification code is required.",
                      },
                    ]}
                  >
                    <Input placeholder="e.g., C-12345" />
                  </Form.Item>

                  {/* Fecha de la Foto */}
                  <Form.Item
                    label="Photo Date"
                    name="photoDate"
                    rules={[
                      { required: true, message: "The date is required." },
                    ]}
                  >
                    <DatePicker
                      className="w-full"
                      format="YYYY-MM-DD"
                      disabledDate={(current) =>
                        current && current > dayjs().endOf("day")
                      }
                    />
                  </Form.Item>

                  {/* Subida de Imágenes */}
                  <Form.Item label="Analysis Images (TOP/SIDE)" required>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Upload.Dragger
                          {...fileUploadProps(topFile, setTopFile)}
                          className="bg-blue-900/50"
                        >
                          <p className="ant-upload-drag-icon">
                            <UploadOutlined />
                          </p>
                          <p className="ant-upload-text">TOP.jpg</p>
                          <p className="ant-upload-hint">
                            Click or drag the top view
                          </p>
                        </Upload.Dragger>
                      </Col>
                      <Col span={12}>
                        <Upload.Dragger
                          {...fileUploadProps(sideFile, setSideFile)}
                          className="bg-blue-900/50"
                        >
                          <p className="ant-upload-drag-icon">
                            <UploadOutlined />
                          </p>
                          <p className="ant-upload-text">SIDE.jpg</p>
                          <p className="ant-upload-hint">
                            Click or drag the side view
                          </p>
                        </Upload.Dragger>
                      </Col>
                    </Row>
                  </Form.Item>

                  {/* Botón de Submit */}
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      size="large"
                      className="w-full"
                      icon={<CloudUploadOutlined />}
                      loading={isProcessing}
                      disabled={!canAnalyze}
                    >
                      {isProcessing
                        ? "Analyzing..."
                        : "Analyze and Save Measurement"}
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            </Col>

            {/* Columna de Resultados */}
            <Col xs={24} md={12}>
              <Card title="Processing Results" className="shadow-lg min-h-full">
                {/* Estado Inicial / Espera */}
                {!isProcessing && !results && (
                  <div className="flex flex-col items-center justify-center p-12 text-center text-gray-500">
                    <CloudUploadOutlined
                      style={{ fontSize: "48px", color: "#1193d4" }}
                    />
                    <Text type="secondary" className="mt-4">
                      Upload your images and click "Analyze" to see the results.
                    </Text>
                  </div>
                )}

                {/* Estado de Procesamiento (Síncrono) */}
                {isProcessing && (
                  <div className="flex flex-col items-center justify-center space-y-4 p-8">
                    <Spin
                      indicator={
                        <LoadingOutlined
                          style={{ fontSize: 48, color: "#1193d4" }}
                          spin
                        />
                      }
                    />
                    <Text strong className="text-lg">
                      Processing images...
                    </Text>
                    <Text type="secondary">
                      Running Detectron2 model on the backend.
                    </Text>
                  </div>
                )}

                {/* Estado de Resultados */}
                {results && (
                  <div className="space-y-6">
                    <Title level={4} style={{ color: "#1193d4" }}>
                      Estimated Volume:{" "}
                      <Text strong className="text-5xl">
                        {results.volume_ml.toFixed(3)} mL
                      </Text>
                    </Title>

                    <Row gutter={[16, 16]}>
                      <Col span={12}>
                        <Card
                          size="small"
                          title="TOP Segmented"
                          bodyStyle={{ padding: 0 }}
                        >
                          {/* 🔴 Usamos la URL devuelta por Flask */}
                          <img
                            alt="Segmented TOP view"
                            src={results.top_image_url}
                            className="w-full h-auto object-cover rounded-b"
                          />
                        </Card>
                      </Col>
                      <Col span={12}>
                        <Card
                          size="small"
                          title="SIDE Segmented"
                          bodyStyle={{ padding: 0 }}
                        >
                          {/* 🔴 Usamos la URL devuelta por Flask */}
                          <img
                            alt="Segmented SIDE view"
                            src={results.side_image_url}
                            className="w-full h-auto object-cover rounded-b"
                          />
                        </Card>
                      </Col>
                    </Row>
                    <Button type="default" block>
                      View Growth History
                    </Button>
                  </div>
                )}
              </Card>
            </Col>
          </Row>
        </div>
      </Content>
    </div>
  );
};

export default NewMeasurement;
