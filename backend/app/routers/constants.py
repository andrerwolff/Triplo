from fastapi import APIRouter
from app.constants import CSI_DIVS

router = APIRouter()


@router.get("/constants/csi-divisions")
def get_csi_divisions():
    return {"divisions": CSI_DIVS}
