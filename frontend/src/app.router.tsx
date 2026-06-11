


import { createBrowserRouter } from "react-router-dom"
import { Dashboard } from "./pages/Dashboard"
import { LandingPage } from "./pages/LandingPage"
import { AuditPage } from "./pages/AuditLogs"
import { StrategyPage } from "./pages/Agent"
import { ProfilePage } from "./pages/ProfilePage"
import { PortfolioPage } from "./pages/PortfolioPage"

export const appRouter = createBrowserRouter([

    //RUTAS PUBLICAS
    {
        path: "/dashboard",
        element: <Dashboard />

    },
    {
        path: "/",
        element: <LandingPage />
    },
    {
        path: "/agent",
        element: <StrategyPage />
    },
        {
        path: "/audit",
        element: <AuditPage />
    },
    {
        path:"/profile",
        element:<ProfilePage/>
    },
        {
        path:"/portfolio",
        element:<PortfolioPage/>
    }
]

)
