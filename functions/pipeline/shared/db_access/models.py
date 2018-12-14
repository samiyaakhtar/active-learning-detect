from enum import IntEnum, unique

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
    
    @staticmethod
    def fromJson(dictionary):
        image_tag = ImageTag(dictionary["image_id"], dictionary["x_min"], dictionary["x_max"], dictionary["y_min"], dictionary["y_max"], dictionary["classification_names"])
        return image_tag

#This class doesn't have box and image confidence because they are human curated labels
class AnnotatedLabel(object):
    def __init__(self, image_id, classification_id, x_min, x_max, y_min, y_max):
        self.image_id = image_id
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.classification_id = classification_id


class ImageLabel(object):
    def __init__(self,image_id, imagelocation,image_height: int, image_width: int, labels: list, user_folder=None):
        self.image_id = image_id
        self.imagelocation = imagelocation
        self.image_height = image_height
        self.image_width = image_width
        self.user_folder = user_folder
        self.labels = labels
    
    @staticmethod
    def fromJson(dictionary):
        tags = []
        if (isinstance(dictionary["labels"], dict)):
            tags = [ImageTag.fromJson(dictionary["labels"])]
        elif (isinstance(dictionary["labels"], list)):
            tags = [ImageTag.fromJson(label) for label in dictionary["labels"]]

        image_label = ImageLabel(dictionary["image_id"], dictionary["imagelocation"], dictionary["image_height"], dictionary["image_width"], tags, dictionary.get("user_folder"))
        return image_label


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
