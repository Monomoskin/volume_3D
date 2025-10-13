import { Route, Routes } from "react-router-dom";
import Dashboard from "../Pages/Dashboard/Dashboard";
import NewMeasurement from "../Pages/Mesurement/NewMeasurement";
import DahsboardLayout from "../Layouts/DahsboardLayout";
import CellList from "../Pages/CellList/CellList";
import CellDetails from "../Pages/CellDetails/CellDetails";

export default function Rutas() {
  return (
    <Routes>
      <Route path="/" element={<DahsboardLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="/measurements" element={<NewMeasurement />} />
        <Route path="/cells" element={<CellList />} />
        <Route path="/cells/:id" element={<CellDetails />} />
      </Route>
    </Routes>
  );
}
