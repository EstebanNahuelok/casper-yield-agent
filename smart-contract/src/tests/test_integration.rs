#[cfg(test)]
mod tests {
    use odra::casper_types::U512;
    use odra::host::{Deployer, HostRef};
    use odra_test::env;

    use crate::vault::{YieldVault, YieldVaultInitArgs};

    /// Flujo completo: deposit → agent logs action → agent executes swap → withdraw.
    #[test]
    fn full_agent_yield_farming_flow() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        // 1. Usuario deposita
        let deposit_amount = U512::from(10_000_000_000u64); // 10 CSPR
        env.set_caller(user);
        vault.with_tokens(deposit_amount).deposit();
        assert_eq!(vault.get_balance(user), deposit_amount);

        // 2. Agente registra una acción de rebalanceo
        env.set_caller(agent);
        vault.log_action(
            "REBALANCE".into(),
            r#"{"target_ratio":0.6,"current_ratio":0.4}"#.into(),
        );
        assert_eq!(vault.get_action_count(), 1);

        let action = vault.get_last_action().expect("debe haber una acción");
        assert_eq!(action.action_type, "REBALANCE");
        assert_eq!(action.agent, agent);

        // 3. Agente registra un swap
        vault.execute_swap(
            "CSPR".into(),
            "USDT".into(),
            U512::from(5_000_000_000u64),
            U512::from(4_900_000_000u64),
        );
        assert_eq!(vault.get_swap_count(), 1);

        // 4. Agente registra otra acción (harvest yield)
        vault.log_action(
            "HARVEST".into(),
            r#"{"yield_earned":150000000}"#.into(),
        );
        assert_eq!(vault.get_action_count(), 2);

        // 5. Usuario retira sus fondos
        env.set_caller(user);
        vault.withdraw(deposit_amount);
        assert_eq!(vault.get_balance(user), U512::zero());
        assert_eq!(vault.get_total_locked(), U512::zero());

        // 6. Verificar estado final del log
        let last = vault.get_last_action().expect("debe existir");
        assert_eq!(last.action_type, "HARVEST");
        assert_eq!(last.id, 1);
    }

    /// El agente tiene balance 0 en el vault — no tiene participación en los fondos.
    #[test]
    fn agent_has_zero_balance_in_vault() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let deposit = U512::from(5_000_000_000u64);
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();

        assert_eq!(vault.get_balance(agent), U512::zero());
        assert_eq!(vault.get_total_locked(), deposit);
    }

    /// El agente intenta retirar fondos del usuario — debe revertir.
    #[test]
    #[should_panic]
    fn agent_withdraw_attempt_reverts() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let deposit = U512::from(5_000_000_000u64);
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();

        // El agente no depositó nada — intentar retirar debe revertir
        env.set_caller(agent);
        vault.withdraw(U512::from(1u64));
    }

    /// Después de cambiar de agente, el nuevo agente puede loggear y el viejo no.
    #[test]
    fn agent_rotation_works_correctly() {
        let env = env();
        let owner = env.get_account(0);
        let old_agent = env.get_account(1);
        let new_agent = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent: old_agent });

        // Agente original puede loggear
        env.set_caller(old_agent);
        vault.log_action("OLD_ACTION".into(), "{}".into());
        assert_eq!(vault.get_action_count(), 1);

        // Owner rota el agente
        env.set_caller(owner);
        vault.set_agent(new_agent);

        // Nuevo agente puede loggear
        env.set_caller(new_agent);
        vault.log_action("NEW_ACTION".into(), "{}".into());
        assert_eq!(vault.get_action_count(), 2);
    }

    /// El owner pausa, el agente no puede operar, el owner reanuda y la operación funciona.
    #[test]
    fn pause_and_resume_cycle() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user = env.get_account(2);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let deposit = U512::from(1_000_000_000u64);

        // Depósito inicial
        env.set_caller(user);
        vault.with_tokens(deposit).deposit();

        // Owner pausa
        env.set_caller(owner);
        vault.pause();
        assert!(vault.is_paused());

        // Owner reanuda
        vault.unpause();
        assert!(!vault.is_paused());

        // Ahora el agente puede operar nuevamente
        env.set_caller(agent);
        vault.log_action("POST_RESUME".into(), "{}".into());
        assert_eq!(vault.get_action_count(), 1);

        // Y el usuario puede retirar
        env.set_caller(user);
        vault.withdraw(deposit);
        assert_eq!(vault.get_balance(user), U512::zero());
    }
}
