CREATE TABLE Training_Info (
    TrainingId SERIAL PRIMARY KEY,
    TrainingDescription text,
    ModelLocation text NOT NULL,
    ClassPerfAvg decimal(6,5) NOT NULL,
    --Consider additional metadata like a path to zip file
    --containing the pipeline.config, model, etc.
    CreatedByUser integer REFERENCES User_Info(UserId),
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp
);
