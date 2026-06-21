CREATE DATABASE ai_sales_analytics;
USE ai_sales_analytics;

CREATE TABLE sales_orders (
    order_id VARCHAR(100),
    order_date DATE,
    sku VARCHAR(100),
    category VARCHAR(100),
    qty INT,
    amount DECIMAL(12,2),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    fulfillment VARCHAR(50),
    sales_channel VARCHAR(50),
    b2b VARCHAR(10)
);

CREATE TABLE products (
    sku VARCHAR(100) PRIMARY KEY,
    category VARCHAR(100),
    style VARCHAR(100),
    size VARCHAR(50),
    asin VARCHAR(50),
    price DECIMAL(12,2)
);

CREATE TABLE financials (
    date DATE,
    sku VARCHAR(100),
    revenue DECIMAL(12,2),
    expenses DECIMAL(12,2),
    profit DECIMAL(12,2)
);

CREATE TABLE inventory (
    sku VARCHAR(100),
    stock INT,
    category VARCHAR(100),
    size VARCHAR(50),
    color VARCHAR(50)
);