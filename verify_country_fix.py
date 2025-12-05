#!/usr/bin/env python
"""Verify that Country nodes are created with proper data."""

from src.pagr.fds.models.fibo import Country
from src.pagr.fds.graph.builder import GraphBuilder

# Create test Country objects
countries = {
    "US": Country(
        fibo_id="fibo:country:US",
        name="United States",
        iso_code="US",
    ),
    "FR": Country(
        fibo_id="fibo:country:FR",
        name="France",
        iso_code="FR",
    ),
    "GB": Country(
        fibo_id="fibo:country:GB",
        name="United Kingdom",
        iso_code="GB",
    ),
}

# Create graph builder
builder = GraphBuilder()

# Add country nodes
builder.add_country_nodes(countries)

# Get statements
statements = builder.get_all_statements()

print("Generated Cypher statements for Country nodes:")
print("=" * 80)
for i, stmt in enumerate(statements, 1):
    print(f"\n{i}. {stmt}")

print("\n" + "=" * 80)
print(f"\nTotal statements: {len(statements)}")
print("\nExpected behavior:")
print("- Each Country node MERGES on iso_code (unique identifier)")
print("- Properties SET: fibo_id, name")
print("- Result: Country nodes with complete data (no None values)")
