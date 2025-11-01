import { Button, Card, Row, Col, Typography, Image } from "antd";
import { useNavigate } from "react-router-dom";
const { Title, Text } = Typography;

export default function Results({ results }) {
  const navigate = useNavigate();
  return (
    <div className="space-y-6">
      <Title level={4} style={{ color: "#1193d4" }}>
        Estimated Volume:
        <Text strong className="text-5xl">
          {results.volume_ml.toFixed(3)} mL
        </Text>
      </Title>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card size="small" title="TOP Segmented" bodyStyle={{ padding: 0 }}>
            <Image
              alt="Segmented TOP view"
              src={results.top_image_url}
              style={{
                width: "100%",
                height: "auto",
                objectFit: "cover",
                borderRadius: "0 0 6px 6px",
              }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="SIDE Segmented" bodyStyle={{ padding: 0 }}>
            <Image
              alt="Segmented SIDE view"
              src={results.side_image_url}
              style={{
                width: "100%",
                height: "auto",
                objectFit: "cover",
                borderRadius: "0 0 6px 6px",
              }}
            />
          </Card>
        </Col>
      </Row>
      <Button
        type="default"
        block
        onClick={() =>
          navigate(`/cells/${results.cell_name}`, {
            state: { fromResults: true },
          })
        }
      >
        View Growth History
      </Button>
    </div>
  );
}
