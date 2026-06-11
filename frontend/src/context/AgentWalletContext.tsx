import { createContext, useContext, useEffect, useState, type ReactNode, } from "react";

type WalletState = {
    connected: boolean;
    address: string;
    loading: boolean;
};

type AgentWalletContextType = WalletState & {
    connect: () => Promise<void>;
    disconnect: () => Promise<void>;
};

const AgentWalletContext = createContext<AgentWalletContextType | null>(null);

export const AgentWalletProvider = ({ children }: { children: ReactNode }) => {
    const [connected, setConnected] = useState(false);
    const [address, setAddress] = useState("");
    const [loading, setLoading] = useState(true);

    // Al montar, chequear si ya hay sesión activa
    useEffect(() => {
        const checkConnection = async () => {
            try {
                const providerFactory = (window as any).CasperWalletProvider;
                if (!providerFactory) return;

                const provider =
                    typeof providerFactory === "function"
                        ? providerFactory(window)
                        : providerFactory;

                const isConnected = await provider.isConnected();
                if (isConnected) {
                    const activeKey = await provider.getActivePublicKey();
                    if (activeKey) {
                        setAddress(activeKey);
                        setConnected(true);
                    }
                }
            } catch (err) {
                console.error("Wallet check error:", err);
            } finally {
                setLoading(false);
            }
        };

        checkConnection();

        // Escuchar eventos de la wallet
        const handleConnected = (e: any) => {
            const key = e.detail?.activeKey;
            if (key) {
                setAddress(key);
                setConnected(true);
            }
        };

        const handleDisconnected = () => {
            setAddress("");
            setConnected(false);
        };

        const handleActiveKeyChanged = (e: any) => {
            const key = e.detail?.activeKey;
            if (key) {
                setAddress(key);
            } else {
                setAddress("");
                setConnected(false);
            }
        };

        window.addEventListener("casper-wallet:connected", handleConnected);
        window.addEventListener("casper-wallet:disconnected", handleDisconnected);
        window.addEventListener("casper-wallet:activeKeyChanged", handleActiveKeyChanged);

        return () => {
            window.removeEventListener("casper-wallet:connected", handleConnected);
            window.removeEventListener("casper-wallet:disconnected", handleDisconnected);
            window.removeEventListener("casper-wallet:activeKeyChanged", handleActiveKeyChanged);
        };
    }, []);

    const connect = async () => {
        try {
            const providerFactory = (window as any).CasperWalletProvider;
            if (!providerFactory) {
                window.open("https://www.casperwallet.io/", "_blank");
                return;
            }

            const provider =
                typeof providerFactory === "function"
                    ? providerFactory(window)
                    : providerFactory;

            await provider.requestConnection();
            const activeKey = await provider.getActivePublicKey();
            if (activeKey) {
                setAddress(activeKey);
                setConnected(true);
            }
        } catch (err) {
            console.error("Connect error:", err);
        }
    };

    const disconnect = async () => {
        try {
            const providerFactory = (window as any).CasperWalletProvider;
            if (!providerFactory) return;

            const provider =
                typeof providerFactory === "function"
                    ? providerFactory(window)
                    : providerFactory;

            if (provider.disconnect) await provider.disconnect();
            if (provider.requestDisconnect) await provider.requestDisconnect();
        } catch (err) {
            console.error("Disconnect error:", err);
        } finally {
            setAddress("");
            setConnected(false);
        }
    };

    return (
        <AgentWalletContext.Provider value={{ connected, address, loading, connect, disconnect }}>
            {children}
        </AgentWalletContext.Provider>
    );
};

export const useAgentWallet = () => {
    const ctx = useContext(AgentWalletContext);
    if (!ctx) throw new Error("useAgentWallet must be used inside AgentWalletProvider");
    return ctx;
};