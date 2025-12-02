"""Configuration loader for the application."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class MemgraphConfig(BaseModel):
    """Memgraph database configuration."""

    host: str = Field(default="localhost", description="Memgraph host")
    port: int = Field(default=7687, description="Memgraph port")
    username: str = Field(default="", description="Memgraph username")
    password: str = Field(default="", description="Memgraph password")
    encrypted: bool = Field(default=False, description="Use encrypted connection")


class FactSetConfig(BaseModel):
    """FactSet API configuration."""

    credentials_file: str = Field(default="fds-api.key", description="Path to credentials file")
    base_url: str = Field(
        default="https://api.factset.com", description="FactSet API base URL"
    )
    rate_limit_rps: int = Field(default=10, description="Requests per second limit")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    cache_enabled: bool = Field(default=False, description="Enable API response caching")
    cache_dir: str = Field(default="data/cache", description="Cache directory")


class PortfolioConfig(BaseModel):
    """Portfolio configuration."""

    default_file: str = Field(default="data/sample_portfolio.csv", description="Default portfolio file")
    supported_formats: list[str] = Field(
        default=["csv", "xlsx"], description="Supported file formats"
    )


class FIBOConfig(BaseModel):
    """FIBO ontology configuration."""

    fetch_subsidiaries: bool = Field(default=True, description="Fetch subsidiary relationships")
    fetch_supply_chain: bool = Field(
        default=False, description="Fetch supply chain relationships"
    )
    fetch_executives: bool = Field(default=True, description="Fetch executive data")
    fetch_geography: bool = Field(default=True, description="Fetch geographic data")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="logs/pipeline.log", description="Log file path")
    console_level: str = Field(default="INFO", description="Console log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    memgraph: MemgraphConfig = Field(default_factory=MemgraphConfig)
    factset: FactSetConfig = Field(default_factory=FactSetConfig)
    portfolio: PortfolioConfig = Field(default_factory=PortfolioConfig)
    fibo: FIBOConfig = Field(default_factory=FIBOConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    """Load application configuration from YAML file with environment variable overrides.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        AppConfig object with all configuration values

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If configuration file is invalid YAML
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file) as f:
        config_dict = yaml.safe_load(f) or {}

    # Override with environment variables if present
    if env_mg_host := os.getenv("MEMGRAPH_HOST"):
        if "memgraph" not in config_dict:
            config_dict["memgraph"] = {}
        config_dict["memgraph"]["host"] = env_mg_host

    if env_mg_port := os.getenv("MEMGRAPH_PORT"):
        if "memgraph" not in config_dict:
            config_dict["memgraph"] = {}
        config_dict["memgraph"]["port"] = int(env_mg_port)

    if env_fs_creds := os.getenv("FACTSET_CREDENTIALS_FILE"):
        if "factset" not in config_dict:
            config_dict["factset"] = {}
        config_dict["factset"]["credentials_file"] = env_fs_creds

    return AppConfig(**config_dict)


def get_config() -> AppConfig:
    """Get or create global configuration instance.

    Returns:
        AppConfig object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
    """
    return load_config()
