--TO DELETE
CREATE TABLE Tags_Classification (
    ImageTagId integer REFERENCES Image_Tags(ImageTagId),
    ClassificationId integer REFERENCES Classification_Info(ClassificationId),
    ModifiedDtim timestamp NOT NULL default current_timestamp,
    CreatedDtim timestamp NOT NULL default current_timestamp,
    PRIMARY KEY (ImageTagId,ClassificationId)
);