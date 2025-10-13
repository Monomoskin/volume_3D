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

const MOCK_IMAGE_DATA = {
  measurementId: "20240115-A1-001",
  measurementDate: "2024-01-15",
  topImageSrc:
    "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
  sideImageSrc:
    "data:image/gif;base64,R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
};

const ImageViewerModal = ({ isVisible, onClose, data = MOCK_IMAGE_DATA }) => {
  const [isLoading] = useState(false);

  // Usamos las URLs temporales del último mensaje del usuario para la demostración
  const sideImage =
    "https://lh3.googleusercontent.com/aida-public/AB6AXuCEc4vA2dJoZ9dFgo64tKZteAjCAWTnPzLRT0c5ks7aDInodrRTrB9zGMclskoq71oV4iCpp_4HAGTkhLVvhjh1K-mzSFS7IHL2Y2i_DbDEJf1z4i1tH_jgEKxOdtDj0WkB-X9frKHynZA02Tc2kECNEPLJ6jiUBT4O8nHJHB72LebwodSXeEo7eMmpdfLDZCioNUHMlL2b7h1imRffpTHuIGFERppsVciSUkGK0mcAL5Q0OT-PAdVzqI7ND8zsDe4EuZT_2qh70hZe";
  const topImage =
    "https://lh3.googleusercontent.com/aida-public/AB6AXuDUG6ZFk6gKAMQ9ZgBs6A5JNKxfGLIz0DB3xh4TQ1NkSjYDnpxPSMuQG3qTqUdC9Qd68KQuTqg5uSsipVePI_7x_-vlnSWI2dlaCDmFuU72H-ho-88TBb4DUa-G4JoUjj-sre_0tINTB_8-p1uBdkGnsAJYbu3lzBbXdFYMxrJOfz3A0BOzkIAK0bKpaAdlZSt4zdOIptcUpL7QYGSqW3TASA5nK5qm6AqCAG20VHi5oeydMLAbyn6oSLxv9bc4i9TWKgJ9qPGEtL20";

  // Usamos las URLs temporales si están definidas, sino usamos el mock de Base64
  const finalTopSrc = topImage || data.topImageSrc;
  const finalSideSrc = sideImage || data.sideImageSrc;

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

  // Componente interno ahora usa el componente Image de Ant Design
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
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-4 mb-6 -mt-2">
        <div>
          <Title level={4} className="mb-0 text-gray-900 dark:text-white">
            Images for Cell:{" "}
            <span className="font-bold text-primary">{data.measurementId}</span>
          </Title>
          <Paragraph className="text-sm text-gray-500 dark:text-gray-400 mb-0">
            Measurement Date: {dayjs(data.measurementDate).format("YYYY-MM-DD")}
          </Paragraph>
        </div>
      </header>

      {/* Main Content con Image.PreviewGroup */}
      <main>
        <Image.PreviewGroup>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <ImageCard
              title="TOP VIEW"
              src={finalTopSrc}
              alt={`Top view of measurement ${data.measurementId}`}
            />
            <ImageCard
              title="SIDE VIEW"
              src={finalSideSrc}
              alt={`Side view of measurement ${data.measurementId}`}
            />
          </div>
        </Image.PreviewGroup>
      </main>
    </Modal>
  );
};

export default ImageViewerModal;
