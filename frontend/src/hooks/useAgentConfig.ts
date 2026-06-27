import { useEffect, useState } from "react";
import { getConfigAgentAction } from "../actions/get-config-agent.action";

export interface AgentConfig {
    check_interval_seconds: number;
    min_apy_delta: number;
    max_slippage_pct: number;
    min_balance_cspr: number;
    swarm_vote_threshold: number;
    casper_network: string;
    vault_public_key: string;
}

const DEFAULT_CONFIG: AgentConfig = {
    check_interval_seconds: 300,
    min_apy_delta: 2.0,
    max_slippage_pct: 1.5,
    min_balance_cspr: 100.0,
    swarm_vote_threshold: 2,
    casper_network: "testnet",
    vault_public_key: "",
};

export function useAgentConfig(): AgentConfig {
    const [config, setConfig] = useState<AgentConfig>(DEFAULT_CONFIG);

    useEffect(() => {
        getConfigAgentAction()
            .then(setConfig)
            .catch(() => {});
    }, []);

    return config;
}
