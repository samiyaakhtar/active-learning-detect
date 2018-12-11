import string
import logging
import random
from enum import IntEnum, unique
import getpass
import itertools
from ..db_provider import DatabaseInfo, PostGresProvider


@unique
class ImageTagState(IntEnum):
    NOT_READY = 0
    READY_TO_TAG = 1
    TAG_IN_PROGRESS = 2
    COMPLETED_TAG = 3
    INCOMPLETE_TAG = 4
    ABANDONED = 5

# An entity class for a VOTT image
class ImageInfo(object):
    def __init__(self, image_name, image_location, height, width):
        self.image_name = image_name
        self.image_location = image_location
        self.height = height
        self.width = width


# Entity class for Tags stored in DB
class ImageTag(object):
    def __init__(self, image_id, x_min, x_max, y_min, y_max, classification_names):
        self.image_id = image_id
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.classification_names = classification_names

#This class doesn't have box and image confidence because they are human curated labels
class AnnotatedLabel(object):
    def __init__(self, image_id, classification_id, x_min, x_max, y_min, y_max):
        self.image_id = image_id
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.classification_id = classification_id

# TODO: Think about moving all this schemas to a separate file 
class ImageLabel(object):
    def __init__(self,image_id, imagelocation,image_height: int, image_width: int, labels: list, user_folder=None):
        self.image_id = image_id
        self.imagelocation = imagelocation
        self.image_height = image_height
        self.image_width = image_width
        self.user_folder = user_folder
        self.labels = labels

class Tag(object):
    def __init__(self,classificationname, x_min: float, x_max: float, y_min: float, y_max: float):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_min
        self.classificationname = classificationname

class PredictionLabel(AnnotatedLabel):
    def __init__(self, training_id, image_id, classification_id, x_min, x_max, y_min, y_max, 
                image_height, image_width, box_confidence=0, image_confidence= 0):
        super().__init__(image_id, classification_id, x_min, x_max, y_min, y_max)
        self.training_id = training_id
        self.image_height = image_height
        self.image_width = image_width
        self.box_confidence = box_confidence
        self.image_confidence = image_confidence


# Vott tags have image height & width data as well.
class VottImageTag(ImageTag):
    def __init__(self, image_id, x_min, x_max, y_min, y_max, classification_names, image_height, image_width, image_location):
        super().__init__(image_id, x_min, x_max, y_min, y_max, classification_names)
        self.image_height = image_height
        self.image_width = image_width
        self.image_location = image_location


