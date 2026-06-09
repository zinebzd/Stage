import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import Login      from "./pages/Login";
import Dashboard  from "./pages/Dashboard";
import Stats      from "./pages/Stats";
import Historique from "./pages/Historique";
import Predict    from "./pages/Predict";
import Batch      from "./pages/Batch";
import Analyze    from "./pages/Analyze";
import Admin      from "./pages/Admin";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/dashboard" element={
        <ProtectedRoute permission="view_dashboard">
          <Layout><Dashboard /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/stats" element={
        <ProtectedRoute permission="view_stats">
          <Layout><Stats /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/historique" element={
        <ProtectedRoute permission="view_history">
          <Layout><Historique /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/predict" element={
        <ProtectedRoute permission="view_predict">
          <Layout><Predict /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/batch" element={
        <ProtectedRoute permission="view_batch">
          <Layout><Batch /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/analyze" element={
        <ProtectedRoute permission="view_analyze">
          <Layout><Analyze /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/admin" element={
        <ProtectedRoute permission="view_admin">
          <Layout><Admin /></Layout>
        </ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
