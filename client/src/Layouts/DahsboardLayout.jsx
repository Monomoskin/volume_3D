import Sidebar from "../components/Sidebar/Sidebar";
import { Outlet } from "react-router-dom";
import styles from "./layout.module.less";

export default function DahsboardLayout() {
  const darkMode = true;

  return (
    <div className={styles.mainLayout}>
      <Sidebar darkMode={darkMode} activeLink="dashboard" />
      <div className={styles.bodyDark}>
        <Outlet />
      </div>
    </div>
  );
}
