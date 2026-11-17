from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import FittingRoomRow, Item, Order, OrderItem
from app.schemas.orders import OrderStatus
from app.services import users as users_service

ALLOWED_TRANSITIONS = {
    OrderStatus.pending: [OrderStatus.paid, OrderStatus.cancelled],
    OrderStatus.paid: [OrderStatus.shipped, OrderStatus.cancelled],
    OrderStatus.shipped: [],
    OrderStatus.cancelled: [],
}


def create_order(db: Session, user_id: int) -> Order:
    users_service.get_user(db, user_id)
    rows = list(db.scalars(select(FittingRoomRow).where(FittingRoomRow.user_id == user_id).order_by(FittingRoomRow.id)))
    if not rows:
        raise BusinessRuleError("Fitting room is empty")
    item_ids = [row.item_id for row in rows]
    items = {item.id: item for item in db.scalars(select(Item).where(Item.id.in_(item_ids)).with_for_update())}
    for row in rows:
        item = items[row.item_id]
        if row.quantity > item.stock:
            db.rollback()
            raise ConflictError(f"Not enough stock for item {item.id}: {item.stock} left")
    order = Order(user_id=user_id, total=0, status=OrderStatus.pending)
    for row in rows:
        item = items[row.item_id]
        item.stock -= row.quantity
        order.items.append(OrderItem(item_id=item.id, name=item.name, price=item.price, quantity=row.quantity))
        order.total += item.price * row.quantity
        db.delete(row)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def list_user_orders(db: Session, user_id: int) -> list[Order]:
    return users_service.get_user(db, user_id).orders


def get_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found")
    return order


def change_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    order = get_order(db, order_id)
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise ConflictError(f"Cannot change order status from {order.status} to {new_status}")
    if new_status == OrderStatus.cancelled:
        for row in order.items:
            if row.item_id is not None:
                db.get(Item, row.item_id).stock += row.quantity
    order.status = new_status
    db.commit()
    return order
