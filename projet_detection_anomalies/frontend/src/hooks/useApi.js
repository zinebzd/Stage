import { useState, useCallback } from "react";
import axios from "axios";

const API = axios.create({ baseURL: "http://localhost:8000" });

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const call = useCallback(async (fn) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fn(API);
      return res.data;
    } catch (e) {
      const msg = e.response?.data?.detail ?? e.message;
      setError(Array.isArray(msg) ? msg.map((m) => m.msg).join(", ") : msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, call };
}
