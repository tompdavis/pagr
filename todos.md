# Project Todos

## Pending Tasks

- [ ] Get dirty price instead of clean price from Formula API
  - Currently using clean price from the Formula API
  - Need to investigate if Formula API supports dirty price formulas
  - Update `get_bond_prices_formula_api()` to fetch dirty price
  - Update response parsing to extract dirty price field
  - Update pipeline and enricher to use dirty price instead of clean price
- [ ] Add more enrichment like subsidiaries 
- [ ] Add regions 
- [ ] Add multi-portfolios 
- [ ] Add equity options 
