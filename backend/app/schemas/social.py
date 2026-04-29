"""Social layer schemas."""

from pydantic import BaseModel


class SimilarUser(BaseModel):
    id: str
    username: str
    similarity: float
    shared_tags: list[str] = []


class FollowResponse(BaseModel):
    followed: bool
    follower_id: str
    followed_id: str


class UserListResponse(BaseModel):
    users: list[SimilarUser]
    total: int
