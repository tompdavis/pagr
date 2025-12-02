"""FactSet API response models."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class IdentifierResolutionResult(BaseModel):
    """FactSet identifier resolution result."""

    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId", description="Requested identifier")
    fsym_id: Optional[str] = Field(alias="fsymId", default=None, description="FactSet symbol ID")
    fsym_security_id: Optional[str] = Field(
        alias="fsymSecurityId", default=None, description="FactSet security ID"
    )


class CompanyProfile(BaseModel):
    """FactSet company profile."""

    model_config = ConfigDict(populate_by_name=True)

    fsym_id: Optional[str] = Field(alias="fsymId", default=None, description="FactSet ID")
    company_name: Optional[str] = Field(
        alias="companyName", default=None, description="Company name"
    )
    primary_exchange: Optional[str] = Field(
        alias="primaryExchange", default=None, description="Primary exchange"
    )
    sector: Optional[str] = Field(default=None, description="GICS sector")
    industry: Optional[str] = Field(default=None, description="GICS industry")
    market_cap: Optional[float] = Field(alias="marketCap", default=None, description="Market cap")
    business_description: Optional[str] = Field(
        alias="businessDescription", default=None, description="Business description"
    )
    headquarters_country: Optional[str] = Field(
        alias="headquartersCountry", default=None, description="HQ country"
    )
    headquarters_city: Optional[str] = Field(
        alias="headquartersCity", default=None, description="HQ city"
    )


class EntityStructureItem(BaseModel):
    """Entity structure relationship (parent/subsidiary)."""

    model_config = ConfigDict(populate_by_name=True)

    entity_id: Optional[str] = Field(alias="entityId", default=None, description="Entity ID")
    parent_id: Optional[str] = Field(alias="parentId", default=None, description="Parent entity ID")
    entity_name: Optional[str] = Field(
        alias="entityName", default=None, description="Entity name"
    )
    parent_name: Optional[str] = Field(
        alias="parentName", default=None, description="Parent name"
    )
    ownership_percentage: Optional[float] = Field(
        alias="ownershipPercentage", default=None, description="Ownership %"
    )


class Officer(BaseModel):
    """Company officer (executive)."""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default=None, description="Officer name")
    title: Optional[str] = Field(default=None, description="Officer title")
    start_date: Optional[str] = Field(
        alias="startDate", default=None, description="Start date (YYYY-MM-DD)"
    )


class FactSetResponse(BaseModel):
    """Generic FactSet API response."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields in response

    data: Optional[list[Any]] = Field(default=None, description="Response data")
    errors: Optional[list[dict]] = Field(default=None, description="Error messages")


class IdentifierResolutionResponse(FactSetResponse):
    """Identifier resolution response."""

    data: Optional[list[IdentifierResolutionResult]] = Field(
        default=None, description="Resolution results"
    )


class CompanyProfileResponse(FactSetResponse):
    """Company profile response."""

    data: Optional[list[CompanyProfile]] = Field(default=None, description="Company profiles")


class EntityStructureResponse(FactSetResponse):
    """Entity structure response."""

    data: Optional[list[EntityStructureItem]] = Field(
        default=None, description="Structure items"
    )


class OfficersResponse(FactSetResponse):
    """Officers response."""

    data: Optional[list[Officer]] = Field(default=None, description="Officers list")
