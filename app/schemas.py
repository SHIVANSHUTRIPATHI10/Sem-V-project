from pydantic import BaseModel

class TransactionRequest(BaseModel):
    transaction_id: str
    amount: float
    oldbalanceOrg: float
    oldbalanceDest: float
    type: str
    step: int
    nameDest: str