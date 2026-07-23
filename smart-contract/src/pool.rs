use odra::prelude::*;
use odra::casper_types::U512;

use crate::errors::VaultError;

#[odra::event]
pub struct PoolSwap {
    pub cspr_in: U512,
    pub scspr_out: U512,
    pub recipient: Address,
    pub new_cspr_reserve: U512,
    pub new_scspr_reserve: U512,
    pub timestamp: u64,
}

#[odra::event]
pub struct PoolSwapReverse {
    pub scspr_in: U512,
    pub cspr_out: U512,
    pub recipient: Address,
    pub new_cspr_reserve: U512,
    pub new_scspr_reserve: U512,
    pub timestamp: u64,
}

#[odra::event]
pub struct PoolSeeded {
    pub cspr_added: U512,
    pub total_cspr_reserve: U512,
}

/// Minimal x*y=k AMM pool that accepts native CSPR and tracks sCSPR reserves.
///
/// CSPR deposited here is real (moves on-chain). The sCSPR reserve is an internal
/// accounting figure that represents the pool's sCSPR liquidity — seeded by the
/// owner and decremented on each swap. A 0.3% swap fee is applied.
#[odra::module]
pub struct SimplePool {
    owner: Var<Address>,
    cspr_reserve: Var<U512>,
    scspr_reserve: Var<U512>,
}

#[odra::module]
impl SimplePool {
    /// Constructor: caller becomes owner, initial sCSPR reserve is set virtually.
    /// CSPR reserve starts at 0 and grows via seed_cspr().
    pub fn init(&mut self, initial_scspr_reserve: U512) {
        let caller = self.env().caller();
        self.owner.set(caller);
        self.cspr_reserve.set(U512::zero());
        self.scspr_reserve.set(initial_scspr_reserve);
    }

