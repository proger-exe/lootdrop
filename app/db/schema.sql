create table if not exists users (
    id integer primary key autoincrement,
    telegram_id integer not null unique,
    username text,
    first_name text,
    last_name text,
    language_code text,
    is_blocked integer not null default 0,
    is_bot_blocked integer not null default 0,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    last_activity_at text
);

create table if not exists legal_acceptances (
    id integer primary key autoincrement,
    user_id integer not null references users(id),
    legal_documents_version text not null,
    telegram_language_code text,
    accepted_at text not null default current_timestamp,
    unique (user_id, legal_documents_version)
);

create table if not exists staff (
    id integer primary key autoincrement,
    user_id integer not null references users(id),
    public_name text not null,
    is_active integer not null default 1,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create table if not exists staff_roles (
    staff_id integer not null references staff(id),
    role text not null,
    primary key (staff_id, role)
);

create table if not exists categories (
    id integer primary key autoincrement,
    slug text not null unique,
    name text not null,
    description text not null default '',
    media_file_id text,
    is_active integer not null default 1,
    sort_order integer not null default 0,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    deleted_at text
);

create table if not exists products (
    id integer primary key autoincrement,
    category_id integer not null references categories(id),
    sku text not null unique,
    name text not null,
    short_description text not null,
    full_description text not null,
    price_minor integer not null,
    base_currency text not null,
    media_file_id text,
    is_active integer not null default 1,
    is_featured integer not null default 0,
    sort_order integer not null default 0,
    fulfillment_sla_minutes integer not null,
    fulfillment_schema text not null,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    deleted_at text
);

create table if not exists orders (
    id integer primary key autoincrement,
    public_id text not null unique,
    user_id integer not null references users(id),
    status text not null,
    assigned_manager_id integer references staff(id),
    base_amount_minor integer not null,
    base_currency text not null,
    checkout_idempotency_key text not null unique,
    user_comment text,
    internal_comment text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    paid_at text,
    queued_at text,
    started_at text,
    completed_at text,
    cancelled_at text,
    version integer not null default 1
);

create table if not exists order_items (
    id integer primary key autoincrement,
    order_id integer not null references orders(id),
    product_id integer references products(id),
    product_snapshot text not null,
    quantity integer not null,
    unit_price_minor integer not null,
    total_price_minor integer not null
);

create table if not exists order_fulfillment_data (
    id integer primary key autoincrement,
    order_id integer not null references orders(id),
    field_key text not null,
    encrypted_value text not null,
    masked_value text not null,
    created_at text not null default current_timestamp,
    unique (order_id, field_key)
);

create table if not exists order_status_history (
    id integer primary key autoincrement,
    order_id integer not null references orders(id),
    from_status text,
    to_status text not null,
    actor_type text not null,
    actor_user_id integer,
    created_at text not null default current_timestamp
);

create table if not exists order_messages (
    id integer primary key autoincrement,
    order_id integer not null references orders(id),
    sender_type text not null,
    sender_user_id integer,
    body text,
    file_id text,
    created_at text not null default current_timestamp
);

create table if not exists payment_methods (
    id integer primary key autoincrement,
    ticker text not null unique,
    display_name text not null,
    network text not null,
    asset text not null,
    destination_address text not null,
    confirmations_required integer not null default 1,
    is_active integer not null default 1,
    sort_order integer not null default 0,
    icon_file_id text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create table if not exists payment_invoices (
    id integer primary key autoincrement,
    public_id text not null unique,
    order_id integer not null references orders(id),
    provider text not null,
    ticker text not null,
    network text not null,
    asset text not null,
    base_amount_minor integer not null,
    base_currency text not null,
    expected_coin_amount text not null,
    received_coin_amount text not null default '0',
    forwarded_coin_amount text,
    exchange_rate text not null,
    destination_address text not null,
    payment_address text not null,
    callback_url text not null,
    callback_nonce_hash text not null,
    provider_payload text not null,
    minimum_transaction_coin text not null default '0',
    expires_at text not null,
    status text not null,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    confirmed_at text,
    last_polled_at text,
    next_poll_at text
);

create table if not exists payment_poll_events (
    id integer primary key autoincrement,
    invoice_id integer not null references payment_invoices(id),
    provider text not null,
    provider_uuid text not null,
    ticker text not null,
    txid_in text not null,
    txid_out text,
    pending integer not null,
    raw_payload text not null,
    duplicate_count integer not null default 0,
    created_at text not null default current_timestamp,
    unique (provider, provider_uuid),
    unique (provider, ticker, txid_in, pending)
);

create table if not exists support_tickets (
    id integer primary key autoincrement,
    public_id text not null unique,
    user_id integer not null references users(id),
    order_id integer references orders(id),
    category text not null,
    status text not null,
    assigned_staff_id integer references staff(id),
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    closed_at text
);

create table if not exists support_messages (
    id integer primary key autoincrement,
    ticket_id integer not null references support_tickets(id),
    sender_type text not null,
    sender_user_id integer,
    body text,
    file_id text,
    created_at text not null default current_timestamp
);

create table if not exists notifications (
    id integer primary key autoincrement,
    user_id integer references users(id),
    event_type text not null,
    payload text not null,
    status text not null default 'PENDING',
    created_at text not null default current_timestamp,
    sent_at text
);

create table if not exists audit_logs (
    id integer primary key autoincrement,
    actor_type text not null,
    actor_user_id integer,
    action text not null,
    entity_type text not null,
    entity_id text not null,
    before_data text,
    after_data text,
    ip_address text,
    request_id text,
    created_at text not null default current_timestamp
);

create table if not exists application_settings (
    key text primary key,
    value text not null,
    updated_at text not null default current_timestamp
);

create table if not exists outbox_events (
    id integer primary key autoincrement,
    event_type text not null,
    payload text not null,
    status text not null default 'PENDING',
    attempts integer not null default 0,
    created_at text not null default current_timestamp,
    locked_at text,
    processed_at text
);

create index if not exists idx_payment_invoices_polling
    on payment_invoices(status, next_poll_at);

create index if not exists idx_orders_user_status on orders(user_id, status);
create index if not exists idx_orders_queue on orders(status, assigned_manager_id);
