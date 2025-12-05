"""Enricher for company data from FactSet API."""

import logging
from typing import Optional, Tuple

from pagr.fds.clients.factset_client import FactSetClient
from pagr.fds.models.fibo import Company, Executive

logger = logging.getLogger(__name__)


class CompanyEnricher:
    """Enriches company data from FactSet API to FIBO entities."""

    def __init__(self, factset_client: FactSetClient):
        """Initialize company enricher.

        Args:
            factset_client: FactSet API client
        """
        self.client = factset_client

    def enrich_company(self, ticker: str) -> Optional[Tuple[Company, Optional[str]]]:
        """Enrich company data from ticker.

        Args:
            ticker: Security ticker (e.g., 'AAPL-US' or 'AAPL')

        Returns:
            Tuple of (Company FIBO entity, CUSIP) or None if not found
            CUSIP may be None if not available in API response

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Enriching company data for {ticker}")

        try:
            # Step 1: Fetch company profile (which also resolves ticker to entity ID)
            profile_response = self.client.get_company_profile([ticker])

            if not profile_response.get("data") or len(profile_response["data"]) == 0:
                logger.warning(f"Could not fetch profile for ticker {ticker}")
                return None

            profile = profile_response["data"][0]
            entity_id = profile.get("fsymId")

            if not entity_id:
                logger.warning(f"No entity ID found for {ticker}")
                return None

            logger.debug(f"Resolved {ticker} to entity ID {entity_id}")

            # Extract CUSIP from profile if available
            cusip = profile.get("cusip")  # FactSet API includes CUSIP in profile response
            if cusip:
                logger.debug(f"Resolved {ticker} to CUSIP {cusip}")

            # Step 3: Create Company FIBO entity
            # Extract country from address if available
            country = None
            if profile.get("address"):
                country = profile["address"].get("country")

            company = Company(
                fibo_id=f"fibo:company:{entity_id}",
                factset_id=entity_id,
                name=profile.get("name", ""),
                ticker=ticker,
                sector=profile.get("sector"),
                industry=profile.get("industry"),
                market_cap=profile.get("marketCapitalization"),
                description=None,  # Skip description to avoid Cypher parsing issues with long text
                country=country,
            )

            logger.info(
                f"Successfully enriched {company.name} ({ticker}): "
                f"sector={company.sector}, country={company.country}"
                + (f", cusip={cusip}" if cusip else "")
            )

            return (company, cusip)

        except Exception as e:
            if "400 Client Error" in str(e):
                logger.warning(f"Invalid ticker or bad request for {ticker}: {e}")
                return None
            logger.error(f"Error enriching company for {ticker}: {e}")
            raise

    def enrich_executives(self, entity_id: str) -> list[Executive]:
        """Enrich executive data for a company.

        Args:
            entity_id: FactSet entity ID

        Returns:
            List of Executive FIBO entities

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Enriching executives for entity {entity_id}")

        try:
            response = self.client.get_company_officers([entity_id])

            if not response.get("data"):
                logger.debug(f"No officers found for {entity_id}")
                return []

            executives = []
            for officer in response["data"]:
                name = officer.get("name")
                title = officer.get("title")

                if not name:
                    continue

                # Create Executive entity
                exec_entity = Executive(
                    fibo_id=f"fibo:person:{entity_id}:{name.lower().replace(' ', '-')}",
                    name=name,
                    title=title,
                    start_date=officer.get("startDate"),
                )

                executives.append(exec_entity)
                logger.debug(f"Found executive: {name} ({title})")

            logger.info(f"Found {len(executives)} executives for {entity_id}")
            return executives

        except Exception as e:
            logger.error(f"Error enriching executives for {entity_id}: {e}")
            raise

    def get_ceo(self, entity_id: str) -> Optional[Executive]:
        """Get CEO of a company.

        Args:
            entity_id: FactSet entity ID

        Returns:
            CEO Executive entity or None if not found

        Raises:
            Exception: If API call fails
        """
        executives = self.enrich_executives(entity_id)

        for exec_entity in executives:
            if exec_entity.title and "chief executive" in exec_entity.title.lower():
                logger.debug(f"Found CEO: {exec_entity.name}")
                return exec_entity

        logger.debug(f"No CEO found for {entity_id}")
        return None
