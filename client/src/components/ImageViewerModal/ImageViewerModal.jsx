import React from "react";
import {
  Modal,
  Card,
  Typography,
  Button,
  Tooltip,
  Space,
  Image,
  Divider,
} from "antd";
import {
  CloseOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

const { Title, Paragraph } = Typography;

const EMPTY_DATA = {
  "Measurement ID": "N/A",
  "Upload Date": dayjs().toISOString(),
  predicted_image_top_clean_url: null,
  predicted_image_top_with_text_url: null,
  predicted_image_side_clean_url: null,
  predicted_image_side_with_text_url: null,
  uploaded_image_top_url: null,
  uploaded_image_side_url: null,
};

const ImageViewerModal = ({ isVisible, onClose, data = EMPTY_DATA }) => {
  const measurementId = data["Measurement ID"] || EMPTY_DATA["Measurement ID"];
  const measurementDate = data["Upload Date"] || EMPTY_DATA["Upload Date"];

  // Predicted images (prefer "with text" versions)
  const topWithText = data.predicted_image_top_with_text_url;
  const topClean = data.predicted_image_top_clean_url;
  const sideWithText = data.predicted_image_side_with_text_url;
  const sideClean = data.predicted_image_side_clean_url;

  // Original uploaded images
  const topOriginal = data.uploaded_image_top_url;
  const sideOriginal = data.uploaded_image_side_url;

  const footer = (
    <Button key="close" onClick={onClose} type="primary">
      Close Viewer
    </Button>
  );

  const ImageCard = ({ title, src, alt }) => (
    <div className="relative flex flex-col items-center h-52">
      <Paragraph strong className="mb-2 text-gray-500 dark:text-gray-400">
        {title}
      </Paragraph>
      <Card
        className="w-full h-48 overflow-hidden shadow-md border border-gray-200 dark:border-gray-700 hover:border-primary transition-all flex items-center justify-center"
        bodyStyle={{
          padding: 0,
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        hoverable
      >
        {src ? (
          <Image
            alt={alt}
            src={src}
            className="max-w-full max-h-full object-contain" // ← clave: object-contain + max-w/max-h
            preview={{
              mask: (
                <Space
                  size="middle"
                  className="rounded-full bg-white/30 p-3 text-white backdrop-blur-sm"
                >
                  <Tooltip title="Zoom In">
                    <ZoomInOutlined className="text-2xl" />
                  </Tooltip>
                  <Tooltip title="Fullscreen">
                    <FullscreenOutlined className="text-2xl" />
                  </Tooltip>
                </Space>
              ),
              visible: !!src,
            }}
          />
        ) : (
          <div className="flex items-center justify-center text-gray-400 bg-gray-50 dark:bg-gray-800 w-full h-full">
            Image not available
          </div>
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
      width={1000} // Balanced width for smaller cards
      centered
      // closeIcon={<CloseOutlined />}
      footer={false}
      maskStyle={{
        backgroundColor: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(6px)",
      }}
    >
      <header className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-4 mb-6">
        <div>
          <Title level={4} className="mb-0 text-gray-900 dark:text-white">
            Analysis Images for Cell:{" "}
            <span className="font-bold text-blue-600">{measurementId}</span>
          </Title>
          <Paragraph className="text-sm text-gray-500 dark:text-gray-400 mb-0">
            Measurement Date:{" "}
            {dayjs(measurementDate).format("YYYY-MM-DD HH:mm:ss")}
          </Paragraph>
        </div>
      </header>

      <main>
        <Image.PreviewGroup>
          {/* Predicted Images Section */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-4 lg:grid-cols-4 mb-8">
            <ImageCard
              title="TOP View (With Text)"
              src={topWithText}
              alt={`TOP with text - ${measurementId}`}
              label="With Text"
            />

            <ImageCard
              title="TOP View (Clean)"
              src={topClean}
              alt={`TOP clean - ${measurementId}`}
              label="Clean"
            />

            <ImageCard
              title="SIDE View (With Text)"
              src={sideWithText}
              alt={`SIDE with text - ${measurementId}`}
              label="With Text"
            />

            <ImageCard
              title="SIDE View (Clean)"
              src={sideClean}
              alt={`SIDE clean - ${measurementId}`}
              label="Clean"
            />
          </div>

          {/* Original Uploaded Images (optional section) */}
          {(topOriginal || sideOriginal) && (
            <>
              <Divider orientation="left">Original Uploaded Images</Divider>
              <div className="grid grid-cols-1 w-96 gap-6 sm:grid-cols-2">
                <ImageCard
                  title="TOP Original"
                  src={topOriginal}
                  alt={`Original TOP - ${measurementId}`}
                />

                <ImageCard
                  title="SIDE Original"
                  src={sideOriginal}
                  alt={`Original SIDE - ${measurementId}`}
                />
              </div>
            </>
          )}
        </Image.PreviewGroup>
      </main>
    </Modal>
  );
};

export default ImageViewerModal;
