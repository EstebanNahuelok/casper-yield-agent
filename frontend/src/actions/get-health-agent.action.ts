import { agenteApi } from "../api/agentApi"



export const asyncgetHealthAgentAction=async ()=>{
    const {data}=await agenteApi.get("/health")
    return {data}
}