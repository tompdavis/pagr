"""Enricher for relationship data from FactSet API."""

import logging
from typing import Optional

from pagr.fds.clients.factset_client import FactSetClient
from pagr.fds.models.fibo import Country, Relationship

logger = logging.getLogger(__name__)


# Country mapping from company data to ISO codes
COUNTRY_MAPPING = {
    "United States": {"iso_code": "US", "region": "North America"},
    "Taiwan": {"iso_code": "TW", "region": "Asia-Pacific"},
    "Japan": {"iso_code": "JP", "region": "Asia-Pacific"},
    "China": {"iso_code": "CN", "region": "Asia-Pacific"},
    "South Korea": {"iso_code": "KR", "region": "Asia-Pacific"},
    "Hong Kong": {"iso_code": "HK", "region": "Asia-Pacific"},
    "Singapore": {"iso_code": "SG", "region": "Asia-Pacific"},
    "India": {"iso_code": "IN", "region": "Asia-Pacific"},
    "Australia": {"iso_code": "AU", "region": "Asia-Pacific"},
    "Canada": {"iso_code": "CA", "region": "North America"},
    "Mexico": {"iso_code": "MX", "region": "North America"},
    "Brazil": {"iso_code": "BR", "region": "South America"},
    "United Kingdom": {"iso_code": "GB", "region": "Europe"},
    "Germany": {"iso_code": "DE", "region": "Europe"},
    "France": {"iso_code": "FR", "region": "Europe"},
    "Netherlands": {"iso_code": "NL", "region": "Europe"},
    "Switzerland": {"iso_code": "CH", "region": "Europe"},
    "Sweden": {"iso_code": "SE", "region": "Europe"},
    "Norway": {"iso_code": "NO", "region": "Europe"},
    "Denmark": {"iso_code": "DK", "region": "Europe"},
    "Israel": {"iso_code": "IL", "region": "Middle East"},
    "UAE": {"iso_code": "AE", "region": "Middle East"},
    "Saudi Arabia": {"iso_code": "SA", "region": "Middle East"},
}


class RelationshipEnricher:
    """Enriches relationship data from FactSet API to FIBO relationships."""

    def __init__(self, factset_client: FactSetClient):
        """Initialize relationship enricher.

        Args:
            factset_client: FactSet API client
        """
        self.client = factset_client

    def enrich_geography(self, entity_id: str, country_name: Optional[str] = None) -> list[Relationship]:
        """Enrich geographic relationships for a company.

        Args:
            entity_id: FactSet entity ID
            country_name: Optional company headquarters country name

        Returns:
            List of geographic relationships

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Enriching geography for entity {entity_id}")

        relationships = []

        if not country_name:
            logger.debug(f"No country information provided for {entity_id}")
            return relationships

        try:
            # Create country entity
            country_info = self._get_country_info(country_name)

            if not country_info:
                logger.warning(f"Unknown country: {country_name}")
                return relationships

            country = Country(
                fibo_id=f"fibo:country:{country_info['iso_code']}",
                name=country_name,
                iso_code=country_info["iso_code"],
                region=country_info.get("region"),
            )

            # Create HEADQUARTERED_IN relationship
            hq_rel = Relationship(
                rel_type="HEADQUARTERED_IN",
                source_fibo_id=f"fibo:company:{entity_id}",
                target_fibo_id=country.fibo_id,
                source_type="company",
                target_type="country",
                properties={},
            )

            relationships.append(hq_rel)
            logger.debug(
                f"Created HEADQUARTERED_IN relationship: {entity_id} -> {country.iso_code}"
            )

            # Could also add OPERATES_IN for revenue-sharing countries
            # For now, we'll just use HEADQUARTERED_IN

            return relationships

        except Exception as e:
            logger.error(f"Error enriching geography for {entity_id}: {e}")
            raise

    def enrich_subsidiaries(self, entity_id: str) -> list[Relationship]:
        """Enrich subsidiary relationships for a company.

        Args:
            entity_id: FactSet entity ID

        Returns:
            List of subsidiary relationships

        Raises:
            Exception: If API call fails
        """
        logger.info(f"Enriching subsidiaries for entity {entity_id}")

        relationships = []

        try:
            response = self.client.get_entity_structure([entity_id])

            if not response.get("data"):
                logger.debug(f"No entity structure found for {entity_id}")
                return relationships

            for item in response["data"]:
                parent_id = item.get("parentId")
                child_id = item.get("entityId")

                if not parent_id or not child_id:
                    continue

                # Determine relationship direction
                if parent_id == entity_id:
                    # This company is the parent
                    rel_type = "HAS_SUBSIDIARY"
                    from_id = f"fibo:company:{parent_id}"
                    to_id = f"fibo:company:{child_id}"
                elif child_id == entity_id:
                    # This company is the child
                    rel_type = "SUBSIDIARY_OF"
                    from_id = f"fibo:company:{child_id}"
                    to_id = f"fibo:company:{parent_id}"
                else:
                    # Neither parent nor child is our entity, skip
                    continue

                ownership_pct = item.get("ownershipPercentage")

                rel = Relationship(
                    rel_type=rel_type,
                    source_fibo_id=from_id,
                    target_fibo_id=to_id,
                    source_type="company",
                    target_type="company",
                    properties={
                        "ownership_percentage": ownership_pct,
                        "parent_name": item.get("parentName"),
                        "entity_name": item.get("entityName"),
                    },
                )

                relationships.append(rel)
                logger.debug(
                    f"Created {rel_type} relationship: {from_id} -> {to_id} "
                    f"({ownership_pct}%)"
                )

            logger.info(f"Found {len(relationships)} subsidiary relationships for {entity_id}")
            return relationships

        except Exception as e:
            logger.error(f"Error enriching subsidiaries for {entity_id}: {e}")
            raise

    @staticmethod
    def _get_country_info(country_name: str) -> Optional[dict]:
        """Get country information from mapping.

        Args:
            country_name: Country name

        Returns:
            Country info dict with iso_code and region, or None if not found
        """
        return COUNTRY_MAPPING.get(country_name)
