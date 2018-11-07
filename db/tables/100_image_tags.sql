-- Set up table
CREATE TABLE Image_Tags (
    ImageTagId SERIAL UNIQUE,
    ImageId integer REFERENCES Image_Info(ImageId) ON DELETE RESTRICT,
    --ClassificationId text NOT NULL, --Needed?
    --Confidence double precision NOT NULL, --Needed?
    X_Min double precision NOT NULL, 
    X_Max double precision NOT NULL,
    Y_Min double precision NOT NULL,
    Y_Max double precision NOT NULL,
    --VOTT_Data json NOT NULL
    PRIMARY KEY (ImageTagId,ImageId)
);