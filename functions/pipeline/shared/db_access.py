import os
import pg8000

from enum import IntEnum, unique

# TODO: Add error handling cases

@unique
class ImageTagState(IntEnum):
    NOT_READY = 0
    READY_TO_TAG = 1
    TAG_IN_PROGRESS = 2
    COMPLETED_TAG = 3
    INCOMPLETE_TAG = 4
    ABANDONED = 5

# Temp for local testing/
default_db_host = ""
default_db_name = ""
default_db_user = ""
default_db_pass = ""

# An entity class for a VOTT image
class ImageInfo(object):
    def __init__(self, image_name, image_location, height, width):
        self.image_name = image_name
        self.image_location = image_location
        self.height = height
        self.width = width

def get_connection():
    return __new_postgres_connection(os.getenv('DB_HOST', default_db_host), os.getenv('DB_NAME', default_db_name), os.getenv('DB_USER', default_db_user), os.getenv('DB_PASS', default_db_pass))

def __new_postgres_connection(host_name, db_name, db_user, db_pass):
    return pg8000.connect(db_user, host=host_name, unix_sock=None, port=5432, database=db_name, password=db_pass, ssl=True, timeout=None, application_name=None)

def get_image_ids_for_new_images(conn, list_of_image_infos):
    url_to_image_id_map = {}
    if(len(list_of_image_infos) > 0):
        cursor = conn.cursor()
        for img in list(list_of_image_infos):
            query = "INSERT INTO Image_Info (OriginalImageName,ImageLocation,Height,Width) VALUES ('{0}','{1}',{2},{3}) RETURNING ImageId;"
            cursor.execute(query.format(img.image_name,img.image_location,str(img.height),str(img.width)))
            new_img_id = cursor.fetchone()[0]
            url_to_image_id_map[img.image_location] = new_img_id
            #__update_images(conn,[new_img_id],ImageTagState.NOT_READY)
        conn.commit()
    print(f"Inserted {len(url_to_image_id_map)} images to the DB")
    return url_to_image_id_map

def get_images_for_tagging(conn, num_images):
    cursor = conn.cursor()

    # From the database, select the number of images the user requested where tag state is "READY_TO_TAG"
    cursor.execute("SELECT b.ImageId, b.OriginalImageName, a.TagStateId, b.ImageLocation FROM Image_Tagging_State a JOIN Image_Info b ON a.ImageId = b.ImageId WHERE a.TagStateId IN ({0},{1}) order by a.createddtim ASC limit {2}".format(ImageTagState.READY_TO_TAG, ImageTagState.INCOMPLETE_TAG,num_images))
    
    # Put the ImageId and ImageLocation (URL) for the images to tag into a dictionary named selected_images_to_tag
    selected_images_to_tag = {}
    for row in cursor:
        print('Image Id: {0} \t\tImage Name: {1} \t\tTag State: {2}'.format(row[0], row[1], row[2]))
        selected_images_to_tag[str(row[0])] = str(row[3])
    
    # If there are images in the list, update the tagging state for the selected images from "READY_TO_TAG" to "TAG_IN_PROGRESS" state
    # If there are no images left to tag, output a message to the user
    # TODO: Separate this code out into an "update" helper function?
    if(len(selected_images_to_tag) > 0):
        images_to_update = '{0}'.format(', '.join(selected_images_to_tag.keys()))
        cursor.execute("UPDATE Image_Tagging_State SET TagStateId = {0} WHERE ImageId IN ({1})".format(ImageTagState.TAG_IN_PROGRESS, images_to_update))
        conn.commit()
        print("Updated {len(selected_images_to_tag)} images to the state {0}".format(ImageTagState.TAG_IN_PROGRESS))
    else:
        print("No images untagged images left!")
    # Return the list of URLs to the user (values in the selected_images_to_tag dictionary)
    return list(selected_images_to_tag.values())

def update_tagged_images(conn, list_of_image_ids):
    __update_images(conn, list_of_image_ids, ImageTagState.COMPLETED_TAG)
    print("Updated {0} image(s) to the state {1}".format(len(list_of_image_ids),ImageTagState.COMPLETED_TAG.name))

def update_untagged_images(conn, list_of_image_ids):
    __update_images(conn, list_of_image_ids, ImageTagState.INCOMPLETE_TAG)
    print("Updated {0} image(s) to the state {1}".format(len(list_of_image_ids),ImageTagState.INCOMPLETE_TAG.name))

def __update_images(conn, list_of_image_ids, new_image_tag_state):
    if not isinstance(new_image_tag_state, ImageTagState):
        raise TypeError('new_image_tag_state must be an instance of Direction Enum')

    if(len(list_of_image_ids) > 0):
        cursor = conn.cursor()
        image_ids_as_strings = [str(i) for i in list_of_image_ids]
        images_to_update = '{0}'.format(', '.join(image_ids_as_strings))
        query = "UPDATE Image_Tagging_State SET TagStateId = {0}, ModifiedDtim = now() WHERE ImageId IN ({1})"
        cursor.execute(query.format(new_image_tag_state,images_to_update))
        conn.commit()
        #print(f"Updated {len(list_of_image_ids)} image(s) to the state {new_image_tag_state.name}")
    else:
        print("No images to update")