class ImageTagDataAccess(object):
    def __init__(self,  db_provider):
        self._db_provider = db_provider

    def test_connection(self):
        conn = self._db_provider.get_connection()
        cursor = conn.cursor()
        cursor.execute('select * from tagstate')
        row = cursor.fetchone()
        logging.info('')
        while row:
            logging.info(str(row[0]) + " " + str(row[1]))
            row = cursor.fetchone()

    def create_user(self,user_name):
        user_id = -1
        if not user_name:
            raise ArgumentException("Parameter cannot be an empty string")
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = ("WITH existingUser AS ( "
                        "SELECT Userid,UserName FROM User_Info "
                        "WHERE username = %s), "
                    "data(user_name) AS (values (%s)), "
                    "newUser AS ( "
                        "INSERT INTO User_Info (UserName) "
                        "SELECT d.user_name FROM data d "
                        "WHERE NOT EXISTS (select 1 FROM User_Info u WHERE u.UserName = d.user_name) "
                        "RETURNING userid,username) "
                    "SELECT userid,username FROM newUser "  
                    "UNION ALL "
                    "SELECT userid,username FROM existingUser")
                cursor.execute(query,(user_name,user_name,))
                user_id = cursor.fetchone()[0]
                conn.commit()
            finally: cursor.close()
        except Exception as e:
            logging.error("An error occured creating a user: {0}".format(e))
            raise
        finally: conn.close()
        return user_id

    def get_images_for_tagging(self, number_of_images, user_id):
        if number_of_images <= 0:
            raise ArgumentException("Parameter must be greater than zero")

        selected_images_to_tag = {}
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = ("SELECT b.ImageId, b.ImageLocation, a.TagStateId FROM Image_Tagging_State a "
                        "JOIN Image_Info b ON a.ImageId = b.ImageId WHERE a.TagStateId IN ({1}, {2}) order by "
                        "a.createddtim DESC limit {0}")
                cursor.execute(query.format(number_of_images, ImageTagState.READY_TO_TAG, ImageTagState.INCOMPLETE_TAG))
                for row in cursor:
                    logging.debug('Image Id: {0} \t\tImage Name: {1} \t\tTag State: {2}'.format(row[0], row[1], row[2]))
                    selected_images_to_tag[row[0]] = str(row[1])
                self._update_images(selected_images_to_tag,ImageTagState.TAG_IN_PROGRESS, user_id, conn)
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An errors occured getting images: {0}".format(e))
            raise
        finally:
            conn.close()
        return selected_images_to_tag

    def add_new_images(self,list_of_image_infos, user_id):

        if type(user_id) is not int:
            raise TypeError('user id must be an integer')

        url_to_image_id_map = {}
        if(len(list_of_image_infos) > 0):
            try:
                conn = self._db_provider.get_connection()
                try:
                    cursor = conn.cursor()
                    for img in list(list_of_image_infos):
                        query = ("INSERT INTO Image_Info (OriginalImageName,ImageLocation,Height,Width,CreatedByUser) "
                                "VALUES (%s,%s,%s,%s,%s) RETURNING ImageId;")
                        cursor.execute(query,(img.image_name,img.image_location,img.height,img.width,user_id))
                        new_img_id = cursor.fetchone()[0]
                        url_to_image_id_map[img.image_location] = new_img_id
                    conn.commit()
                finally: cursor.close()
                logging.debug("Inserted {0} images to the DB".format(len(url_to_image_id_map)))
            except Exception as e:
                logging.error("An errors occured getting image ids: {0}".format(e))
                raise
            finally: conn.close()
        return url_to_image_id_map

    def get_images_by_tag_status(self, tag_status, limit=None):
        images_by_tag_status = {}
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                tags = ''
                for id in tag_status:
                    tags += str(id) + ','
                tags = tags[:-1]
                query = ("SELECT b.ImageId, b.ImageLocation, a.TagStateId FROM Image_Tagging_State a "
                        "JOIN Image_Info b ON a.ImageId = b.ImageId WHERE a.TagStateId IN ({0}) order by "
                        "a.createddtim DESC")
                if limit:
                    query += " limit {1}"
                cursor.execute(query.format(tags, limit))
                for row in cursor:
                    logging.debug('Image Id: {0} \t\tImage Name: {1} \t\tTag State: {2}'.format(row[0], row[1], row[2]))
                    images_by_tag_status[row[0]] = str(row[1])
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An errors occured getting ready to tag images: {0}".format(e))
            raise
        finally:
            conn.close()
        return images_by_tag_status
  
    def get_image_info_for_image_ids(self, image_ids):
        if not image_ids:
            return list()

        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                ids = ''
                for id in image_ids:
                    ids += str(id) + ','
                ids = ids[:-1]
                query = ("select imageid, originalimagename, imagelocation, height, width, createdbyuser from image_info where imageid IN ({0});")
                cursor.execute(query.format(ids))
                logging.debug("Got image info back for image_id={}".format(image_ids))

                images_info = []
                for row in cursor:
                    info = {}
                    info['height'] = row[3]
                    info['width'] = row[4]
                    info['name'] = row[1]
                    info['location'] = row[2]
                    info['id'] = row[0]
                    images_info.append(info)
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An error occurred getting image tags {0}".format(e))
            raise
        finally:
            conn.close()
        return list(images_info)
  
    def get_image_tags_for_image_ids(self, image_ids):
        if not image_ids:
            return dict()
            
        image_id_to_vott_tags = {}
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                ids = ''
                for id in image_ids:
                    ids += str(id) + ','
                ids = ids[:-1]
                query = ("SELECT image_tags.imagetagid, image_info.imageid, x_min, x_max, y_min, y_max, "
                         "classification_info.classificationname, image_info.height, image_info.width, image_info.imagelocation "
                            "FROM image_tags "
                                "inner join tags_classification on image_tags.imagetagid = tags_classification.imagetagid "
                                "inner join classification_info on tags_classification.classificationid = classification_info.classificationid "
                                "inner join image_info on image_info.imageid = image_tags.imageid "
                            "WHERE image_tags.imageid IN ({0});")
                cursor.execute(query.format(ids,))

                logging.debug("Got image tags back for image_id={}".format(image_ids))
                tag_id_to_vott_tags = self.__build_id_to_VottImageTag(cursor)
                for vott_tag in tag_id_to_vott_tags.values():
                    if vott_tag.image_id not in image_id_to_vott_tags:
                        image_id_to_vott_tags[vott_tag.image_id] = []
                    image_id_to_vott_tags[vott_tag.image_id].append(vott_tag)
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An error occurred getting image tags for image ids = {0}: {1}".format(image_ids, e))
            raise
        finally:
            conn.close()
        return image_id_to_vott_tags

    def get_image_tags(self, image_id: int):
        if type(image_id) is not int:
            raise TypeError('image_id must be an integer')

        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = ("SELECT image_tags.imagetagid, image_info.imageid, x_min, x_max, y_min, y_max, "
                         "classification_info.classificationname, image_info.height, image_info.width, image_info.imagelocation "
                            "FROM image_tags "
                                "inner join tags_classification on image_tags.imagetagid = tags_classification.imagetagid "
                                "inner join classification_info on tags_classification.classificationid = classification_info.classificationid "
                                "inner join image_info on image_info.imageid = image_tags.imageid "
                            "WHERE image_tags.imageid = {0};")
                cursor.execute(query.format(image_id,))

                logging.debug("Got image tags back for image_id={}".format(image_id))
                tag_id_to_VottImageTag = self.__build_id_to_VottImageTag(cursor)

            finally:
                cursor.close()
        except Exception as e:
            logging.error("An error occurred getting image tags for image id = {0}: {1}".format(image_id, e))
            raise
        finally:
            conn.close()
        return list(tag_id_to_VottImageTag.values())

    def __build_id_to_VottImageTag(self, tag_db_cursor):
        tag_id_to_VottImageTag = {}
        try :
            for row in tag_db_cursor:
                logging.debug(row)
                tag_id = row[0]
                if tag_id in tag_id_to_VottImageTag:
                    logging.debug("Existing ImageTag found, appending classification {0}".format(row[6]))
                    tag_id_to_VottImageTag[tag_id].classification_names.append(row[6].strip())
                else:
                    logging.debug("No existing ImageTag found, creating new ImageTag: "
                                  "id={0} x_min={1} x_max={2} x_min={3} x_max={4} classification={5} "
                                  "image_height={6} image_width={7}"
                                  .format(row[1], float(row[2]), float(row[3]), float(row[4]), float(row[5]),
                                          [row[6].strip()], row[7], row[8]))
                    tag_id_to_VottImageTag[tag_id] = VottImageTag(row[1], float(row[2]), float(row[3]),
                                                                  float(row[4]), float(row[5]), [row[6].strip()],
                                                                  row[7], row[8], row[9])
        except Exception as e:
            logging.error("An error occurred building VottImageTag dict: {0}".format(e))
            raise
        return tag_id_to_VottImageTag


    def get_existing_classifications(self):
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = "SELECT classificationname from classification_info order by classificationname asc"
                cursor.execute(query)

                classification_set = set()
                for row in cursor:
                    logging.debug(row)
                    classification_set.add(row[0])
                logging.debug("Got back {0} classifications existing in db.".format(len(classification_set)))
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An error occurred getting classifications from DB: {0}".format(e))
            raise
        finally:
            conn.close()
        return list(classification_set)

    def update_incomplete_images(self, list_of_image_ids, user_id):
        #TODO: Make sure the image ids are in a TAG_IN_PROGRESS state
        self._update_images(list_of_image_ids,ImageTagState.INCOMPLETE_TAG,user_id, self._db_provider.get_connection())
        logging.debug("Updated {0} image(s) to the state {1}".format(len(list_of_image_ids),ImageTagState.INCOMPLETE_TAG.name))

    def update_completed_untagged_images(self,list_of_image_ids, user_id):
        #TODO: Make sure the image ids are in a TAG_IN_PROGRESS state
        self._update_images(list_of_image_ids,ImageTagState.COMPLETED_TAG,user_id, self._db_provider.get_connection())
        logging.debug("Updated {0} image(s) to the state {1}".format(len(list_of_image_ids),ImageTagState.COMPLETED_TAG.name))

    def _update_images(self, list_of_image_ids, new_image_tag_state, user_id, conn):
        if not isinstance(new_image_tag_state, ImageTagState):
            raise TypeError('new_image_tag_state must be an instance of Direction Enum')

        if type(user_id) is not int:
            raise TypeError('user id must be an integer')

        if not conn:
            conn = self._db_provider.get_connection()

        try:
            if(len(list_of_image_ids) > 0):
                cursor = conn.cursor()
                try:
                    image_ids_as_strings = [str(i) for i in list_of_image_ids]
                    images_to_update = '{0}'.format(', '.join(image_ids_as_strings))
                    # TODO: find another way to do string subsitution that doesn't break this query
                    query = "UPDATE Image_Tagging_State SET TagStateId = {0}, ModifiedByUser = {2}, ModifiedDtim = now() WHERE ImageId IN ({1})"
                    cursor.execute(query.format(new_image_tag_state,images_to_update,user_id))
                    conn.commit()
                finally: cursor.close()
            else:
                logging.debug("No images to update")
        except Exception as e:
            logging.error("An errors occured updating images: {0}".format(e))
            raise

    def update_image_urls(self,image_id_to_url_map, user_id):
        if type(user_id) is not int:
            raise TypeError('user id must be an integer')

        if(len(image_id_to_url_map.items())):
            try:
                conn = self._db_provider.get_connection()
                try:
                    cursor = conn.cursor()
                    for image_id, new_url in image_id_to_url_map.items():
                        cursor = conn.cursor()
                        query = "UPDATE Image_Info SET ImageLocation = '{0}', ModifiedDtim = now() WHERE ImageId = {1}"
                        cursor.execute(query.format(new_url,image_id))
                        conn.commit()
                        logging.debug("Updated ImageId: {0} to new ImageLocation: {1}".format(image_id,new_url))
                        self._update_images([image_id],ImageTagState.READY_TO_TAG, user_id,conn)
                        logging.debug("ImageId: {0} to has a new state: {1}".format(image_id,ImageTagState.READY_TO_TAG.name))
                finally: cursor.close()
            except Exception as e:
                logging.error("An errors occured updating image urls: {0}".format(e))
                raise
            finally: conn.close()

    #TODO: Do safer query string formatting
    def update_tagged_images(self,list_of_image_tags, user_id):
        if(not list_of_image_tags):
            return

        if type(user_id) is not int:
            raise TypeError('user id must be an integer')

        groups_by_image_id = itertools.groupby(list_of_image_tags, key=lambda it:it.image_id)
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                for img_id, list_of_tags in groups_by_image_id:
                    for img_tag in list(list_of_tags):
                        query = ("with iti AS ( "
                                "INSERT INTO image_tags (ImageId, X_Min,X_Max,Y_Min,Y_Max,CreatedByUser) "
                                "VALUES ({0},{1},{2},{3},{4},{5}) "
                                "RETURNING ImageTagId), "
                                "ci AS ( "
                                    "INSERT INTO classification_info (ClassificationName) "
                                    "VALUES {6} "
                                    "ON CONFLICT (ClassificationName) DO UPDATE SET ClassificationName=EXCLUDED.ClassificationName "
                                    "RETURNING (SELECT iti.ImageTagId FROM iti), ClassificationId) "
                                "INSERT INTO tags_classification (ImageTagId,ClassificationId) "
                                "SELECT imagetagid,classificationid from ci;")
                        classifications = ", ".join("('{0}')".format(name) for name in img_tag.classification_names)
                        cursor.execute(query.format(img_tag.image_id,img_tag.x_min,img_tag.x_max,img_tag.y_min,img_tag.y_max,user_id,classifications))
                    self._update_images([img_id],ImageTagState.COMPLETED_TAG,user_id,conn)
                    conn.commit()
                logging.debug("Updated {0} image tags".format(len(list_of_image_tags)))
            finally: cursor.close()
        except Exception as e:
            logging.error("An errors occured updating tagged image: {0}".format(e))
            raise
        finally: conn.close()

    def get_classification_map(self, class_names: set, user_id: int) -> dict:
        class_to_id = {}
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = ("WITH sc AS ( "
                        "SELECT classificationid, classificationname FROM classification_info "
                        "WHERE classificationname in ({0})), "
                        "data(class_name) AS (values {1}), "
                        "ci AS ( "
                            "INSERT INTO classification_info (ClassificationName) "
                            "SELECT d.class_name FROM data d "
                            "WHERE NOT EXISTS (select 1 FROM classification_info c WHERE c.classificationname = d.class_name) "
                            "RETURNING classificationid,classificationname) "
                        "SELECT classificationid,classificationname FROM ci  "
                        "UNION ALL "
                        "SELECT classificationid,classificationname FROM sc")
                class_names_where = "'{0}'".format("', '".join(class_names))
                class_names_value = ", ".join("('{0}')".format(class_name) for class_name in class_names)
                query = query.format(class_names_where,class_names_value)
                cursor.execute(query)
                conn.commit()
                for row in cursor:
                    logging.debug(row)
                    class_to_id[row[1]] = int(row[0])
            finally: cursor.close()
        except Exception as e:
            logging.error("An errors occured upserting classification names: {0}".format(e))
            raise
        finally: conn.close()
        return class_to_id

    def update_tagged_images_v2(self, annotated_labels: list, user_id: int):
        if(not annotated_labels):
            return

        if type(user_id) is not int:
            raise TypeError('user id must be an integer')

        labels_length = len(annotated_labels)
        all_image_ids = list(l.image_id for l in annotated_labels)
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = "INSERT INTO Annotated_Labels(ImageId,ClassificationId,X_Min,X_Max,Y_Min,Y_Max,CreatedByUser) VALUES "
                #Build query so we can insert all rows at once
                for i in range(labels_length):
                    label = annotated_labels[i]
                    query+="({0},{1},{2},{3},{4},{5},{6}) ".format(label.image_id,label.classification_id,
                                                            label.x_min,label.x_max,label.y_min,label.y_max,user_id)
                    if i != labels_length-1: query+=","
                cursor.execute(query)
                self._update_images(all_image_ids,ImageTagState.COMPLETED_TAG,user_id,conn)
                conn.commit()
            #logging.debug("Updated status for {0} images".format(len(all_image_ids)))
            finally: cursor.close()
        except Exception as e:
            logging.error("An errors occured updating tagged image: {0}".format(e))
            raise
        finally: conn.close()
    
    def convert_to_annotated_label(self, image_tags: list, class_map: dict):
        annotated_labels = []
        for img_tag in image_tags:
            for class_name in img_tag.classification_names:
                annotated_labels.append(AnnotatedLabel(img_tag.image_id,class_map[class_name],
                                        img_tag.x_min,img_tag.x_max,img_tag.y_min,img_tag.y_max))
        return annotated_labels

    def add_prediction_labels(self, prediction_labels: list, training_id: int):
        if(not prediction_labels):
            return

        if type(training_id) is not int:
            raise TypeError('training id must be an integer')

        labels_length = len(prediction_labels)
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = "INSERT INTO Prediction_Labels(TrainingId,ImageId,ClassificationId,X_Min,X_Max,Y_Min,Y_Max,BoxConfidence,ImageConfidence) VALUES "
                #Build query so we can insert all rows at once
                for i in range(labels_length):
                    label = prediction_labels[i]
                    query+="({0},{1},{2},{3},{4},{5},{6},{7},{8}) ".format(training_id,label.image_id,label.classification_id,
                                                                    label.x_min,label.x_max,label.y_min,label.y_max,
                                                                    label.box_confidence,label.image_confidence)
                    if i != labels_length-1: query+=","
                cursor.execute(query)
                #TODO: Update some sort of training status table?
                #self._update_training_status(training_id,conn)
                conn.commit()
            # logging.debug('Inserted {0} predictions for training session {1}'.format(labels_length, training_id))
            finally: cursor.close()
        except Exception as e:
            logging.error("An errors occured updating tagged image: {0}".format(e))
            raise
        finally: conn.close()

    # In practice we won't be getting multiple class names per bounding box however
    # VOTT supports this. If multple class names per boounding box is common we can get more 
    # efficient with the nesting to avoid dupe bounding boxes per image
    def get_labels(self):        
        id_to_imagelabels = {}
        try:
            conn = self._db_provider.get_connection()
            try:
                cursor = conn.cursor()
                query = ("SELECT d.imageid, d.imagelocation, d.height, d.width, "
                         "c.classificationname, x_min, x_max, y_min, y_max "
                            "FROM Annotated_Labels a "
                                "inner join classification_info c on a.classificationid = c.classificationid "
                                "inner join image_info d on d.imageid = a.imageid ")
                cursor.execute(query)
                for row in cursor:
                    image_id = row[0]
                    tag = Tag(row[4],float(row[5]),float(row[6]),float(row[7]),float(row[8]))
                    if image_id in id_to_imagelabels:                  
                        id_to_imagelabels[image_id].labels.append(tag)
                    else:
                        img_label = ImageLabel(image_id,row[1],row[2],row[3],[tag])
                        id_to_imagelabels[image_id] = img_label
                
                logging.debug("Found labels for {0} images".format(len(id_to_imagelabels)))       
            finally:
                cursor.close()
        except Exception as e:
            logging.error("An error occurred getting labels: {0}".format(e))
            raise
        finally:
            conn.close()
        return list(id_to_imagelabels.values())

