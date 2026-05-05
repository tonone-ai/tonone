# FIXTURE FILE — intentionally contains N+1 query patterns for Spine perf tests.
# DO NOT use this in production code.

import sqlite3

# --- Django ORM-style patterns (simulated with attribute access) ---


class FakeQuerySet:
    """Minimal ORM queryset stub for pattern testing."""

    def filter(self, **kwargs):
        return self

    def all(self):
        return []

    def get(self, **kwargs):
        return FakeModel()


class FakeModel:
    def __init__(self):
        self.id = 1
        self.name = "test"


# Stub globals to mimic ORM-like access
objects = FakeQuerySet()


def get_all_orders_with_customers():
    """Classic N+1: loop over orders, query customer inside loop."""
    orders = objects.filter(status="active")
    result = []
    for order in orders:
        # N+1: hits DB once per order
        customer = objects.filter(id=order.id).get(id=order.id)
        result.append({"order": order, "customer": customer})
    return result


def get_posts_with_comments():
    """Missing prefetch_related: accesses related field in loop."""
    posts = objects.all()
    summaries = []
    for post in posts:
        # N+1: each post.comments triggers a new query
        count = post.comments.all()
        summaries.append({"post": post, "comment_count": count})
    return summaries


def load_users_missing_select_related():
    """Missing select_related: accesses FK in loop."""
    users = objects.filter(active=True)
    rows = []
    for user in users:
        # N+1: user.profile is a FK, accessed in loop without select_related
        profile = user.profile
        rows.append(profile)
    return rows


# --- Raw SQL N+1 patterns ---


def fetch_orders_raw(db_path: str):
    """Raw SQL in loop: executes cursor.execute inside for-loop."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM orders")
    order_ids = cursor.fetchall()

    results = []
    for (order_id,) in order_ids:
        # N+1: separate query per order inside loop
        cursor.execute("SELECT * FROM customers WHERE order_id = ?", (order_id,))
        customer = cursor.fetchone()
        results.append(customer)

    conn.close()
    return results


def fetch_products_formatted_sql(conn, category_ids: list):
    """String-formatted SQL in loop (injection risk + N+1)."""
    cursor = conn.cursor()
    results = []
    for cat_id in category_ids:
        # Bad: string format inside loop — N+1 + SQL injection risk
        query = "SELECT * FROM products WHERE category_id = %s" % cat_id
        cursor.execute(query)
        results.extend(cursor.fetchall())
    return results


# --- Async handler with sync DB call pattern ---


async def async_handler_with_sync_db(request_ids: list):
    """Synchronous DB call pattern inside async context."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    items = []
    for req_id in request_ids:
        # Sync blocking call in async handler
        cursor.execute("SELECT * FROM requests WHERE id = ?", (req_id,))
        row = cursor.fetchone()
        items.append(row)
    conn.close()
    return items
