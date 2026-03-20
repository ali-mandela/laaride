from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# Custom type to handle MongoDB ObjectId as a string in Pydantic v2
# BeforeValidator(str) ensures that bson.ObjectId is converted to str before validation
PyObjectId = Annotated[str, BeforeValidator(str)]


class MongoBaseDocument(BaseModel):
    """Base document model for all MongoDB collections."""

    id: Optional[PyObjectId] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
