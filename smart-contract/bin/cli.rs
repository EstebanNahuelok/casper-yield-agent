use odra::host::{HostEnv, HostRef};
use odra::prelude::Address;
use odra::schema::casper_contract_schema::NamedCLType;
use odra::casper_types::U512;
use odra_cli::{
    deploy::{DeployScript, Error as DeployError},
    scenario::{Args, Error as ScenarioError, Scenario, ScenarioMetadata},
    CommandArg, ContractProvider, DeployedContractsContainer, DeployerExt, OdraCli,
};
use std::str::FromStr;
use yield_vault::vault::{YieldVault, YieldVaultInitArgs};

const DEPLOY_GAS: u64 = 500_000_000_000;

pub struct VaultDeployScript;

impl DeployScript for VaultDeployScript {
    fn deploy(
        &self,
        env: &HostEnv,
        container: &mut DeployedContractsContainer,
    ) -> core::result::Result<(), DeployError> {
        let agent_str =
            std::env::var("ODRA_AGENT_ADDRESS").map_err(|_| DeployError::OdraError {
                message: "ODRA_AGENT_ADDRESS env var is required (e.g. account-hash-abc123...)"
                    .to_string(),
            })?;

        let agent = Address::from_str(&agent_str).map_err(|e| DeployError::OdraError {
            message: format!("Invalid ODRA_AGENT_ADDRESS '{agent_str}': {e:?}"),
        })?;

        odra_cli::log(format!("Deploying YieldVault with agent: {agent_str}"));
        YieldVault::load_or_deploy(env, YieldVaultInitArgs { agent }, container, DEPLOY_GAS)?;
        Ok(())
    }
}

// ── deposit / withdraw scenarios ──────────────────────────────────────────────

pub struct DepositScenario;

impl Scenario for DepositScenario {
    fn args(&self) -> Vec<CommandArg> {
        vec![CommandArg::new(
            "amount_motes",
            "Amount to deposit in motes (1 CSPR = 1_000_000_000 motes)",
            NamedCLType::String,
        )
        .required()]
    }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let amount_str: String = args.get_single("amount_motes")?;
        let amount = U512::from_dec_str(&amount_str).map_err(|_| {
            ScenarioError::MissingScenarioArg(format!("Invalid amount_motes: {amount_str}"))
        })?;

        // Proxy wasm + contract call on Casper testnet needs ~25 CSPR gas
        env.set_gas(25_000_000_000);
        let mut vault = container.contract_ref::<YieldVault>(env)?;
        odra_cli::log(format!(
            "Depositing {} motes ({:.4} CSPR)...",
            amount,
            amount.as_u64() as f64 / 1_000_000_000.0
        ));
        vault.with_tokens(amount).deposit();
        odra_cli::log("Deposit successful.".to_string());
        Ok(())
    }
}

impl ScenarioMetadata for DepositScenario {
    const NAME: &'static str = "deposit";
    const DESCRIPTION: &'static str = "Deposit CSPR into the vault (payable)";
}

// ── read-only scenarios ────────────────────────────────────────────────────────

pub struct GetStatusScenario;

impl Scenario for GetStatusScenario {
    fn args(&self) -> Vec<CommandArg> { vec![] }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        _args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let vault = container.contract_ref::<YieldVault>(env)?;
        odra_cli::log(format!("owner:        {:?}", vault.get_owner()));
        odra_cli::log(format!("agent:        {:?}", vault.get_agent()));
        odra_cli::log(format!("paused:       {}", vault.is_paused()));
        odra_cli::log(format!("total_locked: {} motes", vault.get_total_locked()));
        odra_cli::log(format!("action_count: {}", vault.get_action_count()));
        odra_cli::log(format!("swap_count:   {}", vault.get_swap_count()));
        Ok(())
    }
}

impl ScenarioMetadata for GetStatusScenario {
    const NAME: &'static str = "get_status";
    const DESCRIPTION: &'static str = "Print contract state: owner, agent, paused, totals";
}

pub struct GetBalanceScenario;

impl Scenario for GetBalanceScenario {
    fn args(&self) -> Vec<CommandArg> {
        vec![CommandArg::new(
            "user",
            "Account address (e.g. account-hash-abc123...)",
            NamedCLType::String,
        )
        .required()]
    }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let user_str: String = args.get_single("user")?;
        let user = Address::from_str(&user_str)
            .map_err(|_| ScenarioError::MissingScenarioArg(format!("Invalid address: {user_str}")))?;
        let vault = container.contract_ref::<YieldVault>(env)?;
        let balance = vault.get_balance(user);
        odra_cli::log(format!(
            "balance of {user_str}: {} motes ({:.4} CSPR)",
            balance,
            balance.as_u64() as f64 / 1_000_000_000.0
        ));
        Ok(())
    }
}

