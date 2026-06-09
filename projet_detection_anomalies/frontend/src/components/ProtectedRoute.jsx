import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { can, getHomePage } from "../utils/rbac";

export default function ProtectedRoute({ permission, children }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (permission && !can(user.role, permission)) {
    return <Navigate to={getHomePage(user.role)} replace />;
  }
  return children;
}
