import { Link } from "react-router-dom";
import styles from "./Sidebar.module.less";

const Sidebar = ({ darkMode, activeLink }) => {
  const sidebarClasses = `${styles.sidebar} ${
    darkMode ? styles.sidebarDark : "bg-white"
  }`;
  const headerClasses = `${styles.sidebarHeader} ${
    darkMode ? styles.sidebarHeaderDark : ""
  }`;

  const getLinkClasses = (linkName) => {
    const isActive = activeLink === linkName;
    const baseClass = `${styles.navItem} ${styles.navItemBase} ${
      darkMode ? styles.navItemBaseDark : "text-gray-600"
    } hover:bg-gray-100 dark:hover:bg-gray-800`;
    const activeClass = isActive
      ? `${styles.navItemActive} ${darkMode ? styles.navItemActiveDark : ""} ${
          styles.primaryText
        }`
      : "";
    return `${baseClass} ${activeClass}`;
  };

  const linkBaseClasses = `${styles.navItem} ${styles.navItemBase} ${
    darkMode ? styles.navItemBaseDark : "text-gray-600"
  }`;

  return (
    <aside className={sidebarClasses}>
      <div className={headerClasses}>
        <h1 className="text-md font-bold text-gray-800 dark:text-white">
          CellGrowth Analyzer
        </h1>
      </div>

      <nav className="flex-1 space-y-2 p-4">
        <Link className={getLinkClasses("dashboard")} to={"/"}>
          {/* SVG Icon: Dashboard */}
          <svg
            className="h-5 w-5"
            fill="currentColor"
            height="24"
            viewBox="0 0 24 24"
            width="24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M4 13h6v-2H4v2zm0 4h6v-2H4v2zm0-8h6V7H4v2zm10 2v-2h-2v2h2zm-2-4V7h2v2h-2zm6 4h-2v-2h2v2zm-2-4V7h2v2h-2zm-2 10h6v-2h-6v2zM4 21h6v-2H4v2zm12-8h6v-2h-6v2zm-8-4h6V7h-6v2zM4 5v2h16V5H4z"></path>
          </svg>
          Dashboard
        </Link>
        <Link className={getLinkClasses("measurements")} to="/measurements">
          {/* SVG Icon: Measurements */}
          <svg
            className="h-5 w-5"
            fill="none"
            height="24"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            width="24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
            <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
          </svg>
          Measurements
        </Link>
        <Link className={getLinkClasses("cells")} to={"/cells"}>
          {/* SVG Icon: Cells */}
          <svg
            className="h-5 w-5"
            fill="none"
            height="24"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            width="24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect height="7" width="7" x="3" y="3"></rect>
            <rect height="7" width="7" x="14" y="3"></rect>
            <rect height="7" width="7" x="14" y="14"></rect>
            <rect height="7" width="7" x="3" y="14"></rect>
          </svg>
          Cells
        </Link>
      </nav>
    </aside>
  );
};

const FooterAside = ({ darkMode, activeLink, getLinkClasses }) => {
  const footerClasses = `${styles.sidebarFooter} ${
    darkMode ? styles.sidebarFooterDark : ""
  }`;

  return (
    /* Footer de Navegación (Settings, Help) */
    <div className="mt-auto border-t border-gray-200 dark:border-gray-800 p-4">
      <a className={getLinkClasses("settings")} href="#">
        {/* SVG Icon: Settings */}
        <svg
          className="h-5 w-5"
          fill="none"
          height="24"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          width="24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 0 2l-.15.08a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1 0-2l.15.08a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
        Settings
      </a>
      <a className={getLinkClasses("help")} href="#">
        {/* SVG Icon: Help */}
        <svg
          className="h-5 w-5"
          fill="none"
          height="24"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          width="24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" x2="12.01" y1="17" y2="17"></line>
        </svg>
        Help
      </a>
    </div>
  );
};
export default Sidebar;
