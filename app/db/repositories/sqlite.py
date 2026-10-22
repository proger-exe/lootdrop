"""SQLite repository implementations."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from app.data.enums import OrderStatus, StaffRole
from app.domain.catalog.entities import Category, Product


@dataclass(slots=True)
class SQLiteUserRepository:
    """SQLite user repository."""

    connection: sqlite3.Connection

    async def upsert_telegram_user(self, telegram_user: dict[str, Any]) -> int:
        """Create or update a Telegram user and return internal user ID."""

        self.connection.execute(
            """
            insert into users (
                telegram_id, username, first_name, last_name, language_code, last_activity_at
            )
            values (?, ?, ?, ?, ?, current_timestamp)
            on conflict(telegram_id) do update set
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                language_code = excluded.language_code,
                last_activity_at = current_timestamp,
                updated_at = current_timestamp
            """,
            (
                telegram_user["id"],
                telegram_user.get("username"),
                telegram_user.get("first_name"),
                telegram_user.get("last_name"),
                telegram_user.get("language_code"),
            ),
        )
        self.connection.commit()
        row = self.connection.execute(
            "select id from users where telegram_id = ?",
            (telegram_user["id"],),
        ).fetchone()
        return int(row["id"])

    async def has_accepted_legal(self, user_id: int, version: str) -> bool:
        """Return whether a user accepted the current legal version."""

        row = self.connection.execute(
            """
            select 1 from legal_acceptances
            where user_id = ? and legal_documents_version = ?
            """,
            (user_id, version),
        ).fetchone()
        return row is not None

    async def accept_legal(
        self,
        user_id: int,
        version: str,
        language_code: str | None,
    ) -> None:
        """Persist legal acceptance."""

        self.connection.execute(
            """
            insert or ignore into legal_acceptances
                (user_id, legal_documents_version, telegram_language_code)
            values (?, ?, ?)
            """,
            (user_id, version, language_code),
        )
        self.connection.commit()

    async def profile_summary(self, telegram_id: int) -> dict[str, Any]:
        """Return profile counters for a Telegram user."""

        row = self.connection.execute(
            """
            select u.id, u.username, u.first_name, u.created_at,
                   count(o.id) as orders_total,
                   sum(
                       case
                           when o.status in ('QUEUED', 'IN_PROGRESS', 'NEEDS_INFO')
                           then 1
                           else 0
                       end
                   ) as active_orders
            from users u
            left join orders o on o.user_id = u.id
            where u.telegram_id = ?
            group by u.id
            """,
            (telegram_id,),
        ).fetchone()
        if row is None:
            return {}
        return {
            "id": int(row["id"]),
            "username": row["username"],
            "first_name": row["first_name"],
            "created_at": row["created_at"],
            "orders_total": int(row["orders_total"] or 0),
            "active_orders": int(row["active_orders"] or 0),
        }

    async def list_order_cards(self, telegram_id: int) -> list[str]:
        """Return compact order cards for a Telegram user."""

        rows = self.connection.execute(
            """
            select o.public_id, o.status, o.base_amount_minor, o.base_currency,
                   o.created_at, oi.product_snapshot
            from orders o
            join users u on u.id = o.user_id
            left join order_items oi on oi.order_id = o.id
            where u.telegram_id = ?
            order by o.created_at desc, o.id desc
            limit 10
            """,
            (telegram_id,),
        ).fetchall()
        cards: list[str] = []
        for row in rows:
            snapshot = json.loads(row["product_snapshot"] or "{}")
            product_name = snapshot.get("name") or "Заказ"
            status = OrderStatus(row["status"])
            cards.append(
                f"{row['public_id']} · {product_name}\n"
                f"{status.value} · {int(row['base_amount_minor']) / 100:.2f} {row['base_currency']}"
            )
        return cards


@dataclass(slots=True)
class SQLiteStaffRepository:
    """SQLite staff repository."""

    connection: sqlite3.Connection
    owner_ids: frozenset[int]
    admin_ids: frozenset[int]

    async def get_roles(self, telegram_id: int) -> set[StaffRole]:
        """Return staff roles for a Telegram account."""

        if telegram_id in self.owner_ids:
            return {StaffRole.OWNER, StaffRole.ADMIN, StaffRole.MANAGER}
        if telegram_id in self.admin_ids:
            return {StaffRole.ADMIN, StaffRole.MANAGER}
        row = self.connection.execute(
            """
            select sr.role from staff_roles sr
            join staff s on s.id = sr.staff_id
            join users u on u.id = s.user_id
            where u.telegram_id = ? and s.is_active = 1
            """,
            (telegram_id,),
        )
        return {StaffRole(item["role"]) for item in row.fetchall()}


@dataclass(slots=True)
class SQLiteCatalogRepository:
    """SQLite catalog repository."""

    connection: sqlite3.Connection

    async def list_categories(self, *, active_only: bool = True) -> list[Category]:
        """List categories."""

        where = "where is_active = 1 and deleted_at is null" if active_only else ""
        rows = self.connection.execute(
            f"""
            select id, slug, name, description, media_file_id, is_active, sort_order
            from categories
            {where}
            order by sort_order, id
            """
        ).fetchall()
        return [
            Category(
                id=int(row["id"]),
                slug=str(row["slug"]),
                name=str(row["name"]),
                description=str(row["description"]),
                media_file_id=row["media_file_id"],
                is_active=bool(row["is_active"]),
                sort_order=int(row["sort_order"]),
            )
            for row in rows
        ]

    async def list_products(
        self,
        category_id: int,
        *,
        active_only: bool = True,
    ) -> list[Product]:
        """List products in a category."""

        active_clause = "and is_active = 1 and deleted_at is null" if active_only else ""
        rows = self.connection.execute(
            f"""
            select id, category_id, sku, name, short_description, full_description,
                   price_minor, base_currency, fulfillment_sla_minutes, fulfillment_schema,
                   is_active, is_featured, sort_order, media_file_id
            from products
            where category_id = ? {active_clause}
            order by sort_order, id
            """,
            (category_id,),
        ).fetchall()
        return [self._product_from_row(row) for row in rows]

    async def get_product(self, product_id: int) -> Product | None:
        """Get one product."""

        row = self.connection.execute(
            """
            select id, category_id, sku, name, short_description, full_description,
                   price_minor, base_currency, fulfillment_sla_minutes, fulfillment_schema,
                   is_active, is_featured, sort_order, media_file_id
            from products
            where id = ?
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        return self._product_from_row(row)

    async def get_category(self, category_id: int) -> Category | None:
        """Get one category."""

        row = self.connection.execute(
            """
            select id, slug, name, description, media_file_id, is_active, sort_order
            from categories
            where id = ?
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return Category(
            id=int(row["id"]),
            slug=str(row["slug"]),
            name=str(row["name"]),
            description=str(row["description"]),
            media_file_id=row["media_file_id"],
            is_active=bool(row["is_active"]),
            sort_order=int(row["sort_order"]),
        )

    def seed_game_catalog(self) -> None:
        """Create a game-first catalog and remove earlier placeholder demo data."""

        self.connection.execute(
            """
            update products
            set is_active = 0, deleted_at = current_timestamp
            where sku = 'CRYSTALS-2500' or sku like 'MC-%'
            """
        )
        self.connection.execute(
            """
            update categories
            set is_active = 0, deleted_at = current_timestamp
            where slug in ('currency', 'minecraft')
            """
        )
        games = [
            (
                "roblox",
                "🧱 Roblox",
                "Робуксы, пропуска и помощь с игровыми покупками.",
                [
                    (
                        "RBX-GAMEPASS",
                        "Покупка игрового пропуска",
                        "Покупка пропуска через менеджера.",
                        79900,
                    ),
                    ("RBX-GROUP-RANK", "Ранг в группе", "Выдача ранга в группе Roblox.", 39900),
                ],
            ),
            (
                "fortnite",
                "🪂 Fortnite",
                "В-баксы и косметические наборы через ручное оформление.",
                [
                    (
                        "FN-VBUCKS-1000",
                        "1 000 В-баксов",
                        "Пополнение В-баксов после проверки данных.",
                        89900,
                    ),
                    (
                        "FN-CREW",
                        "Подписка Fortnite Crew",
                        "Оформление подписки через менеджера.",
                        129900,
                    ),
                ],
            ),
            (
                "genshin",
                "✨ Genshin Impact",
                "Кристаллы Сотворения и Благословение с ручным исполнением.",
                [
                    (
                        "GI-WELKIN",
                        "Благословение полой луны",
                        "Пополнение благословения.",
                        59900,
                    ),
                    (
                        "GI-CRYSTALS-980",
                        "980 Кристаллов Сотворения",
                        "Пополнение кристаллов.",
                        149900,
                    ),
                ],
            ),
            (
                "steam",
                "🎮 Steam",
                "Подарки, пополнение и игровые услуги Steam.",
                [
                    ("STEAM-GIFT", "Подарок Steam", "Покупка подарка по ссылке.", 100000),
                    ("STEAM-WALLET", "Пополнение Steam", "Пополнение кошелька Steam.", 150000),
                ],
            ),
        ]
        schema_by_slug = {
            "roblox": {
                "fields": [
                    self._field("username", "Имя пользователя Roblox", "string"),
                    self._field("profile_url", "Ссылка на профиль", "url", required=False),
                ]
            },
            "fortnite": {
                "fields": [
                    self._field("epic_id", "ID Epic Games", "string"),
                    self._choice("platform", "Платформа", ["PC", "PlayStation", "Xbox", "Switch"]),
                ]
            },
            "genshin": {
                "fields": [
                    self._field("uid", "UID аккаунта", "integer"),
                    self._choice("region", "Регион", ["Europe", "Asia", "America", "TW/HK/MO"]),
                ]
            },
            "steam": {
                "fields": [
                    self._field("profile_url", "Ссылка на профиль Steam", "url"),
                    self._field("comment", "Комментарий", "multiline", required=False),
                ]
            },
        }
        for sort_order, (slug, name, description, products) in enumerate(games, start=10):
            self.connection.execute(
                """
                insert into categories (slug, name, description, sort_order)
                values (?, ?, ?, ?)
                on conflict(slug) do update set
                    name = excluded.name,
                    description = excluded.description,
                    sort_order = excluded.sort_order,
                    is_active = 1,
                    deleted_at = null,
                    updated_at = current_timestamp
                """,
                (slug, name, description, sort_order),
            )
            category_id = int(
                self.connection.execute(
                    "select id from categories where slug = ?",
                    (slug,),
                ).fetchone()["id"]
            )
            for product_sort, (sku, product_name, short_description, price_minor) in enumerate(
                products,
                start=10,
            ):
                self.connection.execute(
                    """
                    insert into products (
                        category_id, sku, name, short_description, full_description,
                        price_minor, base_currency, fulfillment_sla_minutes,
                        fulfillment_schema, sort_order, is_active
                    )
                    values (?, ?, ?, ?, ?, ?, 'RUB', 30, ?, ?, 1)
                    on conflict(sku) do update set
                        category_id = excluded.category_id,
                        name = excluded.name,
                        short_description = excluded.short_description,
                        full_description = excluded.full_description,
                        price_minor = excluded.price_minor,
                        base_currency = excluded.base_currency,
                        fulfillment_schema = excluded.fulfillment_schema,
                        sort_order = excluded.sort_order,
                        is_active = 1,
                        deleted_at = null,
                        updated_at = current_timestamp
                    """,
                    (
                        category_id,
                        sku,
                        product_name,
                        short_description,
                        f"{short_description} Заказ выполняется менеджером вручную.",
                        price_minor,
                        json.dumps(schema_by_slug[slug], ensure_ascii=False),
                        product_sort,
                    ),
                )
        self.connection.commit()

    @staticmethod
    def _field(
        key: str,
        label: str,
        field_type: str,
        *,
        required: bool = True,
    ) -> dict[str, Any]:
        """Build a fulfillment schema field."""

        return {
            "key": key,
            "label": label,
            "type": field_type,
            "required": required,
            "min_length": 3 if field_type == "string" else None,
            "max_length": 64 if field_type in {"string", "url"} else None,
        }

    @staticmethod
    def _choice(key: str, label: str, options: list[str]) -> dict[str, Any]:
        """Build a fulfillment schema choice field."""

        return {
            "key": key,
            "label": label,
            "type": "choice",
            "required": True,
            "options": options,
        }

    @staticmethod
    def _product_from_row(row: sqlite3.Row) -> Product:
        """Build a Product entity from a SQLite row."""

        return Product(
            id=int(row["id"]),
            category_id=int(row["category_id"]),
            sku=str(row["sku"]),
            name=str(row["name"]),
            short_description=str(row["short_description"]),
            full_description=str(row["full_description"]),
            price_minor=int(row["price_minor"]),
            base_currency=str(row["base_currency"]),
            fulfillment_sla_minutes=int(row["fulfillment_sla_minutes"]),
            fulfillment_schema=json.loads(str(row["fulfillment_schema"])),
            is_active=bool(row["is_active"]),
            is_featured=bool(row["is_featured"]),
            sort_order=int(row["sort_order"]),
            media_file_id=row["media_file_id"],
        )