class ArgumentException(Exception):
    pass


def main():
    #################################################################
    # This main method is an example of how to use some of
    #  the ImageTagDataAccess methods. For instance:
    #   Creating a User
    #   Onboarding of new images
    #   Checking in images been tagged
    #################################################################

    # import sys
    # import os
    # sys.path.append("..")
    # sys.path.append(os.path.abspath('db_provider'))
    # from db_provider import DatabaseInfo, PostGresProvider

    #Replace me for testing
    db_config = DatabaseInfo("","","","")
    data_access = ImageTagDataAccess(PostGresProvider(db_config))
    user_id = data_access.create_user(getpass.getuser())
    logging.info("The user id for '{0}' is {1}".format(getpass.getuser(),user_id))

    #img_labels = data_access.get_labels()

    simulate_onboarding = False
    if simulate_onboarding:
        list_of_image_infos = generate_test_image_infos(5)
        url_to_image_id_map = data_access.add_new_images(list_of_image_infos,user_id)

        image_ids = list(url_to_image_id_map.values())
        #Skip extra stuff and just put the images to expected state for testing 
        data_access._update_images(image_ids,ImageTagState.READY_TO_TAG, user_id,None)

    simulate_tagging = False
    if simulate_tagging:
        image_tags = generate_test_image_tags(image_ids,4,4)

        all_class_name_lists = (list(it.classification_names for it in image_tags))
        unique_class_names = set(x for l in all_class_name_lists for x in l)
        print(len(unique_class_names))

        #What the Labels API will do when POST http action occurs
        class_map = data_access.get_classification_map(unique_class_names,user_id)
        annotated_labels = data_access.convert_to_annotated_label(image_tags,class_map)
        data_access.update_tagged_images_v2(annotated_labels,user_id)

    simulate_post_training = False
    if simulate_post_training and simulate_tagging:
        training_id = 1
        prediction_labels = generate_test_prediction_labels(training_id,image_ids, class_map)
        data_access.add_prediction_labels(prediction_labels,training_id)


