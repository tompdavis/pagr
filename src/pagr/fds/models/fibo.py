"""FIBO (Financial Industry Business Ontology) entity models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RelationshipType(str, Enum):
    """Relationship type enumeration."""

    HAS_SUBSIDIARY = "HAS_SUBSIDIARY"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    PARENT_OF = "PARENT_OF"
    OPERATES_IN = "OPERATES_IN"
    SUPPLIES_TO = "SUPPLIES_TO"
    CUSTOMER_OF = "CUSTOMER_OF"


class Company(BaseModel):
    """Company entity (FIBO Organization)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:company:000C7F-E",
                "factset_id": "000C7F-E",
                "name": "Apple Inc.",
                "ticker": "AAPL-US",
                "sector": "Information Technology",
                "industry": "Consumer Electronics",
                "market_cap": 3000000000000,
                "country": "United States",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    factset_id: Optional[str] = Field(default=None, description="FactSet entity ID")
    name: str = Field(..., description="Legal company name")
    ticker: Optional[str] = Field(default=None, description="Primary ticker")
    sector: Optional[str] = Field(default=None, description="GICS sector")
    industry: Optional[str] = Field(default=None, description="GICS industry")
    market_cap: Optional[float] = Field(default=None, description="Market cap in USD")
    description: Optional[str] = Field(default=None, description="Business description")
    country: Optional[str] = Field(default=None, description="Headquarters country")


class Country(BaseModel):
    """Country entity (FIBO Geographic location)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:country:US",
                "name": "United States",
                "iso_code": "US",
                "region": "North America",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    name: str = Field(..., description="Country name")
    iso_code: str = Field(..., description="ISO 3166-1 alpha-2 code")
    region: Optional[str] = Field(default=None, description="Geographic region")


class Region(BaseModel):
    """Geographic region entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:region:apac",
                "name": "Asia-Pacific",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    name: str = Field(..., description="Region name")
    description: Optional[str] = Field(default=None, description="Region description")


class Security(BaseModel):
    """Security entity (Stock, Bond, Derivative)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:security:US0378331005",
                "ticker": "AAPL-US",
                "security_type": "Common Stock",
                "isin": "US0378331005",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    ticker: str = Field(..., description="Security ticker")
    security_type: str = Field(..., description="Type: Stock, Bond, Derivative, etc.")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    cusip: Optional[str] = Field(default=None, description="CUSIP identifier")
    sedol: Optional[str] = Field(default=None, description="SEDOL identifier")


class Stock(BaseModel):
    """Stock security entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:stock:US0378331005",
                "ticker": "AAPL-US",
                "security_type": "Common Stock",
                "isin": "US0378331005",
                "cusip": "037833100",
                "sedol": "2046251",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    ticker: str = Field(..., description="Stock ticker")
    security_type: Optional[str] = Field(default="Stock", description="Security type")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    cusip: Optional[str] = Field(default=None, description="CUSIP identifier")
    sedol: Optional[str] = Field(default=None, description="SEDOL identifier")


class Bond(BaseModel):
    """Bond security entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:bond:US3696041033",
                "ticker": "GE-BOND",
                "isin": "US3696041033",
                "cusip": "369604103",
                "security_type": "Corporate Bond",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    ticker: str = Field(..., description="Bond ticker")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")
    cusip: Optional[str] = Field(default=None, description="CUSIP identifier")
    security_type: Optional[str] = Field(default="Bond", description="Bond type")


class Derivative(BaseModel):
    """Derivative security entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:derivative:aapl-call-2024",
                "ticker": "AAPL-CALL",
                "isin": None,
                "security_type": "Call Option",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    ticker: str = Field(..., description="Derivative ticker")
    security_type: Optional[str] = Field(default="Derivative", description="Derivative type")
    isin: Optional[str] = Field(default=None, description="ISIN identifier")


class Executive(BaseModel):
    """Executive/Person entity."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fibo_id": "fibo:person:tim-cook",
                "name": "Tim Cook",
                "title": "Chief Executive Officer",
                "start_date": "2011-08-24",
            }
        }
    )

    fibo_id: str = Field(..., description="Unique FIBO identifier")
    name: str = Field(..., description="Full name")
    title: Optional[str] = Field(default=None, description="Job title")
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")


class Relationship(BaseModel):
    """Generic relationship between entities."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rel_type": "HAS_SUBSIDIARY",
                "source_fibo_id": "fibo:company:parent",
                "target_fibo_id": "fibo:company:subsidiary",
                "source_type": "company",
                "target_type": "company",
                "properties": {"ownership_percentage": 100.0},
            }
        }
    )

    rel_type: str = Field(..., description="Relationship type")
    source_fibo_id: str = Field(..., description="Source entity FIBO ID")
    target_fibo_id: str = Field(..., description="Target entity FIBO ID")
    source_type: str = Field(..., description="Source entity type (company, country, etc.)")
    target_type: str = Field(..., description="Target entity type")
    properties: Optional[dict] = Field(default=None, description="Relationship properties")


class HeadquarteredInRelationship(Relationship):
    """Company headquartered in a country."""

    pass


class OperatesInRelationship(Relationship):
    """Company operates in a country."""

    properties: Optional[dict] = Field(
        default=None,
        description="Optional: revenue_percentage, etc.",
    )


class HasSubsidiaryRelationship(Relationship):
    """Parent company has subsidiary."""

    properties: Optional[dict] = Field(
        default=None,
        description="Ownership percentage, acquisition date, etc.",
    )


class SuppliesRelationship(Relationship):
    """Company supplies to another company."""

    properties: Optional[dict] = Field(
        default=None,
        description="Revenue percentage, estimated value, confidence level, etc.",
    )


class CEOOfRelationship(Relationship):
    """Executive is CEO of company."""

    pass


class IssuedByRelationship(Relationship):
    """Security issued by company."""

    pass
