import React, { useState } from "react";
import {
  Modal,
  Card,
  Typography,
  Button,
  Spin,
  Tooltip,
  Space,
  Image,
} from "antd";
import {
  CloseOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

const { Title, Paragraph } = Typography;

const EMPTY_DATA = {
  "Measurement ID": "N/A",
  "Upload Date": dayjs().toISOString(),
  predicted_image_top_url:
    "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
  predicted_image_side_url:
    "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
};

const ImageViewerModal = ({ isVisible, onClose, data = EMPTY_DATA }) => {
  const [isLoading] = useState(false);
  console.log(data);
  const measurementId = data["Measurement ID"] || EMPTY_DATA["Measurement ID"];
  const measurementDate = data["Upload Date"] || EMPTY_DATA["Upload Date"];

  const finalTopSrc =
    data["predicted_image_top_url"] || EMPTY_DATA["predicted_image_top_url"];
  const finalSideSrc =
    data["predicted_image_side_url"] || EMPTY_DATA["predicted_image_side_url"];
  const initTopSrc =
    data["uploaded_image_top_url"] || EMPTY_DATA["uploaded_image_top_url"];
  const initSideSrc =
    data["uploaded_image_side_url"] || EMPTY_DATA["uploaded_image_side_url"];

  const footer = (
    <Button
      key="close"
      onClick={onClose}
      type="primary"
      style={{ backgroundColor: "#1193d4" }}
    >
      Close Viewer
    </Button>
  );

  const ImageCard = ({ title, src, alt }) => (
    <div className="relative flex flex-col items-center">
      <Paragraph
        strong
        className="mb-2 text-base text-gray-700 dark:text-gray-300"
      >
        {title}
      </Paragraph>
      <Card
        className="w-full aspect-square overflow-hidden shadow-lg border-2 border-primary/20 transition-all hover:border-primary"
        bodyStyle={{ padding: 0 }}
        hoverable
      >
        {isLoading ? (
          <div className="flex h-full items-center justify-center p-8">
            <Spin
              indicator={
                <LoadingOutlined
                  style={{ fontSize: 36, color: "#1193d4" }}
                  spin
                />
              }
            />
          </div>
        ) : (
          <Image
            alt={alt}
            src={src}
            className="h-full w-full object-cover transition-transform duration-300 transform"
            preview={{
              mask: (
                <Space
                  size="large"
                  className="rounded-full bg-white/20 p-3 text-white backdrop-blur-sm"
                >
                  <Tooltip title="Zoom In">
                    <ZoomInOutlined className="text-3xl" />
                  </Tooltip>
                  <Tooltip title="Fullscreen">
                    <FullscreenOutlined className="text-3xl" />
                  </Tooltip>
                </Space>
              ),
              visible: !!src,
            }}
          />
        )}
      </Card>
    </div>
  );

  return (
    <Modal
      open={isVisible}
      onCancel={onClose}
      title={null}
      footer={footer}
      width={850}
      centered
      closeIcon={<CloseOutlined />}
      maskStyle={{
        backgroundColor: "rgba(0, 0, 0, 0.3)",
        backdropFilter: "blur(3px)",
      }}
    >
      <header className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-4 mb-6 -mt-2">
        <div>
          <Title level={4} className="mb-0 text-gray-900 dark:text-white">
            Images for Cell:{" "}
            <span className="font-bold text-primary">{measurementId}</span>
          </Title>
          <Paragraph className="text-sm text-gray-500 dark:text-gray-400 mb-0">
            Measurement Date: {dayjs(measurementDate).format("YYYY-MM-DD")}
          </Paragraph>
        </div>
      </header>

      <main>
        <Image.PreviewGroup>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ImageCard
              title="TOP VIEW"
              src={finalTopSrc}
              alt={`Top view of measurement ${measurementId}`}
            />
            <ImageCard
              title="INITIAL TOP VIEW"
              src={initTopSrc}
              alt={`Side view of measurement ${measurementId}`}
            />
            <ImageCard
              title="SIDE VIEW"
              src={finalSideSrc}
              alt={`Side view of measurement ${measurementId}`}
            />
            <ImageCard
              title="INITIAL SIDE VIEW"
              src={initSideSrc}
              alt={`Side view of measurement ${measurementId}`}
            />
          </div>
        </Image.PreviewGroup>
      </main>
    </Modal>
  );
};

export default ImageViewerModal;
