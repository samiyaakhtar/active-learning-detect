-- Set up table
CREATE TABLE Tags_Classification (
    ImageTagId integer REFERENCES Image_Tags(ImageTagId) UNIQUE,
    ClassificationId integer REFERENCES Classification_Info(ClassificationId),
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp,
    PRIMARY KEY (ImageTagId,ClassificationId)
   --CONSTRAINT FK_IMAGE_TAG FOREIGN KEY(ImageTagId),
    --CONSTRAINT FK_CLASSIFICATION FOREIGN KEY(ClassificationId) 
);