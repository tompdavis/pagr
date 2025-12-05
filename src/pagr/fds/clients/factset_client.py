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
        max_retry_delay: int = 300,
    ):
        """Initialize FactSet API client.

        Args:
            username: FactSet username (format: USERNAME-SERIAL)
            api_key: FactSet API key
            base_url: Base URL for FactSet API
            rate_limit_rps: Requests per second limit
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            max_retry_delay: Maximum seconds to wait for 429 rate limit retry (default: 300/5 minutes)

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
        self.max_retry_delay = max_retry_delay

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

                # Check if retry delay exceeds maximum allowed (prevent 10+ hour blocks)
                if retry_after > self.max_retry_delay:
                    error_msg = (
                        f"Rate limit retry delay ({retry_after}s) exceeds maximum allowed "
                        f"({self.max_retry_delay}s). API quota likely exhausted. "
                        f"Please wait and try again later, or contact FactSet support."
                    )
                    logger.error(error_msg)
                    raise FactSetClientError(error_msg)

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

    def get_last_close_prices(self, tickers: list[str]) -> dict:
        """Fetch last close prices for tickers.

        Args:
            tickers: List of tickers

        Returns:
            API response with prices
        """
        from datetime import datetime, timedelta

        # Fetch last 5 days to ensure we get a closing price
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        logger.info(f"Fetching prices for {len(tickers)} tickers from {start_date} to {end_date}")

        return self._make_request(
            "POST",
            "/content/factset-global-prices/v1/prices",
            json_data={
                "ids": tickers,
                "frequency": "D",
                "startDate": start_date,
                "endDate": end_date
            },
        )

    def get_bond_prices(self, identifiers: list[str], id_type: str = "CUSIP") -> dict:
        """Fetch bond prices using ISIN or CUSIP identifiers.

        Falls back to global prices endpoint if bond-specific endpoint fails.

        Args:
            identifiers: List of ISIN or CUSIP identifiers
            id_type: Identifier type - "ISIN" or "CUSIP" (default: CUSIP)

        Returns:
            API response with bond prices

        Raises:
            FactSetClientError: If API call fails
            ValueError: If id_type is invalid
        """
        if id_type not in ["ISIN", "CUSIP"]:
            raise ValueError(f"Invalid id_type: {id_type}. Must be 'ISIN' or 'CUSIP'")

        from datetime import datetime, timedelta

        # Fetch last 5 days to ensure we get a closing price
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        logger.info(
            f"Fetching bond prices for {len(identifiers)} {id_type} identifiers "
            f"from {start_date} to {end_date}"
        )

        # Use global prices endpoint which works for bonds with ISIN/CUSIP
        return self._make_request(
            "POST",
            "/content/factset-global-prices/v1/prices",
            json_data={
                "ids": identifiers,
                "idType": id_type,
                "frequency": "D",
                "startDate": start_date,
                "endDate": end_date
            },
        )

    def get_bond_details(self, identifier: str, id_type: str = "CUSIP") -> dict:
        """Fetch comprehensive bond details including coupon, currency, maturity, issuer.

        Uses FactSet Fixed Income reference data API and prices API.
        Falls back to graceful degradation if API calls fail.

        Args:
            identifier: Single ISIN or CUSIP identifier
            id_type: Identifier type - "ISIN" or "CUSIP" (default: CUSIP)

        Returns:
            API response with bond details (price, coupon, currency, maturity, issuer)

        Raises:
            FactSetClientError: If API call fails
            ValueError: If id_type is invalid
        """
        if id_type not in ["ISIN", "CUSIP"]:
            raise ValueError(f"Invalid id_type: {id_type}. Must be 'ISIN' or 'CUSIP'")

        logger.info(f"Fetching bond details for {id_type}:{identifier}")

        try:
            # First, try to get reference data (coupon, maturity, currency, issuer)
            reference_data = None
            try:
                ref_response = self._make_request(
                    "POST",
                    "/content/factset-fixed-income/v1/bond-details",
                    json_data={"ids": [identifier], "idType": id_type},
                )
                if ref_response.get("data") and len(ref_response["data"]) > 0:
                    reference_data = ref_response["data"][0]
                    logger.debug(f"Retrieved reference data for {id_type}:{identifier}")
            except Exception as e:
                logger.debug(f"Could not fetch reference data: {e}. Will use prices only.")

            # Second, get prices
            price_data = None
            try:
                price_response = self.get_bond_prices([identifier], id_type)
                if price_response.get("data") and len(price_response["data"]) > 0:
                    price_data = price_response["data"][0]
                    logger.debug(f"Retrieved price data for {id_type}:{identifier}")
            except Exception as e:
                logger.debug(f"Could not fetch price data: {e}. Will use reference data only.")

            # Merge data from both sources
            combined_data = {
                "id": identifier,
                "price": price_data.get("price") if price_data else None,
                "priceDate": price_data.get("priceDate") if price_data else None,
                "coupon": reference_data.get("coupon") if reference_data else None,
                "currency": reference_data.get("currency") if reference_data else None,
                "maturityDate": reference_data.get("maturityDate") if reference_data else None,
                "issuer": reference_data.get("issuer") if reference_data else None,
            }

            logger.debug(f"Combined bond details for {id_type}:{identifier}: {combined_data}")
            return {"data": [combined_data]}

        except Exception as e:
            logger.warning(f"Error fetching bond details for {id_type}:{identifier}: {e}")
            # Return partial response structure for graceful degradation
            return {
                "data": [
                    {
                        "id": identifier,
                        "price": None,
                        "priceDate": None,
                        "coupon": None,
                        "currency": None,
                        "maturityDate": None,
                        "issuer": None,
                    }
                ]
            }

    def get_bond_prices_formula_api(self, cusips: list[str]) -> dict:
        """Fetch bond prices using FactSet Formula API.

        Uses the time-series endpoint with price formulas to get bond close prices.

        Args:
            cusips: List of CUSIP identifiers

        Returns:
            Dict with format: {"data": {"037833BY5": {"price": 99.843}}}

        Raises:
            FactSetClientError: If API call fails
            ValueError: If cusips list is empty
        """
        if not cusips:
            raise ValueError("At least one CUSIP identifier is required")

        logger.info(
            f"Fetching bond prices via Formula API for {len(cusips)} CUSIP identifiers"
        )

        # Build comma-separated list of CUSIPs
        ids_param = ",".join(cusips)

        try:
            # Make GET request with query parameters
            response = self._make_request(
                "GET",
                "/formula-api/v1/time-series",
                params={
                    "ids": ids_param,
                    "formulas": "price,P_PRICE(0)",
                    "flatten": "Y",
                },
            )

            # Parse response and standardize format
            standardized = {"data": {}}

            if response.get("data"):
                for item in response["data"]:
                    request_id = item.get("requestId")
                    price = item.get("PRICE")

                    if request_id and price is not None:
                        standardized["data"][request_id] = {"price": price}
                        logger.debug(f"Got Formula API price for {request_id}: {price}")
                    elif request_id:
                        logger.debug(f"No price data for {request_id} from Formula API")

            logger.info(
                f"Formula API returned prices for {len(standardized['data'])} of {len(cusips)} CUSIPs"
            )

            return standardized

        except FactSetClientError:
            raise
        except Exception as e:
            logger.error(f"Error fetching bond prices via Formula API: {e}")
            raise FactSetClientError(f"Formula API error: {e}")

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
