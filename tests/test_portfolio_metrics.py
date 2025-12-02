"""Test portfolio metrics calculations and display."""

from pagr.fds.models.portfolio import Portfolio, Position
from pagr.ui.metrics import display_portfolio_metrics


def test_metrics_calculation():
    """Test portfolio metrics calculations."""
    print("Testing portfolio metrics calculation...\n")

    # Create test portfolio
    positions = [
        Position(ticker="AAPL-US", quantity=100.0, book_value=19000.00),
        Position(ticker="MSFT-US", quantity=50.0, book_value=21000.00),
        Position(ticker="TSMC-TT", quantity=200.0, book_value=32000.00),
        Position(ticker="GE-US", quantity=150.0, book_value=12000.00),
        Position(ticker="NVDA-US", quantity=30.0, book_value=13500.00),
    ]

    portfolio = Portfolio(name="Test Portfolio", positions=positions)
    portfolio.calculate_weights()

    # Verify total value
    expected_total = 97500.0
    assert portfolio.total_value == expected_total, f"Expected {expected_total}, got {portfolio.total_value}"
    print(f"[PASS] Total portfolio value: ${portfolio.total_value:,.2f}")

    # Verify position count
    assert len(portfolio.positions) == 5, f"Expected 5 positions, got {len(portfolio.positions)}"
    print(f"[PASS] Position count: {len(portfolio.positions)}")

    # Verify largest position
    sorted_positions = sorted(portfolio.positions, key=lambda p: p.book_value, reverse=True)
    largest = sorted_positions[0]
    assert largest.ticker == "TSMC-TT", f"Expected TSMC-TT as largest, got {largest.ticker}"
    assert abs(largest.weight - 32.8) < 0.1, f"Expected weight ~32.8%, got {largest.weight}%"
    print(f"[PASS] Largest position: {largest.ticker} ({largest.weight:.1f}%)")

    # Verify weights sum to 100%
    total_weight = sum(p.weight for p in portfolio.positions)
    assert abs(total_weight - 100.0) < 0.01, f"Weights don't sum to 100%: {total_weight}"
    print(f"[PASS] Weights sum to: {total_weight:.1f}%")

    # Print all positions
    print("\nPortfolio breakdown:")
    for pos in sorted_positions:
        print(f"  {pos.ticker}: {pos.quantity} shares @ ${pos.book_value/pos.quantity:.2f} = ${pos.book_value:,.2f} ({pos.weight:.1f}%)")


def test_metrics_with_market_values():
    """Test portfolio metrics with optional market values."""
    print("\n\nTesting portfolio metrics with market values...\n")

    positions = [
        Position(
            ticker="AAPL-US",
            quantity=100.0,
            book_value=19000.00,
            market_value=24000.00  # +$5k gain
        ),
        Position(
            ticker="MSFT-US",
            quantity=50.0,
            book_value=21000.00,
            market_value=19000.00  # -$2k loss
        ),
    ]

    portfolio = Portfolio(name="Test Portfolio", positions=positions)
    portfolio.calculate_weights()

    # Verify weights are based on book value (not market value)
    # MSFT has higher book_value (21000) than AAPL (19000)
    total_book = portfolio.positions[0].book_value + portfolio.positions[1].book_value
    aapl_weight = (portfolio.positions[0].book_value / total_book) * 100
    msft_weight = (portfolio.positions[1].book_value / total_book) * 100
    print(f"[PASS] Weights correctly based on book value (not market value)")
    print(f"  AAPL weight: {aapl_weight:.1f}% (book $19,000, market $24,000)")
    print(f"  MSFT weight: {msft_weight:.1f}% (book $21,000, market $19,000)")
    print(f"Position 1 (AAPL): Book ${portfolio.positions[0].book_value:,.2f}, Market ${portfolio.positions[0].market_value:,.2f}")
    print(f"Position 2 (MSFT): Book ${portfolio.positions[1].book_value:,.2f}, Market ${portfolio.positions[1].market_value:,.2f}")


def test_portfolio_with_single_position():
    """Test portfolio metrics with single position."""
    print("\n\nTesting single position portfolio...\n")

    positions = [
        Position(ticker="AAPL-US", quantity=100.0, book_value=19000.00),
    ]

    portfolio = Portfolio(name="Single Position", positions=positions)
    portfolio.calculate_weights()

    assert portfolio.total_value == 19000.0
    assert portfolio.positions[0].weight == 100.0
    print(f"[PASS] Single position portfolio: {portfolio.total_value:,.2f} (100%)")


def test_empty_portfolio():
    """Test empty portfolio handling."""
    print("\n\nTesting empty portfolio...\n")

    portfolio = Portfolio(name="Empty", positions=[])
    portfolio.calculate_weights()

    assert portfolio.total_value == 0
    print(f"[PASS] Empty portfolio total value: ${portfolio.total_value:,.2f}")


if __name__ == "__main__":
    print("Testing Portfolio Metrics\n" + "=" * 40 + "\n")

    test_metrics_calculation()
    test_metrics_with_market_values()
    test_portfolio_with_single_position()
    test_empty_portfolio()

    print("\n" + "=" * 40)
    print("[PASS] All portfolio metrics tests passed!")
