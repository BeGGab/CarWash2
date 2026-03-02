from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_public_config():
    """Публичная конфигурация для клиента: город по умолчанию (задаёт системный администратор)."""
    default_city = None
    if (
        settings.default_city_name is not None
        and settings.default_city_lat is not None
        and settings.default_city_lon is not None
    ):
        default_city = {
            "name": settings.default_city_name,
            "lat": settings.default_city_lat,
            "lon": settings.default_city_lon,
        }
    return {
        "defaultCity": default_city,
        "defaultRadiusKm": settings.default_radius_km,
    }
