CREATE TABLE Prediction_Labels (
    TrainingId integer REFERENCES Training_Info(TrainingId),
    ImageId integer REFERENCES Image_Info(ImageId),
    ClassificationId integer REFERENCES Classification_Info(ClassificationId),
    X_Min decimal(6,2) NOT NULL,
    X_Max decimal(6,2) NOT NULL,
    Y_Min decimal(6,2) NOT NULL,
    Y_Max decimal(6,2) NOT NULL,
    BoxConfidence decimal(5,4) NOT NULL,
    ImageConfidence decimal(5,4) NOT NULL,
    PRIMARY KEY (TrainingId,ImageId,ClassificationId,X_Min,X_Max,Y_Min,Y_Max)
);
