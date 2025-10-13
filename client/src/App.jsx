import { useState } from "react";
import Rutas from "./Routes/Routes";
import { ConfigProvider, theme } from "antd";
function App() {
  const [isDark] = useState(true);
  const { defaultAlgorithm, darkAlgorithm } = theme;

  return (
    <>
      <ConfigProvider
        theme={{
          algorithm: isDark ? darkAlgorithm : defaultAlgorithm,
        }}
      >
        <Rutas />
      </ConfigProvider>
    </>
  );
}

export default App;
