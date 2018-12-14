CREATE TABLE Class_Performance (
    TrainingId integer REFERENCES Training_Info(TrainingId),
    ClassificationId integer REFERENCES Classification_Info(ClassificationId),
    AvgPerf decimal(6,5) NOT NULL,
    PRIMARY KEY (TrainingId,ClassificationId)
);