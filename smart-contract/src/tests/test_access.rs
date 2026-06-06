#[cfg(test)]
mod tests {
    use odra::host::Deployer;
    use odra_test::env;

    use crate::events::{AgentUpdated, OwnershipTransferred, VaultPaused, VaultUnpaused};
    use crate::vault::{YieldVault, YieldVaultInitArgs};

    #[test]
    fn init_sets_owner_and_agent() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert_eq!(vault.get_owner(), owner);
        assert_eq!(vault.get_agent(), agent);
    }

    #[test]
    fn only_owner_can_pause() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert!(!vault.is_paused());
        vault.pause();
        assert!(vault.is_paused());
        assert!(env.emitted_event(&vault, VaultPaused { paused_by: owner, timestamp: 0 }));
    }

    #[test]
    #[should_panic]
    fn non_owner_cannot_pause() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let attacker = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(attacker);
        vault.pause();
    }

    #[test]
    fn only_owner_can_unpause() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.pause();
        assert!(vault.is_paused());
        vault.unpause();
        assert!(!vault.is_paused());
        assert!(env.emitted_event(&vault, VaultUnpaused { unpaused_by: owner, timestamp: 0 }));
    }

    #[test]
    #[should_panic]
    fn non_owner_cannot_unpause() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let attacker = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });
        vault.pause();

        env.set_caller(attacker);
        vault.unpause();
    }

    #[test]
    fn owner_can_update_agent() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let new_agent = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.set_agent(new_agent);
        assert_eq!(vault.get_agent(), new_agent);
        assert!(env.emitted_event(
            &vault,
            AgentUpdated { old_agent: agent, new_agent, updated_by: owner },
        ));
    }

    #[test]
    #[should_panic]
    fn non_owner_cannot_set_agent() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let attacker = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(attacker);
        vault.set_agent(attacker);
    }

    #[test]
    #[should_panic]
    fn agent_cannot_log_action_after_revoked() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let new_agent = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        // Revocar agente viejo
        vault.set_agent(new_agent);

        // Agente viejo intenta loggear — debe fallar
        env.set_caller(agent);
        vault.log_action("REBALANCE".into(), "{}".into());
    }

    #[test]
    fn pause_is_idempotent() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.pause();
        vault.pause(); // segunda llamada no debe panic
        assert!(vault.is_paused());
    }

    #[test]
    fn unpause_is_idempotent() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.unpause(); // ya está sin pausar — no debe panic
        assert!(!vault.is_paused());
    }

    #[test]
    fn owner_can_transfer_ownership() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let new_owner = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.transfer_ownership(new_owner);
        assert_eq!(vault.get_owner(), new_owner);
        assert!(env.emitted_event(
            &vault,
            OwnershipTransferred { old_owner: owner, new_owner },
        ));

        // El nuevo owner puede pausar; el viejo ya no puede
        env.set_caller(new_owner);
        vault.pause();
        assert!(vault.is_paused());
    }

    #[test]
    #[should_panic]
    fn non_owner_cannot_transfer_ownership() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let attacker = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        env.set_caller(attacker);
        vault.transfer_ownership(attacker);
    }

    #[test]
    #[should_panic]
    fn old_owner_loses_access_after_transfer() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let new_owner = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        vault.transfer_ownership(new_owner);

        // El owner viejo ya no tiene acceso
        vault.pause();
    }
}
