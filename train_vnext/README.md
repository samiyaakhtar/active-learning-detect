# Training V2

This scripts in this directory are **__in progress__** and experimental.

If one must run these scripts there are a few things one will need to do versus the regular training instructions.

**Update the config.ini KEY 'python_file_directory' to point to this directory**
 
 For instance

```
python_file_directory=/home/abrig/active-learning-detect/train_vnext
```

**On the Training Machine (Azure DSVM) make sure your $PYTHONPATH includes:**

```
/opt/caffe/python:/opt/caffe2/build:
```



