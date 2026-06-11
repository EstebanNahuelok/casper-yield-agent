import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "#components/ui/dropdown-menu";

import {
  User,
  Wallet,
  Settings,
  LogOut,
  ChevronDown,
  Table,
} from "lucide-react";
import { Link } from "react-router-dom";

interface ProfileMenuProps {
  walletAddress: string;
  onDisconnect: () => void;
}

export const ProfileMenu = ({
  walletAddress,
  onDisconnect,
}: ProfileMenuProps) => {
  const shortAddress = `${walletAddress.slice(
    0,
    6
  )}...${walletAddress.slice(-4)}`;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 hover:bg-zinc-800 transition-colors">
          <div className="size-8 rounded-full bg-brand flex items-center justify-center text-zinc-950 font-bold">
            {walletAddress.charAt(0).toUpperCase()}
          </div>

          <div className="hidden md:flex flex-col items-start">
            <span className="text-xs text-zinc-100">
              My Profile
            </span>

            <span className="text-[10px] text-zinc-500 font-mono">
              {shortAddress}
            </span>
          </div>

          <ChevronDown className="size-4 text-zinc-500" />
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        className="w-64 bg-zinc-950 border-zinc-800"
      >
        <div className="p-3">
          <p className="text-sm font-medium text-zinc-100">
            Casper Wallet
          </p>

          <p className="text-xs text-zinc-500 font-mono truncate">
            {walletAddress}
          </p>
        </div>

        <DropdownMenuSeparator />




        <DropdownMenuItem className="text-zinc-200">
          <User className="mr-2 size-5" />
          <Link to="/profile">Profile</Link>
        </DropdownMenuItem>


        <DropdownMenuItem className="text-zinc-200">
          <Table className="mr-2 size-5" />
          <Link to="/dashboard">Dashboard</Link>
        </DropdownMenuItem>

        <DropdownMenuItem className="text-zinc-200">
          <Wallet className="mr-2 size-5" />
          <Link to="/portfolio">Portfolio</Link>
        </DropdownMenuItem>

        <DropdownMenuItem className="text-zinc-200">
          <Settings className="mr-2 size-5" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={onDisconnect}
          className="text-red-400"
        >
          <LogOut className="mr-2 size-4" />
          Disconnect Wallet
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};