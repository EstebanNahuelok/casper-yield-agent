use odra::prelude::*;
use odra::casper_types::U512;

/// Registro de una acción ejecutada por el agente IA.
#[odra::odra_type]
pub struct ActionEntry {
    pub id: u64,
    /// Tipo de acción: "REBALANCE", "HARVEST", "COMPOUND", etc.
    pub action_type: String,
    pub agent: Address,
    /// Parámetros de la acción en formato JSON (máx 512 bytes).
    pub params: String,
    pub timestamp: u64,
}

/// Registro de un swap ejecutado por el agente.
#[odra::odra_type]
pub struct SwapRecord {
    pub id: u64,
    pub token_in: String,
    pub token_out: String,
    pub amount_in: U512,
    pub amount_out: U512,
    pub agent: Address,
    pub timestamp: u64,
}
