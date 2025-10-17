-- Espera para asegurar que SQL Server esté listo
WAITFOR DELAY '00:00:10';

-- Crea la base de datos
CREATE DATABASE CircuitsDB;
GO

-- Cambia al contexto de la nueva base de datos
USE CircuitsDB;
GO

-- Crea la tabla para los circuitos
CREATE TABLE circuits (
    circuitId INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    location NVARCHAR(255),
    country NVARCHAR(255)
);
GO

-- Inserta los datos de los circuitos
INSERT INTO circuits (name, location, country) VALUES
('Albert Park Grand Prix Circuit', 'Melbourne', 'Australia'),
('Sepang International Circuit', 'Kuala Lumpur', 'Malaysia'),
('Bahrain International Circuit', 'Sakhir', 'Bahrain'),
('Circuit de Barcelona-Catalunya', 'Montmeló', 'Spain');
GO

-- Crea la tabla de pilotos con el tipo de dato correcto (FLOAT) para las estadísticas
CREATE TABLE pilots (
    pilotId INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    nationality NVARCHAR(255),
    years_active NVARCHAR(255),
    championships FLOAT,
    race_entries FLOAT,
    race_starts FLOAT,
    pole_positions FLOAT,
    race_wins FLOAT,
    podiums FLOAT,
    fastest_laps FLOAT
);
GO

-- Insertar datos de ejemplo con el nuevo formato
INSERT INTO pilots (name, nationality, years_active, championships, race_entries, race_starts, pole_positions, race_wins, podiums, fastest_laps) VALUES
('Lewis Hamilton', 'British', '[2007-2023]', 7, 332, 332, 104, 103, 197, 65),
('Max Verstappen', 'Dutch', '[2015-2023]', 3, 185, 185, 32, 54, 98, 30),
('Fernando Alonso', 'Spanish', '[2001-2023]', 2, 377, 374, 22, 32, 106, 24);
GO

-- Crear la tabla de usuarios con todas las columnas necesarias desde el principio
CREATE TABLE users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(255) UNIQUE NOT NULL,
    hashed_password NVARCHAR(255) NOT NULL,
    role NVARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BIT NOT NULL DEFAULT 0 -- 0 para inactivo, 1 para activo
);
GO

-- Insertar el usuario administrador (Contraseña: "test")
INSERT INTO users (username, hashed_password, role, is_active) VALUES
('testuser', '$2b$12$cg1s6.g9AGp.19EeFSCyh.qFW8EZZZWvRUX34j0zW0Onc3RHeo4vK', 'admin', 1);
GO
