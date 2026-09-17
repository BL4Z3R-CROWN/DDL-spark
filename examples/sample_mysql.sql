CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    age TINYINT,
    salary DECIMAL(10,2) DEFAULT 0.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    hired_at DATETIME,
    profile_json JSON,
    avatar BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE departments (
    dept_id SMALLINT NOT NULL PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    budget DOUBLE,
    created_at DATE
);
