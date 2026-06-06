#[cfg(test)]
mod tests {
    use odra::casper_types::U512;
    use odra::host::{Deployer, HostRef};
    use odra_test::env;

    use crate::vault::{YieldVault, YieldVaultInitArgs};

    /// Invariante: total_locked == suma de todos los balances individuales.
    #[test]
    fn invariant_total_locked_equals_sum_of_balances() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let users: Vec<_> = (2..6).map(|i| env.get_account(i)).collect();
        let amounts: Vec<U512> = vec![
            U512::from(1_000_000_000u64),
            U512::from(2_000_000_000u64),
            U512::from(500_000_000u64),
            U512::from(3_000_000_000u64),
        ];

        // Depositar
        for (user, amount) in users.iter().zip(amounts.iter()) {
            env.set_caller(*user);
            vault.with_tokens(*amount).deposit();
        }

        let expected_total: U512 = amounts.iter().fold(U512::zero(), |acc, a| acc + *a);
        assert_eq!(vault.get_total_locked(), expected_total);

        // Retirar la mitad de cada uno
        for (user, amount) in users.iter().zip(amounts.iter()) {
            env.set_caller(*user);
            vault.withdraw(*amount / 2);
        }

        let expected_after: U512 = amounts.iter().map(|a| *a - *a / 2).sum();
        assert_eq!(vault.get_total_locked(), expected_after);

        // Verificar que la suma de balances individuales coincide con total_locked
        let sum_of_balances: U512 = users
            .iter()
            .fold(U512::zero(), |acc, user| acc + vault.get_balance(*user));

        assert_eq!(vault.get_total_locked(), sum_of_balances);
    }

    #[test]
    fn unregistered_user_has_zero_balance() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let stranger = env.get_account(9);
        assert_eq!(vault.get_balance(stranger), U512::zero());
    }

    #[test]
    fn total_locked_starts_at_zero() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);

        env.set_caller(owner);
        let vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        assert_eq!(vault.get_total_locked(), U512::zero());
    }

    #[test]
    fn balance_unchanged_after_other_user_withdraws() {
        let env = env();
        let owner = env.get_account(0);
        let agent = env.get_account(1);
        let user_a = env.get_account(2);
        let user_b = env.get_account(3);

        env.set_caller(owner);
        let mut vault = YieldVault::deploy(&env, YieldVaultInitArgs { agent });

        let amount_a = U512::from(1_000_000_000u64);
        let amount_b = U512::from(2_000_000_000u64);

        env.set_caller(user_a);
        vault.with_tokens(amount_a).deposit();

        env.set_caller(user_b);
        vault.with_tokens(amount_b).deposit();

        // user_b retira su saldo completo
        vault.withdraw(amount_b);

        // El saldo de user_a no debe haberse modificado
        assert_eq!(vault.get_balance(user_a), amount_a);
        assert_eq!(vault.get_total_locked(), amount_a);
    }
}
