from fastapi import APIRouter, Depends, HTTPException

from ..log import get_logger
from ..security import verify_secret
from .model import ModelUnavailable, predict
from .schemas import PredictItemResult, PredictRequest, PredictResponse

logger = get_logger("moolabel")

router = APIRouter(
    prefix="/moolabel",
    tags=["moolabel"],
    dependencies=[Depends(verify_secret)],
)


# fungsi biasa (bukan async): scikit-learn memakai CPU, FastAPI menjalankannya di thread
@router.post("/predict", response_model=PredictResponse)
def predict_labels(req: PredictRequest):
    try:
        model_version, hasil = predict([item.note for item in req.items])
    except ModelUnavailable as e:
        # Express tetap menyimpan dan menampilkan catatan asli tanpa label
        logger.error("MooLabel tidak bisa dipakai: %s", e)
        raise HTTPException(503, "MooLabel unavailable")
    return PredictResponse(
        model_version=model_version,
        items=[
            PredictItemResult(order_item_id=item.order_item_id, labels=labels, scores=scores)
            for item, (labels, scores) in zip(req.items, hasil)
        ],
    )
