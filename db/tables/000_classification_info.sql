-- Set up table
CREATE TABLE Classification_Info (
    ClassificationId SERIAL PRIMARY KEY,
    ClassificationName citext NOT NULL UNIQUE,
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp
);