impl ScenarioMetadata for GetBalanceScenario {
    const NAME: &'static str = "get_balance";
    const DESCRIPTION: &'static str = "Query CSPR balance of an account in the vault";
}

// ── agent scenarios ────────────────────────────────────────────────────────────

pub struct LogActionScenario;

impl Scenario for LogActionScenario {
    fn args(&self) -> Vec<CommandArg> {
        vec![
            CommandArg::new("action_type", "Action type (e.g. REBALANCE, HARVEST)", NamedCLType::String).required(),
            CommandArg::new("params", "JSON params string", NamedCLType::String).required(),
        ]
    }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let action_type: String = args.get_single("action_type")?;
        let params: String = args.get_single("params")?;
        let mut vault = container.contract_ref::<YieldVault>(env)?;
        odra_cli::log(format!("Logging action: type={action_type} params={params}"));
        vault.log_action(action_type, params);
        let count = vault.get_action_count();
        odra_cli::log(format!("Action logged. Total actions on-chain: {count}"));
        Ok(())
    }
}

impl ScenarioMetadata for LogActionScenario {
    const NAME: &'static str = "log_action";
    const DESCRIPTION: &'static str = "Log an agent action on-chain";
}

pub struct ExecuteSwapScenario;

impl Scenario for ExecuteSwapScenario {
    fn args(&self) -> Vec<CommandArg> {
        vec![
            CommandArg::new("token_in",   "Input token symbol (e.g. CSPR)",  NamedCLType::String).required(),
            CommandArg::new("token_out",  "Output token symbol (e.g. USDC)", NamedCLType::String).required(),
            CommandArg::new("amount_in",  "Amount in (motes as integer)",    NamedCLType::String).required(),
            CommandArg::new("amount_out", "Amount out (motes as integer)",   NamedCLType::String).required(),
        ]
    }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let token_in:   String = args.get_single("token_in")?;
        let token_out:  String = args.get_single("token_out")?;
        let amount_in_str:  String = args.get_single("amount_in")?;
        let amount_out_str: String = args.get_single("amount_out")?;

        let amount_in = U512::from_dec_str(&amount_in_str)
            .map_err(|_| ScenarioError::MissingScenarioArg(format!("Invalid amount_in: {amount_in_str}")))?;
        let amount_out = U512::from_dec_str(&amount_out_str)
            .map_err(|_| ScenarioError::MissingScenarioArg(format!("Invalid amount_out: {amount_out_str}")))?;

        let mut vault = container.contract_ref::<YieldVault>(env)?;
        odra_cli::log(format!("Executing swap: {amount_in} {token_in} → {amount_out} {token_out}"));
        vault.execute_swap(token_in, token_out, amount_in, amount_out);
        let count = vault.get_swap_count();
        odra_cli::log(format!("Swap recorded on-chain. Total swaps: {count}"));
        Ok(())
    }
}

impl ScenarioMetadata for ExecuteSwapScenario {
    const NAME: &'static str = "execute_swap";
    const DESCRIPTION: &'static str = "Record a swap execution on-chain";
}

pub struct GetLastActionScenario;

impl Scenario for GetLastActionScenario {
    fn args(&self) -> Vec<CommandArg> { vec![] }

    fn run(
        &self,
        env: &HostEnv,
        container: &DeployedContractsContainer,
        _args: Args,
    ) -> core::result::Result<(), ScenarioError> {
        let vault = container.contract_ref::<YieldVault>(env)?;
        match vault.get_last_action() {
            Some(a) => odra_cli::log(format!(
                "last_action: id={} type={} params={} timestamp={}",
                a.id, a.action_type, a.params, a.timestamp
            )),
            None => odra_cli::log("no actions recorded yet".to_string()),
        }
        Ok(())
    }
}

impl ScenarioMetadata for GetLastActionScenario {
    const NAME: &'static str = "get_last_action";
    const DESCRIPTION: &'static str = "Show the most recent agent action recorded on-chain";
}

pub fn main() {
    OdraCli::new()
        .about("CLI for YieldVault — Casper Agentic Buildathon 2026")
        .deploy(VaultDeployScript)
        .contract::<YieldVault>()
        .scenario(DepositScenario)
        .scenario(GetStatusScenario)
        .scenario(GetBalanceScenario)
        .scenario(LogActionScenario)
        .scenario(ExecuteSwapScenario)
        .scenario(GetLastActionScenario)
        .build()
        .run();
}
