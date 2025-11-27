import pytest
import json
from pagr.portfolio import Portfolio, Position
from pathlib import Path

def test_add_position_new():
    p = Portfolio(name="Test", currency="USD", last_updated="", positions=[])
    p.add_position("AAPL", 10)
    assert len(p.positions) == 1
    assert p.positions[0].ticker == "AAPL"
    assert p.positions[0].quantity == 10

def test_add_position_existing():
    p = Portfolio(name="Test", currency="USD", last_updated="", positions=[
        Position(ticker="AAPL", quantity=10, book_value=0)
    ])
    p.add_position("AAPL", 5)
    assert len(p.positions) == 1
    assert p.positions[0].quantity == 15

def test_add_position_remove_zero():
    p = Portfolio(name="Test", currency="USD", last_updated="", positions=[
        Position(ticker="AAPL", quantity=10, book_value=0)
    ])
    p.add_position("AAPL", -10)
    assert len(p.positions) == 0

def test_add_position_short():
    p = Portfolio(name="Test", currency="USD", last_updated="", positions=[])
    p.add_position("AAPL", -10)
    assert len(p.positions) == 1
    assert p.positions[0].quantity == -10

def test_save_portfolio(tmp_path):
    p = Portfolio(name="Test Save", currency="EUR", last_updated="2024-01-01", positions=[
        Position(ticker="AAPL", quantity=10, book_value=100)
    ])
    save_path = tmp_path / "saved.pagr"
    p.save(save_path)
    
    assert save_path.exists()
    
    # Reload to verify
    with open(save_path, 'r') as f:
        data = json.load(f)
        
    assert data["portfolio_name"] == "Test Save"
    assert data["currency"] == "EUR"
    assert len(data["positions"]) == 1
    assert data["positions"][0]["ticker"] == "AAPL"
    assert data["positions"][0]["quantity"] == 10
