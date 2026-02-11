import React, { useState, useEffect } from "react";
import {
  Layout,
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
  message,
  Alert,
} from "antd";
import {
  UploadOutlined,
  CloudUploadOutlined,
  LoadingOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { analyzeSample, getEstimationsSummary } from "../../service/api";
import Results from "./Results";

const { Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

const NewMeasurement = () => {
  const [form] = Form.useForm();

  // Estados para la carga de células existentes
  const [availableCells, setAvailableCells] = useState([]);
  const [loadingCells, setLoadingCells] = useState(true);
  const [cellsError, setCellsError] = useState(null);

  // Estados del formulario y procesamiento
  const [selectedCell, setSelectedCell] = useState(null);
  const [topFile, setTopFile] = useState([]);
  const [sideFile, setSideFile] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);

  // -------------------------------------------------------------------
  // LÓGICA DE CARGA DE CÉLULAS EXISTENTES
  // -------------------------------------------------------------------
  const fetchAvailableCells = async () => {
    try {
      setLoadingCells(true);
      setCellsError(null);

      const summaryData = await getEstimationsSummary();

      const cellsList = summaryData.map((item) => ({
        code: item["Cell Name"],
        name: item["Cell Name"],
      }));

      setAvailableCells(cellsList);
    } catch (error) {
      console.error("Error fetching available cells:", error);
      setCellsError(
        "Failed to load cell list. Check network or server status.",
      );
    } finally {
      setLoadingCells(false);
    }
  };
  useEffect(() => {
    fetchAvailableCells();
  }, []);

  // -------------------------------------------------------------------
  // MANEJO DE ARCHIVOS Y PROPS DE UPLOAD (con previsualización)
  // -------------------------------------------------------------------

  const fileUploadProps = (fileListState, setFileListState) => ({
    accept: ".jpg,.jpeg,.png",
    onRemove: () => setFileListState([]),
    beforeUpload: (file) => {
      // 1. Crear el FileReader
      const reader = new FileReader();
      reader.onload = (e) => {
        // 2. ¡CRÍTICO! Almacenar el archivo binario original (file) bajo la clave 'originFileObj'
        setFileListState([
          {
            ...file,
            status: "done",
            preview: e.target.result,
            originFileObj: file, // 👈 SOLUCIÓN: Preservar el objeto File nativo aquí
          },
        ]);
      };
      reader.readAsDataURL(file);
      return false; // Previene la subida automática
    },

    // (El resto de la función fileUploadProps permanece igual)
    fileList: fileListState.map((file) => ({
      ...file,
      uid: file.uid || file.name,
      name: file.name,
      status: "done",
    })),
    maxCount: 1,
    showUploadList: false,
  });

  // -------------------------------------------------------------------
  // MANEJO DEL FORMULARIO Y API
  // -------------------------------------------------------------------

  // Determina si el botón de Análisis debe estar activo
  const canAnalyze =
    !loadingCells &&
    ((selectedCell && selectedCell !== "new") ||
      (selectedCell === "new" && form.getFieldValue("cellName"))) &&
    topFile.length > 0 &&
    sideFile.length > 0;

  const onFinish = async (values) => {
    if (!canAnalyze || isProcessing) return;

    setIsProcessing(true);
    setResults(null);
    message.info("Iniciando análisis 3D...");

    try {
      const actualTopFile = topFile[0]?.originFileObj;
      const actualSideFile = sideFile[0]?.originFileObj;

      if (!actualTopFile || !actualSideFile) {
        throw new Error("Archivos de imagen no válidos");
      }

      // Construir payload mínimo y correcto
      const payload = {
        cell_name: values.cellName || values.idCode || selectedCell,
      };

      // Solo agregar test_date si el usuario seleccionó una fecha
      if (values.testDate) {
        payload.test_date = values.testDate.format("YYYY-MM-DD");
        console.log("[DEBUG] Enviando test_date:", payload.test_date);
      }

      // Llamada al servicio (ya adaptado)
      const response = await analyzeSample(
        payload,
        actualTopFile,
        actualSideFile,
      );

      // Guardar toda la respuesta (más rica ahora)
      setResults(response);

      message.success(
        `Análisis completado para ${response.cell_name}. ` +
          `Volumen: ${response.estimated_volume?.toFixed(3) || "N/A"} mL`,
      );
    } catch (error) {
      message.error(
        `Error en el análisis: ${error.message || "Error desconocido"}`,
      );
      console.error("Error API:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Maneja el cambio en el selector de Célula
  const handleCellChange = (value) => {
    setSelectedCell(value);
    if (value !== "new") {
      const cell = availableCells.find((c) => c.code === value);
      form.setFieldsValue({
        cellName: cell ? cell.name : "",
        idCode: value,
      });
    } else {
      form.setFieldsValue({ cellName: "", idCode: "" });
    }
  };

  // -------------------------------------------------------------------
  // RENDERIZADO DEL SELECTOR DE CÉLULAS (maneja carga y error)
  // -------------------------------------------------------------------
  const renderCellSelector = () => {
    if (loadingCells) {
      return (
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />}
          tip="Loading cells..."
        />
      );
    }

    if (cellsError) {
      return (
        <Alert
          message="Error loading cells"
          description={cellsError}
          type="error"
          showIcon
        />
      );
    }

    return (
      <Select
        placeholder="Select an existing cell or register a new one"
        onChange={handleCellChange}
      >
        <Option value="new">➕ Register New Cell</Option>
        {availableCells.map((cell) => (
          <Option key={cell.code} value={cell.code}>
            {cell.name} ({cell.code})
          </Option>
        ))}
        {availableCells.length === 0 && (
          <Option disabled>No existing cells found. Register a new one.</Option>
        )}
      </Select>
    );
  };

  // -------------------------------------------------------------------
  // RENDERIZADO PRINCIPAL
  // -------------------------------------------------------------------
  const refresh = () => {
    form.resetFields();
    setTopFile([]);
    setSideFile([]);
    setResults(null);
    fetchAvailableCells();
    message.info("Form has been reset. You can analyze a new measurement.");
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
            {/* Columna de Formulario */}
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
                    {renderCellSelector()}
                  </Form.Item>

                  {/* Nombre y Código */}
                  <Form.Item
                    label="Cell Name"
                    name="cellName"
                    rules={[
                      { required: true, message: "The cell name is required." },
                    ]}
                  >
                    <Input
                      placeholder="e.g., Callus_A_Type_1"
                      disabled={selectedCell && selectedCell !== "new"}
                    />
                  </Form.Item>

                  {/* Fecha de la Foto */}
                  <Form.Item
                    label="Photo Date"
                    name="testDate"
                    // rules={[
                    //   { required: true, message: "The date is required." },
                    // ]}
                  >
                    <DatePicker
                      className="w-full"
                      format="YYYY-MM-DD"
                      allowClear
                      // disabledDate={(current) =>
                      //   current && current < dayjs().endOf("day")
                      // }
                    />
                  </Form.Item>

                  {/* Subida de Imágenes */}
                  <Form.Item label="Analysis Images (TOP/SIDE)" required>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Upload.Dragger
                          {...fileUploadProps(topFile, setTopFile)}
                          className="bg-blue-900/50"
                          height={200} // Puedes ajustar la altura para que la imagen se vea bien
                        >
                          {/* 💡 LÓGICA DE PREVISUALIZACIÓN PARA TOP FILE */}
                          {topFile.length > 0 && topFile[0].preview ? (
                            <img
                              src={topFile[0].preview}
                              alt="Top View Preview"
                              className="w-full h-40 object-cover rounded"
                            />
                          ) : (
                            <>
                              <p className="ant-upload-drag-icon">
                                <UploadOutlined />
                              </p>
                              <p className="ant-upload-text">TOP.jpg</p>
                              <p className="ant-upload-hint">
                                Click or drag the top view
                              </p>
                            </>
                          )}
                        </Upload.Dragger>
                      </Col>
                      <Col span={12}>
                        <Upload.Dragger
                          {...fileUploadProps(sideFile, setSideFile)}
                          className="bg-blue-900/50"
                          height={200} // Ajusta también la altura del Dragger lateral
                        >
                          {sideFile.length > 0 && sideFile[0].preview ? (
                            <img
                              src={sideFile[0].preview}
                              alt="Side View Preview"
                              className="w-full h-40 object-cover rounded"
                            />
                          ) : (
                            <>
                              <p className="ant-upload-drag-icon">
                                <UploadOutlined />
                              </p>
                              <p className="ant-upload-text">SIDE.jpg</p>
                              <p className="ant-upload-hint">
                                Click or drag the side view
                              </p>
                            </>
                          )}
                        </Upload.Dragger>
                      </Col>
                    </Row>
                  </Form.Item>

                  {/* Botón de Submit */}
                  <Form.Item>
                    {!results && (
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
                    )}
                    {results && (
                      <Button
                        type="primary"
                        onClick={refresh}
                        size="large"
                        className="w-full bg-orange-400"
                        icon={<ReloadOutlined />}
                      >
                        {isProcessing
                          ? "Analyzing..."
                          : "Refresh to Analyze Again"}
                      </Button>
                    )}
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

                {/* Estado de Procesamiento */}
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
                {results && <Results results={results} form={form} />}
              </Card>
            </Col>
          </Row>
        </div>
      </Content>
    </div>
  );
};

export default NewMeasurement;
