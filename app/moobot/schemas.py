from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    # menu + harga + aturan dari database, dikirim oleh Express
    context: str = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
