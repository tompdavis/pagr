# PAGR - Portfolio Analysis with Graph Relationships

**PAGR** is a web-based portfolio analysis application that combines FactSet financial data enrichment with FIBO ontology graph relationships. It enables sophisticated portfolio analysis through interactive visualizations and semantic queries.

## Overview

PAGR transforms portfolio data from simple CSV files into rich, interconnected graph structures:

```
CSV Upload
    ↓
Load & Validate Positions
    ↓
FactSet API Enrichment (company profiles, executives, subsidiaries)
    ↓
FIBO Ontology Graph Building (Memgraph)
    ↓
Interactive Analysis & Visualization
```

## Features

### 1. **CSV-Based Portfolio Management**
- Upload portfolio data in simple CSV format
- Support for ticker, quantity, market value, security type, ISIN, CUSIP
- Automatic validation and error handling

### 2. **FactSet API Enrichment**
- Company profiles (sector, industry, market cap)
- Executive/leadership information
- Corporate structure (subsidiaries, parent companies)
- Geographic data and country classification

### 3. **FIBO Ontology Graph**
- **Nodes**: Portfolio, Position, Company, Country, Region, Executive
- **Relationships**: CONTAINS, ISSUED_BY, HEADQUARTERED_IN, CEO_OF, HAS_SUBSIDIARY, PART_OF
- Memgraph graph database for high-performance queries

### 4. **Analysis Views**

#### Tabular Analysis
- Position-level breakdown with market values and weights
- Sector exposure analysis with interactive charts
- Geographic exposure by country
- Regional distribution pie charts

#### Graph Visualization
- Interactive FIBO relationship graph
- Toggleable visualization of executives, countries, subsidiaries
- Color-coded nodes by entity type
- Relationship labels and metadata

## Technology Stack

- **Frontend**: Streamlit web UI
- **Graph Database**: Memgraph (Neo4j-compatible)
- **Data Enrichment**: FactSet API
- **Visualization**: Plotly (charts) + PyVis (graphs)
- **Data Models**: Pydantic with FIBO ontology
- **Package Manager**: uv (modern Python package manager)
- **Language**: Python 3.12+

## Installation

### Prerequisites

1. **Memgraph Server** (running on 127.0.0.1:7687)
   ```bash
   docker run -p 7687:7687 -p 7444:7444 memgraph/memgraph-platform
   ```

2. **FactSet API Credentials**
   - Create `fds-api.key` in project root:
   ```
   FDS_USERNAME="your_username"
   FDS_API_KEY="your_api_key"
   ```

### Setup

1. Clone the repository
   ```bash
   cd C:\Users\todavis\code\PAGR
   ```

2. Install dependencies
   ```bash
   uv sync
   ```

3. Configure application
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Usage

### Starting the Application

```bash
uv run streamlit run src/pagr/app.py
```

The application will open at `http://localhost:8501`

### Portfolio CSV Format

```csv
ticker,quantity,book_value,security_type,isin,cusip
AAPL-US,100,19000.00,Common Stock,US0378331005,037833100
MSFT-US,50,21000.00,Common Stock,US5949181045,594918104
TSMC-TT,200,32000.00,Common Stock,US8740391003,874039100
GE-US,150,12000.00,Common Stock,US3696041033,369604103
```

**Required columns**: `ticker`, `quantity`, `book_value`
**Optional columns**: `security_type`, `isin`, `cusip`, `market_value`, `purchase_date`

**Note**: `book_value` represents the cost basis (what the portfolio manager paid for the position). `market_value` is optional and can be populated manually or fetched separately from data providers.

### Workflow

1. **Upload CSV**: Use sidebar file uploader to select portfolio CSV
2. **ETL Processing**:
   - Portfolio data loaded and validated
   - FactSet API enriches company information
   - Geographic/regional data mapped
   - FIBO graph constructed in Memgraph
   - Query service initialized
3. **Explore Data**:
   - View portfolio metrics and position breakdown
   - Analyze sector and country exposure
   - Interactive graph visualization with relationships

## Project Structure

```
src/pagr/
├── app.py                  # Main Streamlit application
├── session_manager.py      # Streamlit session state management
├── etl_manager.py          # ETL pipeline orchestration
├── ui/
│   ├── metrics.py          # Portfolio metrics display
│   ├── tabular.py          # Tabular view with analysis
│   └── graph_view.py       # PyVis graph visualization
└── fds/                    # FactSet/FIBO integration
    ├── clients/            # API clients (FactSet, Memgraph)
    ├── loaders/            # CSV portfolio loading
    ├── enrichers/          # Data enrichment from FactSet
    ├── graph/              # Graph building and queries
    ├── models/             # FIBO data models
    ├── services/           # ETL pipeline orchestration
    └── utils/              # Logging and utilities

config/
└── config.yaml             # Application configuration

tests/
└── test_basic.py           # Unit tests for core components
```

