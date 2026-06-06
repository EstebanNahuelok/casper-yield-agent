use odra::prelude::*;
use odra::casper_types::U512;

#[odra::event]
pub struct Deposit {
    pub user: Address,
    pub amount: U512,
    pub new_balance: U512,
    pub timestamp: u64,
}

#[odra::event]
pub struct Withdrawal {
    pub user: Address,
    pub amount: U512,
    pub remaining_balance: U512,
    pub timestamp: u64,
}

#[odra::event]
pub struct ActionLogged {
    pub id: u64,
    pub action_type: String,
    pub agent: Address,
    pub timestamp: u64,
}

#[odra::event]
pub struct SwapExecuted {
    pub id: u64,
    pub token_in: String,
    pub token_out: String,
    pub amount_in: U512,
    pub amount_out: U512,
    pub timestamp: u64,
}

#[odra::event]
pub struct AgentUpdated {
    pub old_agent: Address,
    pub new_agent: Address,
    pub updated_by: Address,
}

#[odra::event]
pub struct VaultPaused {
    pub paused_by: Address,
    pub timestamp: u64,
}

#[odra::event]
pub struct VaultUnpaused {
    pub unpaused_by: Address,
    pub timestamp: u64,
}

#[odra::event]
pub struct OwnershipTransferred {
    pub old_owner: Address,
    pub new_owner: Address,
}
