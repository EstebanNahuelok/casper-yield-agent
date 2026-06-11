import type { DropdownMenuItem } from '@radix-ui/react-dropdown-menu'
import { LayoutDashboard, Wallet, Vault } from 'lucide-react'

export const DashboardSection = () => {
    return (
        <>

            <DropdownMenuItem className="rounded-lg cursor-pointer">
                <LayoutDashboard className="mr-3 size-4 text-brand" />
                Dashboard
            </DropdownMenuItem>

            <DropdownMenuItem className="rounded-lg cursor-pointer">
                <Wallet className="mr-3 size-4 text-emerald-400" />
                Portfolio
            </DropdownMenuItem>

            <DropdownMenuItem className="rounded-lg cursor-pointer">
                <Vault className="mr-3 size-4 text-zinc-400" />
                Vaults
            </DropdownMenuItem>
        </>
    )
}
