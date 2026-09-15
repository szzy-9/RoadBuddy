from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AskSource(BaseModel):
    """A corpus passage that supported the answer."""

    name: str
    excerpt: str


class AskResponse(BaseModel):
    answered: bool
    answer: str
    sources: list[AskSource]
    # Why a question was declined: "not_in_sources", "off_topic", or
    # "unavailable" when the model could not be reached. Also "greeting"
    # for a conversational turn, which is not a decline.
    reason: str | None = None
    # Questions to show the user. Populated for a greeting, where the
    # point is to make clear what Buddy can be asked.
    examples: list[str] = []
