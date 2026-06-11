import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { CasperFarmer } from "./CasperFarmer";
import { AgentWalletProvider } from "./context/AgentWalletContext";

createRoot(document.getElementById("root")!).render(
    <AgentWalletProvider>

        <CasperFarmer />
    </AgentWalletProvider>
);