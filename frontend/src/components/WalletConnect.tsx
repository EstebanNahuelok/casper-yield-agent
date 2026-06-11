import { Wallet } from "lucide-react";

interface WalletConnectProps {
  connectWallet: string;
  onConnected: (address: string) => void;
}

export const WalletConnect = ({
  connectWallet: connectLabel,
  onConnected,
}: WalletConnectProps) => {
  const handleConnect = async () => {
    try {
      const providerFactory = (window as any).CasperWalletProvider;

      if (!providerFactory) {
        alert("Casper Wallet no encontrada");
        return;
      }

      const provider =
        typeof providerFactory === "function"
          ? providerFactory(window)
          : providerFactory;

      await provider.requestConnection();

      const publicKey =
        (await provider.getActivePublicKey?.()) ||
        (await provider.requestActivePublicKey?.());

      if (!publicKey) {
        alert("No pude obtener la public key");
        return;
      }

      onConnected(String(publicKey));
    } catch (err) {
      console.error("Wallet error:", err);
    }
  };

  return (
    <button
      onClick={handleConnect}
      className="px-3 py-1.5 rounded-lg text-sm font-medium bg-brand text-red-500 hover:opacity-90 inline-flex items-center gap-2"
    >
      <Wallet className="size-4" />
      {connectLabel}
    </button>
  );
};