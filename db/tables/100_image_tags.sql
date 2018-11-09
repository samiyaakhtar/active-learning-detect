-- Set up table
CREATE TABLE Image_Tags (
    ImageTagId SERIAL UNIQUE,
    ImageId integer REFERENCES Image_Info(ImageId) ON DELETE RESTRICT,
    X_Min decimal(6,2) NOT NULL,
    X_Max decimal(6,2) NOT NULL,
    Y_Min decimal(6,2) NOT NULL,
    Y_Max decimal(6,2) NOT NULL,
    CreatedByUser integer REFERENCES User_Info(UserId),
    CreatedDtim timestamp NOT NULL default current_timestamp,
    --VOTT_Data json NOT NULL
    PRIMARY KEY (ImageId,X_Min,X_Max,Y_Min,Y_Max) --Should we include the bounded box as well?
);