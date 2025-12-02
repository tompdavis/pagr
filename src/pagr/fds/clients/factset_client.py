"""FactSet API client with rate limiting and retry logic."""

import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class FactSetClientError(Exception):
    """Base exception for FactSet client errors."""

    pass


class FactSetAuthenticationError(FactSetClientError):
    """Raised when authentication fails."""

    pass


class FactSetPermissionError(FactSetClientError):
    """Raised when access is denied."""

    pass


class FactSetNotFoundError(FactSetClientError):
    """Raised when resource not found."""

    pass


class FactSetClient:
    """FactSet API client with rate limiting and retry logic.

    Rate limited to 10 requests per second per FactSet API documentation.
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        base_url: str = "https://api.factset.com",
        rate_limit_rps: int = 10,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize FactSet API client.

        Args:
            username: FactSet username (format: USERNAME-SERIAL)
            api_key: FactSet API key
            base_url: Base URL for FactSet API
            rate_limit_rps: Requests per second limit
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts

        Raises:
            ValueError: If credentials are invalid
        """
        if not username or not api_key:
            raise ValueError("Username and API key are required")

        self.username = username
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Rate limiting: delay between requests
        self.rate_limit_delay = 1.0 / rate_limit_rps

        # Create session with auth
        self.session = requests.Session()
        self.session.auth = (username, api_key)

        logger.info(f"Initialized FactSet client for {username}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ),
    )
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        **kwargs: Any,
    ) -> dict:
        """Make HTTP request to FactSet API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            json_data: JSON request body (for POST requests)
            **kwargs: Additional arguments to pass to requests

        Returns:
            Parsed JSON response

        Raises:
            FactSetAuthenticationError: If authentication fails (401)
            FactSetPermissionError: If access denied (403)
            FactSetNotFoundError: If resource not found (404)
            FactSetClientError: For other errors
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "POST":
                response = self.session.post(
                    url, json=json_data, timeout=self.timeout, **kwargs
                )
            else:
                response = self.session.get(url, timeout=self.timeout, **kwargs)

            # Check for rate limit
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                logger.warning(
                    f"Rate limited. Waiting {retry_after} seconds before retry..."
                )
                time.sleep(retry_after)
                # Retry the request
                return self._make_request(method, endpoint, json_data, **kwargs)

            # Check for authentication errors
            if response.status_code == 401:
                logger.error("Authentication failed - invalid credentials")
                raise FactSetAuthenticationError(
                    "Invalid credentials. Check FDS_USERNAME and FDS_API_KEY."
                )

            # Check for permission errors
            if response.status_code == 403:
                logger.error(f"Access denied to {endpoint}")
                raise FactSetPermissionError(
                    f"No access to {endpoint}. Check your API subscription."
                )

            # Check for not found
            if response.status_code == 404:
                logger.error(f"Endpoint not found: {endpoint}")
                raise FactSetNotFoundError(f"Endpoint not found: {endpoint}")

            # Check for server errors
            if response.status_code >= 500:
                logger.error(f"Server error: {response.status_code}")
                raise FactSetClientError(f"Server error: {response.status_code}")

            # Check for other errors
            response.raise_for_status()

            # Apply rate limiting
            time.sleep(self.rate_limit_delay)

            # Parse response
            return response.json()

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout for {endpoint}")
            raise FactSetClientError(f"Request timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {endpoint}")
            raise FactSetClientError(f"Connection error: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise FactSetClientError(f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise FactSetClientError(f"Request error: {e}")

    def resolve_identifiers(self, tickers: list[str]) -> dict:
        """Resolve security tickers to company profiles with entity IDs.

        Note: The old /symbology/v3/identifier-resolution endpoint is deprecated.
        We use the company profile endpoint directly with tickers, which returns fsymId.

        Args:
            tickers: List of tickers (e.g., ['AAPL-US', 'MSFT-US'])

        Returns:
            API response with company profiles including fsymId (entity ID)

        Raises:
            FactSetClientError: If API call fails
        """
        logger.info(f"Resolving identifiers for {len(tickers)} tickers")
        # Use company profile endpoint which accepts tickers directly and returns fsymId
        return self.get_company_profile(tickers)

    def get_company_profile(self, entity_ids: list[str]) -> dict:
        """Fetch company profile data.

        Args:
            entity_ids: List of FactSet entity IDs or tickers (e.g., ['AAPL-US', 'MSFT-US'])

        Returns:
            API response with company profiles

        Raises:
            FactSetClientError: If API call fails
        """
        logger.info(f"Fetching company profiles for {len(entity_ids)} entities")
        # Use GET with query parameters instead of POST
        ids_param = ",".join(entity_ids)
        endpoint = f"/content/factset-fundamentals/v2/company-reports/profile?ids={ids_param}"
        return self._make_request("GET", endpoint)

    def get_entity_structure(self, entity_ids: list[str]) -> dict:
        """Fetch entity structure (parent/subsidiary relationships).

        Args:
            entity_ids: List of FactSet entity IDs

        Returns:
            API response with entity structure

        Raises:
            FactSetClientError: If API call fails
        """
        logger.info(f"Fetching entity structures for {len(entity_ids)} entities")
        return self._make_request(
            "POST",
            "/content/factset-entity/v1/entity-structures",
            json_data={"ids": entity_ids},
        )

    def get_company_officers(self, entity_ids: list[str]) -> dict:
        """Fetch company officers (executives).

        Args:
            entity_ids: List of FactSet entity IDs or tickers

        Returns:
            API response with officers

        Raises:
            FactSetClientError: If API call fails
        """
        logger.info(f"Fetching officers for {len(entity_ids)} entities")
        # Use the profiles endpoint which includes officer/executive information
        return self._make_request(
            "POST",
            "/content/factset-people/v1/profiles",
            json_data={"ids": entity_ids},
        )

    @staticmethod
    def from_credentials_file(
        credentials_file: str = "fds-api.key",
        **kwargs: Any,
    ) -> "FactSet Client":
        """Create FactSet client from credentials file.

        File format:
            FDS_USERNAME="username-serial"
            FDS_API_KEY="api-key"

        Args:
            credentials_file: Path to credentials file
            **kwargs: Additional arguments to pass to __init__

        Returns:
            FactSetClient instance

        Raises:
            FileNotFoundError: If credentials file not found
            ValueError: If credentials file is invalid
        """
        creds_path = Path(credentials_file)

        if not creds_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_file}")

        credentials = {}
        with open(creds_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    value = value.strip('"').strip("'")
                    credentials[key.strip()] = value

        username = credentials.get("FDS_USERNAME")
        api_key = credentials.get("FDS_API_KEY")

        if not username or not api_key:
            raise ValueError(
                "Credentials file must contain FDS_USERNAME and FDS_API_KEY"
            )

        logger.info(f"Loaded credentials from {credentials_file}")
        return FactSetClient(username, api_key, **kwargs)
