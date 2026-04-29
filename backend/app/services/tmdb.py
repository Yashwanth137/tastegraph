"""TMDB API client for fetching movie data."""

import httpx
from app.config import settings


class TMDBClient:
    """Async TMDB API client."""

    def __init__(self):
        self.base_url = settings.TMDB_BASE_URL
        self.api_key = settings.TMDB_API_KEY
        self.headers = {
            "Accept": "application/json",
        }

    def _params(self, **kwargs) -> dict:
        return {"api_key": self.api_key, **kwargs}

    async def get_popular_movies(self, page: int = 1) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/movie/popular",
                params=self._params(page=page, language="en-US"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_top_rated_movies(self, page: int = 1) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/movie/top_rated",
                params=self._params(page=page, language="en-US"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def search_movie(self, query: str, year: int | None = None) -> dict:
        params = self._params(query=query, language="en-US")
        if year:
            params["year"] = year
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/search/movie",
                params=params,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_genre_list(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/genre/movie/list",
                params=self._params(language="en-US"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()


tmdb_client = TMDBClient()
