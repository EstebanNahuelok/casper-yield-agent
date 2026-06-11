import { useCallback } from "react";
import {
    HttpHandler,
    RpcClient,
    NativeTransferBuilder,
    PublicKey,
} from "casper-js-sdk";

const RPC_URLS = [
    "https://rpc.testnet.casper.network",           // oficial (a veces cae)
    "https://casper-testnet.drpc.org",              // alternativa buena
    "https://testnet.casper-node.tatum.io",         // Tatum
    "https://rpc.testnet.cspr.live",                // otra opción
];

export const useCasperTransaction = () => {
    // Rotación simple de nodos
    const getRpcClient = () => {
        const url = RPC_URLS[Math.floor(Math.random() * RPC_URLS.length)];
        console.log("🔌 Usando RPC:", url);
        return new RpcClient(new HttpHandler(url));
    };

    const sendNativeTransfer = useCallback(async (
        fromPublicKeyHex: string,
        toPublicKeyHex: string,
        amountMotes: string,
        walletProvider: any
    ): Promise<string> => {

        const rpcClient = getRpcClient();

        const deploy = new NativeTransferBuilder()
            .from(PublicKey.fromHex(fromPublicKeyHex))
            .target(PublicKey.fromHex(toPublicKeyHex))
            .amount(amountMotes)
            .id(Date.now())
            .chainName("casper-test")
            .payment(300_000_000)   // aumentamos un poco el gas
            .build();

        const deployJson = JSON.stringify(deploy.toJSON());
        const signed = await walletProvider.sign(deployJson, fromPublicKeyHex);

        if (!signed?.signature) {
            throw new Error("La wallet rechazó la firma");
        }

        const signedDeploy = deploy.setSignature(
            signed.signature,
            PublicKey.fromHex(fromPublicKeyHex)
        );

        const result = await rpcClient.putDeploy(signedDeploy);
        return result.deployHash;
    }, []);

    return { sendNativeTransfer };
};