## Configuration

### config/config.yaml

```yaml
memgraph:
  host: localhost
  port: 7687
  username: ""
  password: ""
  encrypted: false

factset:
  credentials_file: "fds-api.key"
  base_url: "https://api.factset.com"
  rate_limit_rps: 10
  timeout: 30
  max_retries: 3

fibo:
  fetch_subsidiaries: true
  fetch_executives: true
  fetch_geography: true
  fetch_supply_chain: false

logging:
  level: "INFO"
  file: "logs/pagr.log"
```

## API Integration

### FactSet Endpoints Used

1. **Company Profile**
   - Endpoint: `/content/factset-fundamentals/v2/company-reports/profile`
   - Returns: company name, sector, industry, market cap, country

2. **Entity Structure**
   - Endpoint: `/content/factset-entity/v1/entity-structures`
   - Returns: subsidiary relationships, parent companies

3. **Company Officers**
   - Endpoint: `/content/factset-people/v1/profiles`
   - Returns: executive names, titles, organizations

### Rate Limiting
- 10 requests per second
- Automatic retry with exponential backoff
- Error handling for quota exceeded scenarios

## Database Schema

### Node Types

| Type | Properties |
|------|-----------|
| Portfolio | name, created_at, total_value |
| Position | ticker, quantity, market_value, weight |
| Company | fibo_id, factset_id, name, ticker, sector, industry, country |
| Country | fibo_id, name, iso_code, region |
| Region | fibo_id, name |
| Executive | fibo_id, name, title |

### Relationship Types

| Relationship | Source | Target |
|-------------|--------|--------|
| CONTAINS | Portfolio | Position |
| ISSUED_BY | Position | Company |
| HEADQUARTERED_IN | Company | Country |
| OPERATES_IN | Company | Country |
| PART_OF | Country | Region |
| CEO_OF | Executive | Company |
| HAS_SUBSIDIARY | Company | Company |

## Testing

Run the test suite:

```bash
uv run pytest tests/ -v
```

Test categories:
- **Unit Tests**: Portfolio models, session management, statistics
- **Integration Tests**: ETL pipeline, database operations (requires Memgraph)

## Troubleshooting

### Memgraph Connection Error

```
Cannot connect to Memgraph database
```

**Solution**:
1. Verify Memgraph is running: `docker ps | grep memgraph`
2. Check connection: `telnet 127.0.0.1 7687`
3. Verify host in config/config.yaml is set to `127.0.0.1`
4. Restart if needed: `docker restart memgraph`

### FactSet API Errors

```
FactSet Quota Exceeded
```

**Solution**:
1. Check API rate limits: max 10 requests per second
2. Verify credentials in `fds-api.key`
3. Check demo account permissions

### CSV Upload Issues

```
Invalid CSV format
```

**Solution**:
1. Verify required columns: `ticker`, `quantity`, `market_value`
2. Ensure tickers use FactSet format (e.g., `AAPL-US`)
3. Check for encoding issues (UTF-8 recommended)

## Performance

- **CSV Loading**: < 1 second for 100 positions
- **FactSet Enrichment**: ~1 second per ticker (rate-limited to 10 RPS)
- **Graph Building**: < 500ms for typical portfolios
- **Query Execution**: < 200ms for standard queries

## Known Limitations

1. **Demo Account**: May have restricted FactSet API access
2. **Supply Chain Data**: Limited availability from FactSet
3. **Real-time Updates**: Batch processing only (no live updates)
4. **Portfolio Size**: Optimized for portfolios < 100 positions

## Development

### Adding New Features

1. Create new component in appropriate module
2. Add tests in `tests/`
3. Update UI component if needed
4. Document in README

### Code Style

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Keep components modular and testable

## Contributing

1. Create feature branch
2. Make changes and test
3. Submit pull request

## License

[Specify license here]

## Support

For issues or questions:
- Check troubleshooting section
- Review logs in `logs/` directory
- Check FactSet API documentation
- Review Memgraph documentation

---

**Version**: 0.1.0
**Last Updated**: December 2025
**Status**: Active Development
