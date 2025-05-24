import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def import_csv_to_db():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logging.error("DATABASE_URL not found in .env file or environment.")
        return

    try:
        engine = create_engine(database_url)
        logging.info(f"Successfully created database engine for {engine.url.database}")
    except Exception as e:
        logging.error(f"Failed to create database engine: {e}")
        return

    try:
        # Read the CSV file
        # Assuming email_history.csv is in the same directory as this script
        csv_file_path = 'email_history.csv'
        df = pd.read_csv(csv_file_path)
        logging.info(f"Successfully read {len(df)} rows from {csv_file_path}")

        # Convert 'date' column to datetime objects if it's not already
        # The CSV has dates like '2025-05-09 17:14:49'
        df['date'] = pd.to_datetime(df['date'])
        
        # Ensure column names in DataFrame match table column names
        # CSV headers: date,to,subject,body,status
        # DB columns (from migration): id, date, to, subject, body, status
        # 'id' is autoincrementing, so we don't need to provide it.
        
        # Rename columns if necessary to match the database table
        # df.rename(columns={'old_name': 'new_name'}, inplace=True) # Example

    except FileNotFoundError:
        logging.error(f"Error: The file {csv_file_path} was not found.")
        return
    except Exception as e:
        logging.error(f"Error reading or processing CSV file: {e}")
        return

    with engine.connect() as connection:
        try:
            with connection.begin(): # Start a transaction
                # Optional: Clear the table before inserting new data
                # if you want to re-run the script and avoid duplicates.
                # connection.execute(text("DELETE FROM email_history"))
                # logging.info("Cleared existing data from email_history table.")

                for index, row in df.iterrows():
                    # Construct the SQL query carefully to prevent SQL injection if using f-strings directly.
                    # Using SQLAlchemy's text() and bind parameters is safer.
                    insert_query = text(
                        'INSERT INTO email_history (date, "to", subject, body, status) '
                        'VALUES (:date, :to, :subject, :body, :status)'
                    )
                    connection.execute(insert_query, {
                        'date': row['date'],
                        'to': row['to'],
                        'subject': row['subject'],
                        'body': row['body'],
                        'status': row['status']
                    })
                logging.info(f"Successfully inserted {len(df)} rows into email_history table.")
            logging.info("Data import committed successfully.")
        except SQLAlchemyError as e:
            logging.error(f"Database error during insertion: {e}")
            logging.error("Transaction rolled back.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during data insertion: {e}")
            logging.error("Transaction rolled back.")

if __name__ == "__main__":
    import_csv_to_db() 