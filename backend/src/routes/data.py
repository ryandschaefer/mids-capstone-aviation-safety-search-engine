from fastapi.routing import APIRouter
import controllers.data as controller

# Initialize Fastapi router
router = APIRouter(prefix = "/data")

# Return the first 15 records as a test set
@router.get("/test")
def get_test_data():
    return controller.get_test_data()