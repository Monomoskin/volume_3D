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
  Progress,
  message,
} from "antd";
import {
  UploadOutlined,
  CloudUploadOutlined,
  TableOutlined,
  DashboardOutlined,
  SettingOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

// Mock cell data (This would come from your Backend API)
const MOCK_CELLS = [
  { code: "C-12345", name: "Cell Alpha" },
  { code: "C-67890", name: "Cell Beta" },
];

const NewMeasurement = () => {
  const [form] = Form.useForm();
  const [selectedCell, setSelectedCell] = useState(null); // 'new' or cell code
  const [topFile, setTopFile] = useState([]);
  const [sideFile, setSideFile] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);

  const canAnalyze =
    ((selectedCell && selectedCell !== "new") ||
      (selectedCell === "new" &&
        form.getFieldValue("cellName") &&
        form.getFieldValue("idCode"))) &&
    topFile.length > 0 &&
    sideFile.length > 0;

  const onFinish = async (values) => {
    if (!canAnalyze) return;

    setIsProcessing(true);
    setResults(null);
    setProgress(0);
    message.info("Starting 3D analysis. This may take a few seconds...");

    try {
      console.log("Form data submitted:", values);

      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            return 100;
          }
          return prev + 10;
        });
      }, 300);

      // Simulating backend processing time (2.5 seconds)
      // Here you would put your actual: await fetch('http://127.0.0.1:8000/analyze-sample/', { method: 'POST', body: formData });
      await new Promise((resolve) => setTimeout(resolve, 2500));
      clearInterval(interval);

      // Mock response from the Backend (JSON with volume and Base64 images)
      const mockResponse = {
        sample_key: values.idCode || selectedCell,
        volume_ml: 12.345 + Math.random() * 2,
        // A very small, valid Base64 placeholder image (1x1 transparent GIF)
        top_image_b64:
          "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
        side_image_b64:
          "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
      };

      setResults(mockResponse);
      message.success(`Analysis completed for ${mockResponse.sample_key}.`);
    } catch (error) {
      message.error(
        "Failed to communicate with the Backend. Check console for details."
      );
      console.error(error);
    } finally {
      setIsProcessing(false);
      setProgress(100);
    }
  };

  // Props for the Ant Design Upload component (prevents auto-upload)
  const fileUploadProps = (fileListState, setFileListState) => ({
    accept: ".jpg,.jpeg,.png",
    onRemove: () => setFileListState([]),
    beforeUpload: (file) => {
      setFileListState([file]); // Only allows 1 file
      return false; // Prevents Antd's automatic upload
    },
    fileList: fileListState,
    maxCount: 1,
  });

  // Handles changing the Cell Select input
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
    <div className="min-h-screen   font-sans">
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

                  <Form.Item label="Analysis Images (TOP/SIDE)" required>
                    <Row gutter={16}>
                      <Col span={12}>
                        <Upload.Dragger
                          {...fileUploadProps(topFile, setTopFile)}
                          className=" bg-blue-900/50"
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
                          className="bg-blue-50 dark:bg-blue-900/50"
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

                  {/* Submit Button */}
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

            {/* Results Column */}
            <Col xs={24} md={12}>
              <Card title="Processing Results" className="shadow-lg min-h-full">
                {/* Initial State / Waiting */}
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

                {/* Processing State */}
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
                    <Progress
                      percent={progress}
                      status={progress === 100 ? "success" : "active"}
                    />
                    <Text type="secondary">
                      Running Detectron2 model on the backend.
                    </Text>
                  </div>
                )}

                {/* Results State */}
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
                          <img
                            alt="Segmented TOP view"
                            src={results.top_image_b64} // Base64 string from backend
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
                          <img
                            alt="Segmented SIDE view"
                            src={results.side_image_b64} // Base64 string from backend
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
