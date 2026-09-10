

#This is not investment advice

"""Five-year FCFF discounted cash flow model (USD millions)."""

# Editable inputs
# Tesla FY2025 Form 10-K (filed Jan. 29, 2026); USD millions.
# FCFF proxy: operating cash flow ($14,747) less cash capex ($8,527).
starting_fcff = 6220.0                # USD millions, at the end of Year 0
growth_rates = [0.08, 0.06, 0.05, 0.04, 0.03]
wacc = 0.10
terminal_growth = 0.03
non_operating_cash = 44059.0          # Cash, equivalents, and short-term investments
debt = 8177.0                         # Total debt carrying value; excludes finance leases
diluted_shares = 3528.0               # FY2025 weighted-average diluted shares, in millions

# Editable sensitivity and reverse-DCF inputs
sensitivity_wacc_values = [0.09, 0.10, 0.11]
sensitivity_terminal_growth_values = [0.02, 0.03, 0.04]
target_share_price = 367.81           # TSLA quoted price on Sep. 10, 2026
reverse_growth_shift_lower_percentage_points = -5.0
reverse_growth_shift_upper_percentage_points = 10.0


def calculate_dcf(discount_rate, perpetual_growth_rate, explicit_growth_rates):
    """Return DCF outputs for one set of valuation assumptions."""
    fcff_by_year = []
    fcff = starting_fcff
    for growth_rate in explicit_growth_rates:
        fcff *= 1.0 + growth_rate
        fcff_by_year.append(fcff)

    pv_explicit_fcff = sum(
        yearly_fcff / (1.0 + discount_rate) ** year
        for year, yearly_fcff in enumerate(fcff_by_year, start=1)
    )
    terminal_value_year_5 = (
        fcff_by_year[-1] * (1.0 + perpetual_growth_rate)
        / (discount_rate - perpetual_growth_rate)
    )
    pv_terminal_value = terminal_value_year_5 / (1.0 + discount_rate) ** len(fcff_by_year)
    enterprise_value = pv_explicit_fcff + pv_terminal_value
    equity_value = enterprise_value + non_operating_cash - debt
    value_per_diluted_share = equity_value / diluted_shares
    pv_terminal_value_share_of_ev = pv_terminal_value / enterprise_value

    return {
        "fcff_by_year": fcff_by_year,
        "pv_explicit_fcff": pv_explicit_fcff,
        "terminal_value_year_5": terminal_value_year_5,
        "pv_terminal_value": pv_terminal_value,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "value_per_diluted_share": value_per_diluted_share,
        "pv_terminal_value_share_of_ev": pv_terminal_value_share_of_ev,
    }


def print_sensitivity_grid():
    print("\nSensitivity Grid: Value per Diluted Share")
    header = "Terminal Growth \\ WACC" + "".join(
        f" | {discount_rate:>8.2%}" for discount_rate in sensitivity_wacc_values
    )
    print(header)
    print("-" * len(header))
    for perpetual_growth_rate in sensitivity_terminal_growth_values:
        row = f"{perpetual_growth_rate:>20.2%}"
        for discount_rate in sensitivity_wacc_values:
            if perpetual_growth_rate >= discount_rate:
                cell = "INVALID"
            else:
                value = calculate_dcf(
                    discount_rate, perpetual_growth_rate, growth_rates
                )["value_per_diluted_share"]
                cell = f"${value:.4f}"
            row += f" | {cell:>8}"
        print(row)


