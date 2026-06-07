use odra::prelude::*;
use odra::casper_types::U512;

use crate::errors::VaultError;
use crate::events::{
    ActionLogged, AgentUpdated, Deposit, OwnershipTransferred, SwapExecuted, VaultPaused,
    VaultUnpaused, Withdrawal,
};
use crate::types::{ActionEntry, SwapRecord};

pub const MAX_ACTIONS: u64 = 10_000;
pub const MAX_SWAPS: u64 = 10_000;
pub const MAX_TYPE_LEN: usize = 64;
pub const MAX_PARAMS_LEN: usize = 512;
pub const MAX_TOKEN_LEN: usize = 16;

#[odra::module]
pub struct YieldVault {
    owner: Var<Address>,
    agent: Var<Address>,
    paused: Var<bool>,
    balances: Mapping<Address, U512>,
    total_locked: Var<U512>,
    action_count: Var<u64>,
    actions: Mapping<u64, ActionEntry>,
    swap_count: Var<u64>,
    swaps: Mapping<u64, SwapRecord>,
}

#[odra::module]
impl YieldVault {
    /// Constructor. Establece owner = caller, agent = parámetro.
    pub fn init(&mut self, agent: Address) {
        let caller = self.env().caller();
        self.owner.set(caller);
        self.agent.set(agent);
        self.paused.set(false);
        self.total_locked.set(U512::zero());
        self.action_count.set(0u64);
        self.swap_count.set(0u64);
    }

    /// Acepta depósitos CSPR del caller.
    /// Actualiza balance del usuario y total_locked.
    #[odra(payable)]
    pub fn deposit(&mut self) {
        self.require_not_paused();

        let caller = self.env().caller();
        let amount = self.env().attached_value();

        if amount.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }

        let old_balance = self.balances.get_or_default(&caller);
        let new_balance = old_balance
            .checked_add(amount)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let new_total = self
            .total_locked
            .get_or_default()
            .checked_add(amount)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        self.balances.set(&caller, new_balance);
        self.total_locked.set(new_total);

