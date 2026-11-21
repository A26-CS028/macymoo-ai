from pydantic import BaseModel, ConfigDict, Field

# Kontrak KF 9.6 dan docs/openapi.yaml macymoo-fs (MooLabelPredictRequest/Response)


class PredictItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    order_item_id: int
    # catatan kosong tidak dikirim Express; kalau lolos, ditolak 422
    note: str = Field(min_length=1, max_length=500)


class PredictRequest(BaseModel):
    items: list[PredictItem] = Field(min_length=1, max_length=50)


class PredictItemResult(BaseModel):
    order_item_id: int
    labels: list[str]
    scores: dict[str, float]  # 8 label, urutan LABELS


class PredictResponse(BaseModel):
    model_version: str
    items: list[PredictItemResult]
