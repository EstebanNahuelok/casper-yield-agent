import { useState } from "react";
import {
    User,
    Camera,
    Wallet,
    Save,
    Shield,
    Activity,
    Copy,
} from "lucide-react";
import { useAgentWallet } from "../context/AgentWalletContext";

export const ProfilePage = () => {
    const [name, setName] = useState("");
    const {address}=useAgentWallet()

    const walletAddress =address


    const copyAddress = async () => {
        await navigator.clipboard.writeText(walletAddress);
    };

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-300">
            <main className="mx-auto max-w-7xl px-6 py-10">
                {/* Header */}

                <div className="mb-10">
                    <div className="text-[10px] font-mono uppercase tracking-widest text-brand mb-2">
                        Account
                    </div>

                    <h1 className="text-4xl font-semibold tracking-tight text-zinc-100">
                        Profile Settings
                    </h1>

                    <p className="mt-3 max-w-2xl text-zinc-500">
                        Manage your wallet information, profile details and
                        account preferences.
                    </p>
                </div>

                {/* Notice */}

                <div className="mb-8 rounded-xl border border-brand/20 bg-brand/5 p-4">
                    <div className="flex items-center gap-3">
                        <Shield className="h-4 w-4 text-brand" />

                        <span className="text-sm text-zinc-300">
                            Wallet successfully connected to Casper Testnet.
                        </span>
                    </div>
                </div>

                {/* Content */}

                <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
                    {/* LEFT */}

                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
                        <div className="flex flex-col items-center">
                            <div className="flex h-36 w-36 items-center justify-center rounded-full border border-zinc-800 bg-zinc-900">
                                <Camera className="h-8 w-8 text-zinc-500" />
                            </div>

                            <button className="mt-4 text-sm text-brand hover:opacity-80">
                                Upload Photo
                            </button>

                            <p className="mt-1 text-xs text-zinc-600">
                                JPG, PNG, GIF · Max 3MB
                            </p>
                        </div>

                        <div className="my-8 border-t border-zinc-800" />

                        <div>
                            <div className="mb-4 flex items-center gap-2">
                                <Wallet className="h-4 w-4 text-brand" />

                                <span className="font-medium text-zinc-100">
                                    Wallet Information
                                </span>
                            </div>

                            <div className="space-y-5">
                                <div>
                                    <div className="mb-1 text-[10px] uppercase tracking-widest text-zinc-500">
                                        Public Key
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-xs text-zinc-300 break-all">
                                            {walletAddress.slice(0, 14)}...
                                            {walletAddress.slice(-14)}
                                        </span>

                                        <button
                                            onClick={copyAddress}
                                            className="text-zinc-500 hover:text-zinc-300"
                                        >
                                            <Copy size={14} />
                                        </button>
                                    </div>
                                </div>

                                <div>
                                    <div className="mb-1 text-[10px] uppercase tracking-widest text-zinc-500">
                                        Wallet
                                    </div>

                                    <div className="font-mono text-sm text-zinc-200">
                                        Casper Wallet
                                    </div>
                                </div>

                                <div>
                                    <div className="mb-1 text-[10px] uppercase tracking-widest text-zinc-500">
                                        Network
                                    </div>

                                    <div className="font-mono text-sm text-zinc-200">
                                        Casper Testnet
                                    </div>
                                </div>

                                <div>
                                    <div className="mb-1 text-[10px] uppercase tracking-widest text-zinc-500">
                                        Status
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <Activity className="h-3 w-3 text-emerald-500" />

                                        <span className="font-mono text-xs uppercase tracking-wider text-emerald-500">
                                            Connected
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* RIGHT */}

                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-8">
                        <div className="mb-8">
                            <h2 className="text-xl font-medium text-zinc-100">
                                Personal Information
                            </h2>

                            <p className="mt-2 text-sm text-zinc-500">
                                Update your profile details.
                            </p>
                        </div>

                        <div className="space-y-6">
                            <div>
                                <label className="mb-2 block text-xs uppercase tracking-widest text-zinc-500">
                                    Full Name
                                </label>

                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />

                                    <input
                                        value={name}
                                        onChange={(e) =>
                                            setName(e.target.value)
                                        }
                                        placeholder="Enter your full name"
                                        className="
                                            w-full
                                            rounded-lg
                                            border
                                            border-zinc-800
                                            bg-zinc-950
                                            py-3
                                            pl-11
                                            pr-4
                                            text-zinc-100
                                            outline-none
                                            transition
                                            focus:border-brand
                                        "
                                    />
                                </div>
                            </div>

                            <div className="pt-4">
                                <button
                                    className="
                                        inline-flex
                                        items-center
                                        gap-2
                                        rounded-lg
                                        bg-[#ff2d2d]
                                        px-5
                                        py-3
                                        text-sm
                                        font-semibold
                                        text-black
                                        transition
                                        hover:opacity-90
                                    "
                                >
                                    <Save size={16} />
                                    Save Changes
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};