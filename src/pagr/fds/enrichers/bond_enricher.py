"""Enricher for bond data from FactSet API."""

import logging
from typing import Optional

from pagr.fds.clients.factset_client import (
    FactSetClient,
    FactSetClientError,
    FactSetNotFoundError,
)
from pagr.fds.models.fibo import Bond, Company
from pagr.errors import BondEnrichmentError, FactSetAPIError

logger = logging.getLogger(__name__)


class BondEnricher:
    """Enriches bond data from FactSet API to FIBO entities."""

    def __init__(self, factset_client: FactSetClient):
        """Initialize bond enricher.

        Args:
            factset_client: FactSet API client
        """
        self.client = factset_client

    def enrich_bond(
        self, cusip: Optional[str] = None, isin: Optional[str] = None
    ) -> Optional[Bond]:
        """Enrich bond data from CUSIP or ISIN identifier.

        Prefers CUSIP over ISIN if both provided. Implements graceful degradation
        when FactSet data is unavailable.

        Args:
            cusip: CUSIP identifier (preferred)
            isin: ISIN identifier (fallback)

        Returns:
            Bond FIBO entity with available data, or minimal bond if enrichment fails

        Raises:
            BondEnrichmentError: If neither cusip nor isin provided
        """
        if not cusip and not isin:
            error = BondEnrichmentError("Must provide either CUSIP or ISIN identifier")
            error.log_error()
            raise error

        # Prefer CUSIP
        identifier = cusip or isin
        id_type = "CUSIP" if cusip else "ISIN"

        logger.info(f"Enriching bond data for {id_type}:{identifier}")

        try:
            # Fetch bond details from FactSet
            bond_details = self.get_bond_details(identifier, id_type)

            if not bond_details:
                logger.warning(f"Could not fetch details for {id_type}:{identifier}")
                # Return bond with basic data only
                return Bond(
                    fibo_id=f"fibo:bond:{identifier}",
                    isin=isin,
                    cusip=cusip,
                    security_type="Bond",
                    coupon=None,
                    currency="USD",
                    market_price=None,
                    maturity_date=None,
                )

            # Create Bond FIBO entity
            bond = Bond(
                fibo_id=f"fibo:bond:{identifier}",
                isin=isin,
                cusip=cusip,
                security_type=bond_details.get("security_type", "Bond"),
                coupon=bond_details.get("coupon"),
                currency=bond_details.get("currency", "USD"),
                market_price=bond_details.get("price"),
                maturity_date=bond_details.get("maturity_date"),
            )

            logger.info(
                f"Successfully enriched bond {id_type}:{identifier}: "
                f"coupon={bond.coupon}, currency={bond.currency}, price={bond.market_price}"
            )

            return bond

        except FactSetNotFoundError as e:
            logger.warning(
                f"Bond not found in FactSet for {id_type}:{identifier}. "
                f"Creating bond with basic data."
            )
            # Return bond with N/A values for graceful degradation
            return Bond(
                fibo_id=f"fibo:bond:{identifier}",
                isin=isin,
                cusip=cusip,
                security_type="Bond",
                coupon=None,
                currency="USD",
                market_price=None,
                maturity_date=None,
            )
        except FactSetClientError as e:
            error = FactSetAPIError(
                f"FactSet API error enriching bond {id_type}:{identifier}: {str(e)[:100]}"
            )
            error.log_error()
            logger.warning(f"Using graceful degradation for {id_type}:{identifier}")
            # Return bond with basic data for graceful degradation
            return Bond(
                fibo_id=f"fibo:bond:{identifier}",
                isin=isin,
                cusip=cusip,
                security_type="Bond",
                coupon=None,
                currency="USD",
                market_price=None,
                maturity_date=None,
            )
        except Exception as e:
            error = BondEnrichmentError(f"Unexpected error: {str(e)[:100]}", identifier=identifier, id_type=id_type)
            error.log_error()
            raise

    def get_bond_details(self, identifier: str, id_type: str = "CUSIP") -> dict:
        """Fetch bond details from FactSet API.

        Args:
            identifier: CUSIP or ISIN identifier
            id_type: Identifier type - "CUSIP" or "ISIN" (default: CUSIP)

        Returns:
            Dictionary with bond details:
                - price: Clean price (last close)
                - coupon: Annual coupon rate (%)
                - currency: Bond currency
                - maturity_date: Maturity date (ISO format)
                - issuer: Issuer name
                - security_type: Bond type

        Raises:
            ValueError: If id_type is invalid
            FactSetClientError: If API call fails
        """
        if id_type not in ["CUSIP", "ISIN"]:
            raise ValueError(f"Invalid id_type: {id_type}. Must be 'CUSIP' or 'ISIN'")

        logger.debug(f"Fetching bond details for {id_type}:{identifier}")

        try:
            # Fetch bond prices
            price_response = self.client.get_bond_prices([identifier], id_type)

            if not price_response.get("data") or len(price_response["data"]) == 0:
                logger.warning(f"No price data found for {id_type}:{identifier}")
                return {}

            bond_data = price_response["data"][0]

            # Extract relevant fields
            details = {
                "price": bond_data.get("price"),
                "coupon": bond_data.get("coupon"),
                "currency": bond_data.get("currency", "USD"),
                "maturity_date": bond_data.get("maturityDate"),
                "issuer": bond_data.get("issuer"),
                "security_type": "Bond",
            }

            logger.debug(f"Retrieved bond details for {id_type}:{identifier}: {details}")

            return details

        except (FactSetClientError, FactSetNotFoundError) as e:
            logger.warning(f"API error fetching bond details for {id_type}:{identifier}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching bond details for {id_type}:{identifier}: {e}")
            raise

    def resolve_issuer(
        self, cusip: Optional[str] = None, isin: Optional[str] = None
    ) -> Optional[Company]:
        """Resolve bond issuer to Company FIBO entity.

        Prefers CUSIP over ISIN if both provided.

        Args:
            cusip: CUSIP identifier (preferred)
            isin: ISIN identifier (fallback)

        Returns:
            Company FIBO entity or None if issuer not found

        Raises:
            ValueError: If neither cusip nor isin provided
        """
        if not cusip and not isin:
            raise ValueError("Must provide either CUSIP or ISIN identifier")

        # Prefer CUSIP
        identifier = cusip or isin
        id_type = "CUSIP" if cusip else "ISIN"

        logger.info(f"Resolving issuer for bond {id_type}:{identifier}")

        try:
            # Fetch bond details to get issuer information
            bond_details = self.get_bond_details(identifier, id_type)

            issuer_name = bond_details.get("issuer")

            if not issuer_name:
                logger.warning(f"No issuer found for {id_type}:{identifier}")
                return None

            # Create placeholder Company entity
            # In a production system, you would look up the issuer separately
            company = Company(
                fibo_id=f"fibo:company:{issuer_name.lower().replace(' ', '-')}",
                factset_id=None,
                name=issuer_name,
                ticker=None,  # Not available from bond data
                sector=None,
                industry=None,
                market_cap=None,
                country=None,
            )

            logger.info(f"Resolved issuer for {id_type}:{identifier} to {issuer_name}")

            return company

        except (FactSetClientError, FactSetNotFoundError) as e:
            logger.warning(f"Could not resolve issuer for {id_type}:{identifier}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error resolving issuer for {id_type}:{identifier}: {e}")
            raise

    def get_bond_price(
        self, cusip: Optional[str] = None, isin: Optional[str] = None
    ) -> Optional[float]:
        """Get latest market price for a bond.

        Prefers CUSIP over ISIN if both provided.

        Args:
            cusip: CUSIP identifier (preferred)
            isin: ISIN identifier (fallback)

        Returns:
            Market price (clean price) or None if not available

        Raises:
            ValueError: If neither cusip nor isin provided
        """
        if not cusip and not isin:
            raise ValueError("Must provide either CUSIP or ISIN identifier")

        # Prefer CUSIP
        identifier = cusip or isin
        id_type = "CUSIP" if cusip else "ISIN"

        logger.debug(f"Fetching price for bond {id_type}:{identifier}")

        try:
            bond_details = self.get_bond_details(identifier, id_type)
            price = bond_details.get("price")

            if price is not None:
                logger.debug(f"Retrieved price for {id_type}:{identifier}: ${price}")
            else:
                logger.warning(f"No price available for {id_type}:{identifier}")

            return price

        except Exception as e:
            logger.warning(f"Error fetching price for {id_type}:{identifier}: {e}")
            return None
