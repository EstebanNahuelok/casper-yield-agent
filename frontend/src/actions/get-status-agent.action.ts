import { agenteApi } from "../api/agentApi"


//Obtener estado del agente activo|desactivo
export const getStatusAgentAction=async()=>{

    const {data}=await agenteApi.get("/status")
    return data

}