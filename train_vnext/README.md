# Training vNext

This document covers the most basic instructions to get a training session going on an in development version of the system that uses a new data management paradigm. 

The instructions assume you are familiar with the original manual instructions [here](../Readme.me) and it's woodblock dataset. We also assume your are working with a Training environment (most likely SSHing into a deployed [Azure DSVM](../devops/dsvm/Readme.md)

Consider this to be a **pre-release** version with instructions that will evolve quickly as more automation gets built. 

## Set up legacy config.ini
+ Go to the [config.ini](../config.ini) in your training environment 
+ Update the values for the following keys:
    + python_file_directory
    + data_dir
    + train_dir
    + inference_output_dir
    + tf_models_location
    + download_location
    + user_folders (**Must be set to false for the moment**)
    + classes
    + filetype
 
 For instance on an Azure DSVM the values could be 

```
python_file_directory=/data/home/abrig/repos/models/research/active-learning-detect/train_vnext

data_dir=/data/home/abrig/actlrn-data

train_dir=/data/home/abrig/actlrn-data/training

inference_output_dir=knots_inference_graphs

tf_models_location=/data/home/abrig/repos/models/research

download_location=/data/home/abrig/actlrn-downloads

user_folders=False

classes=knot,defect

filetype=*.png
```
**Note**: The value for config.ini KEY **_python_file_directory_** must be the absolute file path

## Set up CLI

Follow the instructions [here](../cli/Readme.md) to make sure your CLI configuration file exists and is set up. Most importantly you should have your CLI config associated with the ALCONFGI environment variable


## Set up data dependencies
In a command window navigate to the root (one level up from here) of the repo.

**Note:** If you have previosuly followed the original manual instructions [here](../Readme.me) your Active Learning repo will be within your Tensorflow repo (e.g ~/repos/models/research/active-learning-detect/). The [DSVM deployment script](../devops/dsvm/Readme.md) will automate this setup for you.

Run the following command
```
python -m train_vnext.training start -c ~/repos/models/research/active-learning-detect/config.ini
```

This command will 
- Verify the config.ini file 
- Download the all the images, 
- Create the human annotated image labels as a CSV 
- Create a list of "in progress" images as a CSV 
- Create the PASCAL VOC file based on the classification name values ("classes" key) in config.ini

**Note:** You may receive errors about missing configuration keys if your config.ini is not setup correctly

## Execute training 
Next we will navigate to the _training_vnext_ directory and run the command 

```
sh active_learning_train.sh ~/repos/models/research/active-learning-detect/config.ini
```

This process can take 10 mins or longer to execute.

## Save training session
Navigate back to the root of your Active Learning repo and execute:  

```
python -m train_vnext.training save -c ~/repos/models/research/active-learning-detect/config.ini
```

This command will
* Persist the training session's inference graph in cloud storage 
* Log a new training session to the database
* Log all performance and prediction datat from the training session to the database


## Review training performance 
To quickly review training and class performance  over time use the following queries directly against your [deployed](../db/Readme.md) database


Class performance over time
```
SELECT 
    c.classificationname,
    p.avgperf, 
    t.classperfavg
FROM training_info t 
join class_performance p on t.trainingid = p.trainingid
join classification_info c on c.classificationid = p.classificationid
order by t.createddtim desc;
```

Least confident classifications
```
SELECT 
    p.imageid, 
    c.classificationname,
    p.boxconfidence, 
    p.imageconfidence 
FROM Prediction_Labels p
join classification_info c on c.classificationid = p.classificationid
where trainingid = (SELECT MAX(trainingid) FROM training_info) 
order by boxconfidence ASC;
```

Most confident classifications
```
SELECT 
    p.imageid, 
    c.classificationname,
    p.boxconfidence, 
    p.imageconfidence 
FROM Prediction_Labels p
join classification_info c on c.classificationid = p.classificationid
where trainingid = (SELECT MAX(trainingid) FROM training_info) 
order by boxconfidence DESC;
```


