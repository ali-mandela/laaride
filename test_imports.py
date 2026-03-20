"""Quick import verification for models layer."""

try:
    from app.enums import (
        UserRole, BookingStatus, BookingType,
        DriverStatus, AvailabilityStatus, VehicleType,
    )
    print("✓ Enums OK")

    from app.models import (
        MongoBaseDocument, PyObjectId,
        UserDocument, DriverDocument, VehicleDocument,
        RouteDocument, BookingDocument,
    )
    print("✓ Models OK")

    from app.schemas import (
        UserCreate, UserUpdate, UserResponse,
        DriverCreate, DriverUpdate, DriverResponse,
        VehicleCreate, VehicleUpdate, VehicleResponse,
        RouteCreate, RouteUpdate, RouteResponse,
        BookingCreate, BookingUpdate, BookingResponse,
    )
    print("✓ Schemas OK")

    # Quick instantiation test
    user = UserCreate(phone="+919876543210", name="Test User")
    print(f"✓ UserCreate instance: {user.model_dump()}")

    doc = UserDocument(phone="+919876543210", name="Test User")
    print(f"✓ UserDocument instance: {doc.model_dump()}")

    print("\n🎉 All imports and instantiations successful!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
