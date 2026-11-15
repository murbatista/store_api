from typing import List
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import ProductIn, ProductOut, ProductUpdate, ProductUpdateOut
from store.core.exceptions import CreateException, NotFoundException


class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def create(self, body: ProductIn) -> ProductOut:
        product_model = ProductModel(**body.model_dump())
        try:
            await self.collection.insert_one(product_model.model_dump())
        except Exception as exc:
            raise CreateException(
                message="Não foi possível cadastrar o produto."
            ) from exc

        return ProductOut(**product_model.model_dump())

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductOut(**result)

    async def query(
        self,
        price_gt: Decimal | None = None,
        price_lt: Decimal | None = None,
    ) -> List[ProductOut]:
        filters = {}
        if price_gt is not None or price_lt is not None:
            price_filter = {}
            if price_gt is not None:
                price_filter["$gt"] = Decimal128(str(price_gt))
            if price_lt is not None:
                price_filter["$lt"] = Decimal128(str(price_lt))
            filters["price"] = price_filter

        return [
            ProductOut(**item)
            async for item in self.collection.find(filters)
        ]

    async def update(self, id: UUID, body: ProductUpdate) -> ProductUpdateOut:
        update_data = body.model_dump(exclude_none=True)
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )

        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        return ProductUpdateOut(**result)

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        result = await self.collection.delete_one({"id": id})

        return True if result.deleted_count > 0 else False


product_usecase = ProductUsecase()
