from fastapi.testclient import TestClient
from src.main import app
import pytest
import sys

client = TestClient(app)


def test_hello_world():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}


def test_product_mix():
    # Test the product mix calculation endpoint

    # Define a sample payload for the POST request
    payload = {
        "products": [
            {
                "name": "desk",
                "wood_units_needed": 3,
                "labor_time": 1,
                "machine_time": 50,
                "selling_price": 700,
            },
            {
                "name": "table",
                "wood_units_needed": 5,
                "labor_time": 2,
                "machine_time": 20,
                "selling_price": 900,
            },
        ],
        "capacity": {
            "workers": 200,
            "num_machines": 50,
            "single_machine_runtime": 16,
            "supply_of_woods": 3600,
        },
    }

    response = client.post(
        "/product-mix/calculate", json=payload
    )  # Add appropriate payload here")
    assert response.status_code == 200
    assert {"desk": 883, "table": 190} == response.json()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
