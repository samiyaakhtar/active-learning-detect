import sys
import string
import pg8000
import random
import os
import time
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from functions.pipeline.shared.db_access import ImageTagDataAccess
from functions.pipeline.shared.db_provider import PostGresProvider, DatabaseInfo
from functions.pipeline.shared.db_access.db_access_v2 import generate_test_image_infos

def get_transformed_id_to_url_map(id_to_url_map):
    updated_image_id_url_map = {}
    for image_id, old_url in id_to_url_map.items():
        replaced_path = old_url.replace('new-uploads','perm-uploads')   
        file_name_to_replace = extract_image_name_no_suffix(replaced_path)
        transformed_path = replaced_path.replace(file_name_to_replace,str(image_id))
        updated_image_id_url_map[image_id] = transformed_path
    return updated_image_id_url_map

def pretty_print_audit_history(conn, list_of_image_ids):
    if(len(list_of_image_ids) > 0):
        cursor = conn.cursor()
        image_ids_as_strings = [str(i) for i in list_of_image_ids]
        images_to_audit = '{0}'.format(', '.join(image_ids_as_strings))
        query = ("SELECT a.imageid,c.originalimagename, b.tagstatename, d.username, a.ArchiveDtim FROM image_tagging_state_audit a "
                "JOIN tagstate b ON a.tagstateid = b.tagstateid "
                "JOIN image_info c on a.imageid = c.imageid "
                "JOIN user_info d on a.modifiedbyuser = d.userid "
                "WHERE a.ImageId in ({0}) "
                "ORDER BY a.ImageId,ArchiveDtim ASC")
        cursor.execute(query.format(images_to_audit))
        row = cursor.fetchone()  
        print()
        if(row != None):
            print("ImageId\tImgName\tTagState\tUser\tLoggedTime")
        while row:  
            print("{0}\t{1}\t{2}\t{3}\t{4}".format(str(row[0]),str(row[1]),str(row[2]),str(row[3]),str(row[4])))  
            row = cursor.fetchone()
    else:
        print("No images!")

def extract_image_name_no_suffix(url):
    start_idx = url.rfind('/')+1
    end_idx = url.rfind('.')
    return url[start_idx:end_idx]

def extract_image_id_from_urls(list_of_image_urls):
        extracted_image_ids = []
        for url in list_of_image_urls:
            extracted_id = int(extract_image_name_no_suffix(url))
            extracted_image_ids.append(extracted_id)
        return extracted_image_ids

def main(num_of_images,user_name):
    try:
        if(os.getenv("DB_HOST") is None or os.getenv("DB_USER") is None or os.getenv("DB_NAME") is None or os.getenv("DB_PASS") is None):
            print("Please set environment variables for DB_HOST, DB_USER, DB_NAME, DB_PASS")
            return
        
        if(num_of_images < 5 or num_of_images > 20):
            print("Number of images should be between 5 and 20")
            return

        if(not user_name):
            print("User name cannot be empty or whitespace")
            return
        #################################################################
        # Below we simulate the following scenarios:
        #   Creating a User
        #   Onboarding of new images
        #   Checking out images to tag
        #   Checking in images that have or have not been tagged
        #################################################################   

        db_config = DatabaseInfo(os.getenv("DB_HOST"),os.getenv("DB_NAME"),os.getenv("DB_USER"),os.getenv("DB_PASS"))
        pg = PostGresProvider(db_config)
        data_access = ImageTagDataAccess(pg)
        user_id = data_access.create_user(user_name)

        NUMBER_OF_IMAGES = num_of_images
        
        # Simulate new images from VOTT getting created in some blob store
        mocked_images = generate_test_image_infos(NUMBER_OF_IMAGES)
        print()
        print("***\tSubject matter experts use the CLI to upload new images...")
        time.sleep(1)
        print()
        # Simulate the data access layer creating entries in the DB for the new images
        # and returning a map of the original image url to generaled image id 
        url_to_image_id_map = data_access.add_new_images(mocked_images, user_id)
        print()
        
        print("***\tBehind the scenes Az Functions move the images to a new blob location")
        time.sleep(1)
        print()
        #Invert the above map since the client will now be using the image id as a key
        image_to_url = {v: k for k, v in url_to_image_id_map.items()}

        # Simulates when the client has moved images to a new blob store container
        # and creates a payload for the data access layer with a map for image id to new urls
        updated_image_id_url_map = get_transformed_id_to_url_map(image_to_url)
        
        # Simulates the call the client makes to the data access layer
        # with the new payload. Image urls get updated in the DB
        data_access.update_image_urls(updated_image_id_url_map, user_id)
        
        print()
        print("***\tThe newly uploaded images are now onboarded with a 'ready to tag' state.  See audit history")
        print()
        time.sleep(1)
        
        # Prints the audit history of the generated of all the newly onboarded 
        # images involved in the simulation to prove the state tracking for onboarding.
        image_ids = list(updated_image_id_url_map.keys())
        pretty_print_audit_history(pg.get_connection(),image_ids)
        time.sleep(3)
        print()
        
        print("***\tSubject matter experts use the CLI to retrieve images in a 'ready to tag' state")
        time.sleep(2)
        print()
        
        list_of_image_urls = data_access.get_images_for_tagging(NUMBER_OF_IMAGES, user_id)
        print()
        print("***\tLet's wait for image taggers to get through the set of images....")
        time.sleep(5)
        print()
        print("***\tDone! Though the subject matter experts didn't complete tagging all images")
        time.sleep(2)
        print()
        
        '''
        print("***\tRegardless the SMEs use the CLI to post the VOTT json results")
        print()
        # Since we rename the original image name to a integer that matchs the DB image id
        # we need to extract out the image ids. Below this code is simulates extracting 
        # image ids from the VOTT JSON
        extracted_image_ids = extract_image_id_from_urls(list_of_image_urls)
       
        # Let assume 3 images got tagged and 2 images did not. The client will
        # call corresponding methods to update tagged and untagged states
        completed_tagged_ids = []
        incomplete_tagged_ids = []
        num_of_incomplete = NUMBER_OF_IMAGES/5
        for idx, img_id in enumerate(extracted_image_ids):
            if(idx > num_of_incomplete):
                completed_tagged_ids.append(img_id)
            else:
                incomplete_tagged_ids.append(img_id)

        data_access.update_tagged_images(completed_tagged_ids,user_id)
        data_access.update_incomplete_images(incomplete_tagged_ids,user_id)
        
        print()
        print("***\tVOTT json results are posted. Lets take a look at the audit history")
        time.sleep(2)
        # Finally lets look at the audit history again. We expect to see some images as tagged
        # and some as incomplete
        print()
        pretty_print_audit_history(pg.get_connection(),image_ids)

        print()
        print("Success!")
        '''
        #__verify_connect_to_db(get_connection())
        #get_unvisited_items(get_connection(),count_of_images)        
    except Exception as e: print(e)

if __name__ == "__main__":
    #print(sys.path)
    console = logging.StreamHandler()
    log = logging.getLogger()
    log.setLevel(logging.getLevelName('DEBUG'))
    log.addHandler(console)
    if (len(sys.argv) != 3):
        print("Usage: {0} (Number of Images) (User Name)".format(sys.argv[0]))
    else:
        main(int(sys.argv[1]), str(sys.argv[2])) 
