-- ActionFlag: 1 = insert, 2 = update, 3 = delete
CREATE OR REPLACE FUNCTION log_image_tagging_state_changes()
    RETURNS trigger AS
    '
        BEGIN
            IF NEW.TagStateId <> OLD.TagStateId THEN
                INSERT INTO Image_Tagging_State_Audit(ImageId,TagStateId,ModifiedByUser,ModifiedDtim,ArchiveDtim,ActionFlag)
                VALUES(NEW.ImageId,NEW.TagStateId,NEW.ModifiedByUser,NEW.ModifiedDtim,current_timestamp,2);
            END IF;
            
            RETURN NEW;
        END;
    '
    LANGUAGE plpgsql;