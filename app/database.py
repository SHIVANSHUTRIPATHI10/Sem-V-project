import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "transactions.db"


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            step INTEGER NOT NULL,
            amount REAL NOT NULL,
            oldbalanceOrg REAL NOT NULL,
            oldbalanceDest REAL NOT NULL,
            newbalanceDest REAL,
            type TEXT NOT NULL,
            nameDest TEXT NOT NULL,
            xgb_score REAL,
            lstm_score REAL,
            ae_score REAL,
            reconstruction_error REAL,
            risk_score REAL,
            risk_level TEXT,
            decision TEXT,
            alert INTEGER,
            analyst_feedback TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Database ready: {DB_PATH}")


def save_transaction(transaction):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                transaction_id, step, amount, oldbalanceOrg, oldbalanceDest,
                newbalanceDest, type, nameDest, xgb_score, lstm_score, ae_score,
                reconstruction_error, risk_score, risk_level, decision, alert
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction["transaction_id"], transaction["step"], transaction["amount"],
            transaction["oldbalanceOrg"], transaction["oldbalanceDest"],
            transaction.get("newbalanceDest"), transaction["type"], transaction["nameDest"],
            transaction.get("xgb_score"), transaction.get("lstm_score"), transaction.get("ae_score"),
            transaction.get("reconstruction_error"), transaction.get("risk_score"),
            transaction.get("risk_level"), transaction.get("decision"), int(transaction.get("alert", False))
        ))
        conn.commit()
    finally:
        conn.close()


def get_previous_transactions(nameDest, limit=5):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT step, amount, oldbalanceOrg, oldbalanceDest, newbalanceDest, type
            FROM transactions
            WHERE nameDest = ?
            ORDER BY step DESC
            LIMIT ?
        """, (nameDest, limit))
        rows = cursor.fetchall()
        transactions = [dict(row) for row in rows]
        transactions.reverse()
        return transactions
    finally:
        conn.close()


def get_transaction_history(nameDest):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, step, amount, oldbalanceOrg, oldbalanceDest, type,
                   nameDest, xgb_score, lstm_score, ae_score, reconstruction_error,
                   risk_score, risk_level, decision, alert
            FROM transactions
            WHERE nameDest = ?
            ORDER BY step ASC
        """, (nameDest,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_fraud_alerts():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, step, amount, type, nameDest, xgb_score, lstm_score,
                   ae_score, reconstruction_error, risk_score, risk_level, decision, alert, analyst_feedback
            FROM transactions
            WHERE alert = 1
            ORDER BY risk_score DESC
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_all_transactions():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_id, step, amount, type, nameDest, risk_score, risk_level, decision, alert, analyst_feedback
            FROM transactions
            ORDER BY step DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_feedback(transaction_id, feedback):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE transactions
            SET analyst_feedback = ?
            WHERE transaction_id = ?
        """, (feedback, transaction_id))
        conn.commit()
    finally:
        conn.close()


def get_dashboard_stats():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                SUM(CASE WHEN alert = 1 THEN 1 ELSE 0 END) AS total_alerts,
                SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk,
                SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk,
                SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) AS low_risk,
                AVG(risk_score) AS average_risk_score
            FROM transactions
        """)
        row = cursor.fetchone()
        total_transactions = row["total_transactions"] or 0
        total_alerts = row["total_alerts"] or 0
        high_risk = row["high_risk"] or 0
        medium_risk = row["medium_risk"] or 0
        low_risk = row["low_risk"] or 0
        average_risk_score = row["average_risk_score"] or 0

        alert_percentage = (total_alerts / total_transactions * 100) if total_transactions > 0 else 0

        return {
            "total_transactions": total_transactions,
            "total_alerts": total_alerts,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "average_risk_score": round(average_risk_score, 4),
            "alert_percentage": round(alert_percentage, 2)
        }
    finally:
        conn.close()




def save_transaction(transaction):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Check if the transaction already exists
        cursor.execute("SELECT id FROM transactions WHERE transaction_id = ?", (transaction["transaction_id"],))
        existing = cursor.fetchone()

        if existing:
            # Update the existing record
            cursor.execute("""
                UPDATE transactions SET
                    step = ?, amount = ?, oldbalanceOrg = ?, oldbalanceDest = ?,
                    newbalanceDest = ?, type = ?, nameDest = ?, xgb_score = ?,
                    lstm_score = ?, ae_score = ?, reconstruction_error = ?,
                    risk_score = ?, risk_level = ?, decision = ?, alert = ?
                WHERE transaction_id = ?
            """, (
                transaction["step"], transaction["amount"], transaction["oldbalanceOrg"],
                transaction["oldbalanceDest"], transaction.get("newbalanceDest"),
                transaction["type"], transaction["nameDest"], transaction.get("xgb_score"),
                transaction.get("lstm_score"), transaction.get("ae_score"),
                transaction.get("reconstruction_error"), transaction.get("risk_score"),
                transaction.get("risk_level"), transaction.get("decision"),
                int(transaction.get("alert", False)), transaction["transaction_id"]
            ))
            print(f"Updated existing transaction: {transaction['transaction_id']}")
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_id, step, amount, oldbalanceOrg, oldbalanceDest,
                    newbalanceDest, type, nameDest, xgb_score, lstm_score, ae_score,
                    reconstruction_error, risk_score, risk_level, decision, alert
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction["transaction_id"], transaction["step"], transaction["amount"],
                transaction["oldbalanceOrg"], transaction["oldbalanceDest"],
                transaction.get("newbalanceDest"), transaction["type"], transaction["nameDest"],
                transaction.get("xgb_score"), transaction.get("lstm_score"), transaction.get("ae_score"),
                transaction.get("reconstruction_error"), transaction.get("risk_score"),
                transaction.get("risk_level"), transaction.get("decision"), int(transaction.get("alert", False))
            ))
            print(f"Inserted new transaction: {transaction['transaction_id']}")
            
        conn.commit()
    finally:
        conn.close()