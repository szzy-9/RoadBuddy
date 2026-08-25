import asyncio
import json

import httpx

from app.config import Settings
from app.services.geocoding import Coordinates
from app.services.routing import calculate_route


def test_calculate_route_uses_heigit_directions_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.heigit.org"
        assert request.url.path == "/openrouteservice/v2/directions/driving-car/geojson"
        assert request.headers["Authorization"] == "test-only"
        assert json.loads(request.content) == {
            "coordinates": [[144.657, -37.8233], [144.9465, -37.815]],
            "instructions": False,
        }
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "properties": {
                            "summary": {"distance": 41_200, "duration": 2_040}
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [
                                [144.657, -37.8233],
                                [144.9465, -37.815],
                            ],
                        },
                    }
                ]
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await calculate_route(
                Coordinates(144.657, -37.8233, "Tarneit VIC 3029, Australia"),
                Coordinates(144.9465, -37.815, "Docklands VIC 3008, Australia"),
                Settings(ors_api_key="test-only", use_mock_data=False),
                client,
            )

    result = asyncio.run(run())

    assert result.distance_km == 41.2
    assert result.duration_minutes == 34
    assert result.geometry["type"] == "LineString"
