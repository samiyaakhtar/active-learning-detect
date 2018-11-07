-- Set up table
CREATE TABLE Classification_Info (
    ClassificationId SERIAL PRIMARY KEY,
    ClassificationName text NOT NULL,
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp
);
