import pytest

from utils.sql_policy import SqlPolicyError, validate_read_only_sql


@pytest.mark.parametrize("query", ["SELECT * FROM products", "WITH recent AS (SELECT * FROM products) SELECT * FROM recent"])
def test_read_only_sql_is_allowed(query):
    validate_read_only_sql(query, {"products"})


@pytest.mark.parametrize("query", [
    "SELECT 1; DELETE FROM products",
    "SELECT * FROM products -- DELETE FROM products",
    "INSERT INTO products VALUES (1)",
    "UPDATE products SET name = 'x'",
    "DELETE FROM products",
    "DROP TABLE products",
    "ALTER TABLE products ADD COLUMN x INT",
    "TRUNCATE TABLE products",
    "CALL unsafe()",
    "LOAD DATA INFILE 'x' INTO TABLE products",
])
def test_mutating_or_multi_statement_sql_is_rejected(query):
    with pytest.raises(SqlPolicyError):
        validate_read_only_sql(query, {"products"})


def test_unknown_table_is_rejected():
    with pytest.raises(SqlPolicyError):
        validate_read_only_sql("SELECT * FROM unknown_table", {"products"})
