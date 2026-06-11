import axios from "axios"



export const agenteApi=axios.create({
    baseURL:import.meta.env.VITE_AGENT_API_URL,
     headers: {
        'ngrok-skip-browser-warning': 'true',
    },
})

