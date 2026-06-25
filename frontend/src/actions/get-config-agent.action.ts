import { agenteApi } from "../api/agentApi"

export const getConfigAgentAction = async () => {
    const { data } = await agenteApi.get("/config")
    return data
}
