-- Simple User table
CREATE TABLE User_Info (
    UserId SERIAL PRIMARY KEY,
    UserName citext NOT NULL UNIQUE,
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp
);