        self.env().emit_event(Deposit {
            user: caller,
            amount,
            new_balance,
            timestamp: self.env().get_block_time(),
        });
    }

    /// Retira `amount` CSPR al caller.
    /// Solo puede retirar el depositante. Aplica checks-effects-interactions.
    pub fn withdraw(&mut self, amount: U512) {
        self.require_not_paused();

        if amount.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }

        let caller = self.env().caller();
        let balance = self.balances.get_or_default(&caller);

        if balance < amount {
            self.revert(VaultError::InsufficientBalance);
        }

        let new_balance = balance
            .checked_sub(amount)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        let new_total = self
            .total_locked
            .get_or_default()
            .checked_sub(amount)
            .unwrap_or_revert_with(self, VaultError::ArithmeticOverflow);

        // checks-effects-interactions: estado antes de la transferencia
        self.balances.set(&caller, new_balance);
        self.total_locked.set(new_total);

        self.env().transfer_tokens(&caller, &amount);

        self.env().emit_event(Withdrawal {
            user: caller,
            amount,
            remaining_balance: new_balance,
            timestamp: self.env().get_block_time(),
        });
    }

    /// Registra una acción ejecutada por el agente IA.
    /// Solo el agente autorizado puede llamar esta función.
    pub fn log_action(&mut self, action_type: String, params: String) {
        self.require_not_paused();
        self.require_agent();

        if action_type.is_empty() || action_type.len() > MAX_TYPE_LEN || params.len() > MAX_PARAMS_LEN {
            self.revert(VaultError::InvalidInputLength);
        }

        let count = self.action_count.get_or_default();
        if count >= MAX_ACTIONS {
            self.revert(VaultError::ActionLimitReached);
        }

        let caller = self.env().caller();
        let timestamp = self.env().get_block_time();

        let entry = ActionEntry {
            id: count,
            action_type: action_type.clone(),
            agent: caller,
            params,
            timestamp,
        };

        self.actions.set(&count, entry);
        self.action_count.set(count + 1);

        self.env().emit_event(ActionLogged {
            id: count,
            action_type,
            agent: caller,
            timestamp,
        });
    }

    /// Registra un swap ejecutado por el agente.
    /// Solo el agente puede llamar esta función.
    pub fn execute_swap(
        &mut self,
        token_in: String,
        token_out: String,
        amount_in: U512,
        amount_out: U512,
    ) {
        self.require_not_paused();
        self.require_agent();

        if token_in.is_empty()
            || token_out.is_empty()
            || token_in.len() > MAX_TOKEN_LEN
            || token_out.len() > MAX_TOKEN_LEN
        {
            self.revert(VaultError::InvalidInputLength);
        }

        if token_in == token_out {
            self.revert(VaultError::InvalidSwap);
        }

        if amount_in.is_zero() || amount_out.is_zero() {
            self.revert(VaultError::InvalidAmount);
        }

        let count = self.swap_count.get_or_default();
        if count >= MAX_SWAPS {
            self.revert(VaultError::ActionLimitReached);
        }

        let caller = self.env().caller();
        let timestamp = self.env().get_block_time();

        let record = SwapRecord {
            id: count,
            token_in: token_in.clone(),
            token_out: token_out.clone(),
            amount_in,
            amount_out,
            agent: caller,
            timestamp,
        };

        self.swaps.set(&count, record);
        self.swap_count.set(count + 1);

        self.env().emit_event(SwapExecuted {
            id: count,
            token_in,
            token_out,
            amount_in,
            amount_out,
            timestamp,
        });
    }

    // ─── Queries ────────────────────────────────────────────────────────────

    pub fn get_balance(&self, user: Address) -> U512 {
        self.balances.get_or_default(&user)
    }

    pub fn get_last_action(&self) -> Option<ActionEntry> {
        let count = self.action_count.get_or_default();
        if count == 0 {
            return None;
        }
        self.actions.get(&(count - 1))
    }

    pub fn get_action_count(&self) -> u64 {
        self.action_count.get_or_default()
    }

    pub fn get_action(&self, id: u64) -> Option<ActionEntry> {
        if id >= self.action_count.get_or_default() {
            return None;
        }
        self.actions.get(&id)
    }

    pub fn get_swap_count(&self) -> u64 {
        self.swap_count.get_or_default()
    }

    pub fn get_swap(&self, id: u64) -> Option<SwapRecord> {
        if id >= self.swap_count.get_or_default() {
            return None;
        }
        self.swaps.get(&id)
    }

    pub fn get_total_locked(&self) -> U512 {
        self.total_locked.get_or_default()
    }

    pub fn get_owner(&self) -> Address {
        self.owner.get_or_revert_with(VaultError::Unauthorized)
    }

    pub fn get_agent(&self) -> Address {
        self.agent.get_or_revert_with(VaultError::Unauthorized)
    }

    pub fn is_paused(&self) -> bool {
        self.paused.get_or_default()
    }

    // ─── Admin ──────────────────────────────────────────────────────────────

    /// Pausa el contrato. Solo el owner puede llamar.
    /// Idempotente: si ya está pausado no hace nada.
    pub fn pause(&mut self) {
        self.require_owner();
        if self.paused.get_or_default() {
            return;
        }
        let caller = self.env().caller();
        self.paused.set(true);
        self.env().emit_event(VaultPaused {
            paused_by: caller,
            timestamp: self.env().get_block_time(),
        });
    }

    /// Reanuda el contrato. Solo el owner puede llamar.
    /// Idempotente: si ya está activo no hace nada.
    pub fn unpause(&mut self) {
        self.require_owner();
        if !self.paused.get_or_default() {
            return;
        }
        let caller = self.env().caller();
        self.paused.set(false);
        self.env().emit_event(VaultUnpaused {
            unpaused_by: caller,
            timestamp: self.env().get_block_time(),
        });
    }

    /// Actualiza la dirección del agente autorizado. Solo el owner.
    pub fn set_agent(&mut self, new_agent: Address) {
        self.require_owner();
        let old_agent = self.agent.get_or_revert_with(VaultError::Unauthorized);
        let caller = self.env().caller();
        self.agent.set(new_agent);
        self.env().emit_event(AgentUpdated {
            old_agent,
            new_agent,
            updated_by: caller,
        });
    }

    /// Transfiere el ownership a una nueva dirección. Solo el owner actual puede llamar.
    /// Inmediato (single-step). Para mayor seguridad en producción considerar two-step.
    pub fn transfer_ownership(&mut self, new_owner: Address) {
        self.require_owner();
        let old_owner = self.owner.get_or_revert_with(VaultError::Unauthorized);
        self.owner.set(new_owner);
        self.env().emit_event(OwnershipTransferred { old_owner, new_owner });
    }
}

// ─── Access control helpers (no expuestos como entrypoints) ─────────────────

impl YieldVault {
    fn require_owner(&self) {
        let caller = self.env().caller();
        let owner = self.owner.get_or_revert_with(VaultError::Unauthorized);
        if caller != owner {
            self.revert(VaultError::Unauthorized);
        }
    }

    fn require_agent(&self) {
        let caller = self.env().caller();
        let agent = self.agent.get_or_revert_with(VaultError::Unauthorized);
        if caller != agent {
            self.revert(VaultError::Unauthorized);
        }
    }

    fn require_not_paused(&self) {
        if self.paused.get_or_default() {
            self.revert(VaultError::ContractPaused);
        }
    }
}
