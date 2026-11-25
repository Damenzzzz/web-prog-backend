from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, String, Table, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.schemas.items import Category
from app.schemas.orders import OrderStatus
from app.schemas.try_on import TryOnStatus
from app.schemas.users import BodyType, Gender, Role

try_on_items = Table(
    "try_on_items",
    Base.metadata,
    Column("try_on_id", ForeignKey("try_ons.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
)


class Look(Base):
    __tablename__ = "looks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    items: Mapped[list["Item"]] = relationship(back_populates="look", order_by="Item.id")

    @property
    def item_ids(self) -> list[int]:
        return [item.id for item in self.items]


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_items_price_positive"),
        CheckConstraint("stock >= 0", name="ck_items_stock_not_negative"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[Category] = mapped_column(Enum(Category, name="category"))
    color: Mapped[str] = mapped_column(String(30))
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    look_id: Mapped[int | None] = mapped_column(ForeignKey("looks.id", ondelete="SET NULL"), index=True)
    image_url: Mapped[str | None] = mapped_column(String(255))
    look: Mapped[Look | None] = relationship(back_populates="items")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("height_cm BETWEEN 100 AND 250", name="ck_users_height"),
        CheckConstraint("weight_kg BETWEEN 30 AND 250", name="ck_users_weight"),
        UniqueConstraint("email", name="uq_users_email"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.user, server_default=Role.user.value)
    name: Mapped[str] = mapped_column(String(50))
    height_cm: Mapped[int] = mapped_column(Integer)
    weight_kg: Mapped[int] = mapped_column(Integer)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, name="gender"))
    body_type: Mapped[BodyType] = mapped_column(Enum(BodyType, name="body_type"))
    style_preference: Mapped[str | None] = mapped_column(String(200))
    photo_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fitting_room: Mapped[list["FittingRoomRow"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True, order_by="FittingRoomRow.id")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True, order_by="Order.id")
    try_ons: Mapped[list["TryOn"]] = relationship(back_populates="user", cascade="all, delete-orphan", passive_deletes=True, order_by="TryOn.id")


class FittingRoomRow(Base):
    __tablename__ = "fitting_room_rows"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_fitting_room_user_item"),
        CheckConstraint("quantity >= 1", name="ck_fitting_room_quantity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer)
    user: Mapped[User] = relationship(back_populates="fitting_room")
    item: Mapped[Item] = relationship()


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (CheckConstraint("total >= 0", name="ck_orders_total"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    total: Mapped[int] = mapped_column(Integer)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), default=OrderStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", passive_deletes=True, order_by="OrderItem.id")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_order_items_quantity"),
        CheckConstraint("price > 0", name="ck_order_items_price"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")


class TryOn(Base):
    __tablename__ = "try_ons"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[TryOnStatus] = mapped_column(Enum(TryOnStatus, name="try_on_status"))
    source: Mapped[str] = mapped_column(String(10))
    result_url: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="try_ons")
    items: Mapped[list[Item]] = relationship(secondary=try_on_items, order_by=Item.id)

    @property
    def item_ids(self) -> list[int]:
        return [item.id for item in self.items]
