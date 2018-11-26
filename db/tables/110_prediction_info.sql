CREATE TABLE Prediction_Info (
    ImageTagId integer REFERENCES Image_Tags(ImageTagId),
    ClassificationId integer REFERENCES Classification_Info(ClassificationId),
    TrainingId integer REFERENCES Training_Info(TrainingId),
    BoxConfidence decimal(5,4) NOT NULL,
    ImageConfidence decimal(5,4) NOT NULL,
    PRIMARY KEY (ImageTagId,ClassificationId,TrainingId)
);