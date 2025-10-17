#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Start the SQL Server process in the background
/opt/mssql/bin/sqlservr &

# 2. Wait for it to be ready to accept connections
echo "Waiting for SQL Server to start..."
until /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -Q "SELECT 1" &>/dev/null; do
  >&2 echo "SQL Server is unavailable - sleeping"
  sleep 2
done

# 3. Run the setup script to create the DB and tables
echo "SQL Server is up - running setup script..."
/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$SA_PASSWORD" -C -d master -i /usr/src/app/setup.sql

echo "Initialization complete. SQL Server is running."

# Wait for the SQL Server process to end, keeping the container alive
wait