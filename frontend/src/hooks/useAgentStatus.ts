import { useEffect, useState } from "react";
import { getStatusAgentAction } from "../actions/get-status-agent.action";

export function useAgentStatus() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getStatusAgentAction();

        console.log("STATUS", data);

        setStatus(data);
      } catch (err) {
        console.error("AGENT ERROR", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();

    const interval = setInterval(fetchStatus, 30000);

    return () => clearInterval(interval);
  }, []);

  return {
    status,
    loading,
  };
}