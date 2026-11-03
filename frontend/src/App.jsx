import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Blacklist from "./pages/Blacklist";
import Dashboard from "./pages/Dashboard";
import Docs from "./pages/Docs";
import Login from "./pages/Login";
import Software from "./pages/Software";
import Users from "./pages/Users";

function FullScreenLoader() {
  return (
    <div className="boot-screen">
      <div className="boot-mark">USB Qalqon</div>
      <div className="spinner" />
      <p>Yuklanmoqda...</p>
    </div>
  );
}

function Protected() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullScreenLoader />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Layout />;
}

function LoginRoute() {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <Login />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginRoute />} />
      <Route element={<Protected />}>
        <Route index element={<Dashboard />} />
        <Route path="/blacklist" element={<Blacklist />} />
        <Route path="/users" element={<Users />} />
        <Route path="/software" element={<Software />} />
        <Route path="/docs" element={<Docs />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
