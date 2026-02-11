import React from "react";
import {
  Button,
  Card,
  Row,
  Col,
  Typography,
  Image,
  Table,
  Statistic,
  Divider,
} from "antd";
import { useNavigate } from "react-router-dom";
import { InfoCircleOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;

export default function Results({ results }) {
  const navigate = useNavigate();

  // Safe destructuring with defaults
  const {
    cell_name = "N/A",
    estimated_volume = 0,
    height_mm = null,
    num_cells_detected = 0,
    processed_date = "N/A",
    predicted_image_top_clean_url,
    predicted_image_top_with_text_url,
    predicted_image_side_clean_url,
    predicted_image_side_with_text_url,
    cells_summary = [], // list of detected cells (if multiple)
  } = results || {};

  // Prioritize "with_text" versions (more informative) → fallback to clean
  const topImage =
    predicted_image_top_with_text_url || predicted_image_top_clean_url;
  const sideImage =
    predicted_image_side_with_text_url || predicted_image_side_clean_url;

  // Columns for the per-cell details table (shown if multiple cells exist)
  const cellColumns = [
    { title: "ID", dataIndex: "cell_id", key: "cell_id" },
    { title: "Class", dataIndex: "class", key: "class" },
    {
      title: "Volume (mL)",
      dataIndex: "volume_ml",
      key: "volume_ml",
      render: (v) => (v != null ? v.toFixed(3) : "N/A"),
    },
    { title: "Area (mm²)", dataIndex: "area_mm2", key: "area_mm2" },
    {
      title: "Defects (%)",
      dataIndex: "defective_percent",
      key: "defective_percent",
    },
    {
      title: "Quality (%)",
      dataIndex: "quality_percent",
      key: "quality_percent",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Main summary */}
      <Card
        bordered={false}
        className="bg-gradient-to-r from-blue-50 to-cyan-50"
      >
        <Row gutter={24} align="middle">
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Estimated Volume"
              value={estimated_volume}
              precision={3}
              suffix="mL"
              valueStyle={{ color: "#3f8600", fontSize: "1.2rem" }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Height"
              value={height_mm ?? "N/A"}
              suffix={height_mm ? "mm" : ""}
              valueStyle={{ color: "#1890ff", fontSize: "1.2rem" }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Cells Detected"
              value={num_cells_detected}
              valueStyle={{ color: "#722ed1", fontSize: "1.2rem" }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Statistic
              title="Processed Date"
              value={processed_date}
              valueStyle={{ color: "#faad14", fontSize: ".8rem" }}
            />
          </Col>
        </Row>
      </Card>

      {/* Images */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="TOP View" size="small" extra={<InfoCircleOutlined />}>
            {topImage ? (
              <Image
                alt="Segmented TOP view"
                src={topImage}
                style={{
                  width: "100%",
                  height: "auto",
                  objectFit: "contain",
                  borderRadius: "0 0 8px 8px",
                }}
                preview={{ mask: "View full size" }}
              />
            ) : (
              <div className="text-center py-8 text-gray-400">
                Not available
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="SIDE View" size="small" extra={<InfoCircleOutlined />}>
            {sideImage ? (
              <Image
                alt="Segmented SIDE view"
                src={sideImage}
                style={{
                  width: "100%",
                  height: "auto",
                  objectFit: "contain",
                  borderRadius: "0 0 8px 8px",
                }}
                preview={{ mask: "View full size" }}
              />
            ) : (
              <div className="text-center py-8 text-gray-400">
                Not available
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Per-cell details table (only shown if there are multiple cells or details) */}
      {cells_summary.length > 0 && (
        <>
          <Divider orientation="left">Detected Cells Details</Divider>
          <Table
            columns={cellColumns}
            dataSource={cells_summary}
            rowKey="cell_id"
            pagination={false}
            size="small"
            scroll={{ x: "max-content" }}
          />
        </>
      )}

      {/* View history button */}
      <Button
        type="primary"
        block
        size="large"
        onClick={() =>
          navigate(`/cells/${cell_name}`, {
            state: { fromResults: true },
          })
        }
      >
        View Growth History
      </Button>
    </div>
  );
}
