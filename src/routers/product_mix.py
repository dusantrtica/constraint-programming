from fastapi import APIRouter
from typing import List, Dict

from src.algorithms.simple_lp_product_mix import (parametrized_product_mix, Product, Capacity)

product_mix_router = APIRouter()

@product_mix_router.post("/calculate")
async def calculate_product_mix(products: List[Product], capacity: Capacity) -> Dict[str, int]:
    return parametrized_product_mix(products, capacity)
