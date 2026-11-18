from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=500)
    # menu + harga + aturan dari database, dikirim oleh Express
    # batas supaya permintaan raksasa tidak menghabiskan token Gemini
    context: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str
