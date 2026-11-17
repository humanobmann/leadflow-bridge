"""Lead schema used by both importer and the local CRM API."""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Lead(BaseModel):
    """Minimal demonstration lead; intentionally does not collect phone numbers."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    external_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    company: str = Field(default="", max_length=120)
    source: str = Field(default="", max_length=80)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        # A demonstration-level email syntax check, not mailbox verification.
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("invalid email format")
        return value
