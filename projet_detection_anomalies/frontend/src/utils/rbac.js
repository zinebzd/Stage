// Permissions par rôle
export const ROLES = {
  admin: "admin",
  top_management: "top_management",
  user: "user",
};

const PERMISSIONS = {
  admin: [
    "view_dashboard",
    "view_stats",
    "view_history",
    "view_predict",
    "view_batch",
    "view_analyze",
    "view_admin",
    "manage_users",
  ],
  top_management: [
    "view_dashboard",
    "view_stats",
    "view_history",
  ],
  user: [
    "view_predict",
    "view_batch",
    "view_analyze",
    "view_history",
  ],
};

export function can(role, permission) {
  return PERMISSIONS[role]?.includes(permission) ?? false;
}

export function canAny(role, permissions) {
  return permissions.some((p) => can(role, p));
}

// Menu selon le rôle
export function getNavItems(role) {
  const all = [
    { path: "/dashboard",  label: "Dashboard",    icon: "📊", permission: "view_dashboard" },
    { path: "/stats",      label: "Statistiques", icon: "📈", permission: "view_stats"     },
    { path: "/historique", label: "Historique",   icon: "🗄️", permission: "view_history"   },
    { path: "/predict",    label: "Prédiction",   icon: "🔍", permission: "view_predict"   },
    { path: "/batch",      label: "Batch",        icon: "📦", permission: "view_batch"     },
    { path: "/analyze",    label: "Analyser",     icon: "📂", permission: "view_analyze"   },
    { path: "/admin",      label: "Admin",        icon: "⚙️", permission: "view_admin"     },
  ];
  return all.filter((item) => can(role, item.permission));
}

// Page d'accueil selon le rôle
export function getHomePage(role) {
  if (role === ROLES.admin || role === ROLES.top_management) return "/dashboard";
  return "/predict";
}