    /// Owner deposits CSPR to seed the pool's CSPR side of the pair.
    #[odra(payable)]
    pub fn seed_cspr(&mut self) {
        self.require_owner();
        let amount = self.env().attached_value();
        if amount.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }
        let new_reserve = self
            .cspr_reserve
            .get_or_default()
            .checked_add(amount)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);
        self.cspr_reserve.set(new_reserve);
        self.env().emit_event(PoolSeeded {
            cspr_added: amount,
            total_cspr_reserve: new_reserve,
        });
    }

    /// Swaps CSPR (attached to the call) for sCSPR using the x*y=k formula with 0.3% fee.
    /// Records the swap and updates reserves. Returns the actual sCSPR amount out.
    ///
    /// `min_amount_out`: minimum sCSPR expected (slippage guard). Pass 0 to disable.
    /// `recipient`: address that conceptually receives the sCSPR (recorded in event).
    #[odra(payable)]
    pub fn swap_cspr_for_scspr(&mut self, min_amount_out: U512, recipient: Address) -> U512 {
        let amount_in = self.env().attached_value();
        if amount_in.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }

        let cspr_reserve = self.cspr_reserve.get_or_default();
        let scspr_reserve = self.scspr_reserve.get_or_default();

        if cspr_reserve.is_zero() || scspr_reserve.is_zero() {
            self.revert(VaultError::InsufficientLiquidity);
        }

        // x*y=k with 0.3% fee on amount_in
        let amount_in_with_fee = amount_in
            .checked_mul(U512::from(997u64))
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow)
            .checked_div(U512::from(1000u64))
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let numerator = scspr_reserve
            .checked_mul(amount_in_with_fee)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let denominator = cspr_reserve
            .checked_add(amount_in_with_fee)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let amount_out = numerator
            .checked_div(denominator)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        if amount_out < min_amount_out {
            self.revert(VaultError::SlippageExceeded);
        }

        if amount_out > scspr_reserve {
            self.revert(VaultError::InsufficientLiquidity);
        }

        let new_cspr_reserve = cspr_reserve
            .checked_add(amount_in)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);
        let new_scspr_reserve = scspr_reserve
            .checked_sub(amount_out)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        self.cspr_reserve.set(new_cspr_reserve);
        self.scspr_reserve.set(new_scspr_reserve);

        self.env().emit_event(PoolSwap {
            cspr_in: amount_in,
            scspr_out: amount_out,
            recipient,
            new_cspr_reserve,
            new_scspr_reserve,
            timestamp: self.env().get_block_time(),
        });

        amount_out
    }

    /// Swaps sCSPR (virtual reserve) for real CSPR using x*y=k formula with 0.3% fee.
    /// Transfers CSPR from the pool purse to `recipient`.
    ///
    /// `amount_in`: sCSPR units to swap in.
    /// `min_amount_out`: minimum CSPR expected (pass 0 to disable slippage guard).
    pub fn swap_scspr_for_cspr(
        &mut self,
        amount_in: U512,
        min_amount_out: U512,
        recipient: Address,
    ) -> U512 {
        if amount_in.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }

        let cspr_reserve = self.cspr_reserve.get_or_default();
        let scspr_reserve = self.scspr_reserve.get_or_default();

        if cspr_reserve.is_zero() || scspr_reserve.is_zero() {
            self.revert(VaultError::InsufficientLiquidity);
        }

        // x*y=k with 0.3% fee applied to the sCSPR input
        let amount_in_with_fee = amount_in
            .checked_mul(U512::from(997u64))
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow)
            .checked_div(U512::from(1000u64))
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let numerator = cspr_reserve
            .checked_mul(amount_in_with_fee)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let denominator = scspr_reserve
            .checked_add(amount_in_with_fee)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let amount_out = numerator
            .checked_div(denominator)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        if amount_out < min_amount_out {
            self.revert(VaultError::SlippageExceeded);
        }

        if amount_out > cspr_reserve {
            self.revert(VaultError::InsufficientLiquidity);
        }

        let new_cspr_reserve = cspr_reserve
            .checked_sub(amount_out)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);
        let new_scspr_reserve = scspr_reserve
            .checked_add(amount_in)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        self.cspr_reserve.set(new_cspr_reserve);
        self.scspr_reserve.set(new_scspr_reserve);

        self.env().transfer_tokens(&recipient, &amount_out);

        self.env().emit_event(PoolSwapReverse {
            scspr_in: amount_in,
            cspr_out: amount_out,
            recipient,
            new_cspr_reserve,
            new_scspr_reserve,
            timestamp: self.env().get_block_time(),
        });

        amount_out
    }

    // ─── Queries ────────────────────────────────────────────────────────────

    pub fn get_cspr_reserve(&self) -> U512 {
        self.cspr_reserve.get_or_default()
    }

    pub fn get_scspr_reserve(&self) -> U512 {
        self.scspr_reserve.get_or_default()
    }

    /// Simulates the amount of sCSPR returned for `amount_in` CSPR (read-only).
    pub fn get_amount_out(&self, amount_in: U512) -> U512 {
        let cspr_reserve = self.cspr_reserve.get_or_default();
        let scspr_reserve = self.scspr_reserve.get_or_default();
        if cspr_reserve.is_zero() || scspr_reserve.is_zero() || amount_in.is_zero() {
            return U512::zero();
        }
        let fee_in = amount_in * U512::from(997u64) / U512::from(1000u64);
        let numerator = scspr_reserve * fee_in;
        let denominator = cspr_reserve + fee_in;
        numerator / denominator
    }

    pub fn get_owner(&self) -> Address {
        self.owner.get_or_revert_with(VaultError::Unauthorized)
    }
}

impl SimplePool {
    fn require_owner(&self) {
        let caller = self.env().caller();
        let owner = self.owner.get_or_revert_with(VaultError::Unauthorized);
        if caller != owner {
            self.revert(VaultError::Unauthorized);
        }
    }
}