def solve_reverse_dcf():
    """Solve for a uniform percentage-point shift to explicit growth rates."""
    lower_shift = reverse_growth_shift_lower_percentage_points / 100.0
    upper_shift = reverse_growth_shift_upper_percentage_points / 100.0
    if lower_shift > upper_shift:
        return None, "Invalid bracket: lower bound is greater than upper bound."

    def value_for_shift(shift):
        shifted_growth_rates = [growth_rate + shift for growth_rate in growth_rates]
        return calculate_dcf(wacc, terminal_growth, shifted_growth_rates)[
            "value_per_diluted_share"
        ]

    lower_growth_rates = [growth_rate + lower_shift for growth_rate in growth_rates]
    upper_growth_rates = [growth_rate + upper_shift for growth_rate in growth_rates]
    if any(growth_rate <= -1.0 for growth_rate in lower_growth_rates + upper_growth_rates):
        return None, (
            "Invalid bracket: it pushes at least one annual growth rate to "
            "-100% or below."
        )

    lower_difference = value_for_shift(lower_shift) - target_share_price
    upper_difference = value_for_shift(upper_shift) - target_share_price
    if lower_difference == 0.0:
        return lower_shift, None
    if upper_difference == 0.0:
        return upper_shift, None
    if lower_difference * upper_difference > 0.0:
        return None, "No solution in this bracket."

    for _ in range(100):
        midpoint = (lower_shift + upper_shift) / 2.0
        midpoint_difference = value_for_shift(midpoint) - target_share_price
        if abs(midpoint_difference) < 1e-10:
            return midpoint, None
        if lower_difference * midpoint_difference < 0.0:
            upper_shift = midpoint
        else:
            lower_shift = midpoint
            lower_difference = midpoint_difference

    return None, "No solution found to the required precision in this bracket."


def print_reverse_dcf():
    print("\nReverse DCF: Uniform Explicit-Growth Shift")
    print(f"Target Share Price: ${target_share_price:.4f}")
    print("Inputs held fixed:")
    print(f"  Starting FCFF: {starting_fcff:.4f}")
    print(f"  Base explicit growth rates: {growth_rates}")
    print(f"  WACC: {wacc:.2%}")
    print(f"  Terminal growth: {terminal_growth:.2%}")
    print(f"  Non-operating cash: {non_operating_cash:.4f}")
    print(f"  Debt: {debt:.4f}")
    print(f"  Diluted shares: {diluted_shares:.4f}")
    print(
        "  Search bracket (percentage points): "
        f"[{reverse_growth_shift_lower_percentage_points:.4f}, "
        f"{reverse_growth_shift_upper_percentage_points:.4f}]"
    )
    solved_shift, message = solve_reverse_dcf()
    if message:
        print(message)
    else:
        print(f"Solved uniform growth shift: {solved_shift * 100.0:.8f} percentage points")


def main():
    if terminal_growth >= wacc:
        raise SystemExit(
            "Error: terminal growth must be less than WACC for the Gordon-growth formula."
        )

    results = calculate_dcf(wacc, terminal_growth, growth_rates)
    fcff_by_year = results["fcff_by_year"]
    pv_explicit_fcff = results["pv_explicit_fcff"]
    terminal_value_year_5 = results["terminal_value_year_5"]
    pv_terminal_value = results["pv_terminal_value"]
    enterprise_value = results["enterprise_value"]
    equity_value = results["equity_value"]
    value_per_diluted_share = results["value_per_diluted_share"]
    pv_terminal_value_share_of_ev = results["pv_terminal_value_share_of_ev"]

    for year, yearly_fcff in enumerate(fcff_by_year, start=1):
        print(f"FCFF Year {year}: {yearly_fcff:.4f}")
    print(f"Present Value of Explicit FCFF: {pv_explicit_fcff:.4f}")
    print(f"Terminal Value at Year 5: {terminal_value_year_5:.4f}")
    print(f"Present Value of Terminal Value: {pv_terminal_value:.4f}")
    print(f"Enterprise Value: {enterprise_value:.4f}")
    print(f"Equity Value: {equity_value:.4f}")
    print(f"Value per Diluted Share: {value_per_diluted_share:.4f}")
    print(
        "PV Terminal Value as Share of Enterprise Value: "
        f"{pv_terminal_value_share_of_ev:.4f}"
    )
    print_sensitivity_grid()
    print_reverse_dcf()


if __name__ == "__main__":
    main()
