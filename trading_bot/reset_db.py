
import database as db
from database import engine, metadata

def reset_db():
    print("Resetting Database Schema...")
    metadata.drop_all(engine)
    metadata.create_all(engine)
    print("Database Reset Complete.")

if __name__ == "__main__":
    reset_db()