TestClassifications = ("maine coon","german shephard","goldfinch","mackerel","african elephant","rattlesnake")

def generate_test_image_infos(count):
    list_of_image_infos = []
    for i in range(count):
        file_name = "{0}.jpg".format(id_generator(size=random.randint(4,10)))
        image_location = "https://mock-storage.blob.core.windows.net/new-uploads/{0}".format(file_name)
        img = ImageInfo(file_name,image_location,random.randint(100,600),random.randint(100,600))
        list_of_image_infos.append(img)
    return list_of_image_infos

def generate_test_image_tags(list_of_image_ids,max_tags_per_image,max_classifications_per_tag):
    list_of_image_tags = []
    for image_id in list(list_of_image_ids):
        tags_per_image = random.randint(1,max_tags_per_image)
        for i in range(tags_per_image):
            x_min = random.uniform(50,300)
            x_max = random.uniform(x_min,300)
            y_min = random.uniform(50,300)
            y_max = random.uniform(y_min,300)
            classifications_per_tag = random.randint(1,max_classifications_per_tag)
            image_tag = ImageTag(image_id,x_min,x_max,y_min,y_max,random.sample(TestClassifications,classifications_per_tag))
            list_of_image_tags.append(image_tag)
    return list_of_image_tags

def generate_test_prediction_labels(training_id, list_of_image_ids,class_map: dict):
    list_of_prediction_labels = []
    for image_id in list(list_of_image_ids):
        tags_per_image = random.randint(1,3)
        for i in range(tags_per_image):
            x_min = random.uniform(50,300)
            x_max = random.uniform(x_min,300)
            y_min = random.uniform(50,300)
            y_max = random.uniform(y_min,300)         
            image_conf = random.uniform(.5,1)
            box_conf = random.uniform(image_conf,1)
            class_name = random.choice(TestClassifications)
            class_id = class_map[class_name]
            prediction_label = PredictionLabel(training_id,image_id,class_id,
                                x_min,x_max,y_min,y_max,random.randint(100,600),
                                random.randint(100,600), box_conf,image_conf)
            list_of_prediction_labels.append(prediction_label)
    return list_of_prediction_labels

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

if __name__ == "__main__":
    #Log to console when run locally
    console = logging.StreamHandler()
    log = logging.getLogger()
    log.setLevel(logging.getLevelName('DEBUG'))
    log.addHandler(console)
    main()
