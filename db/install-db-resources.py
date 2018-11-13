import pg8000
import os
import sys
import collections
import argparse
from os import listdir
from os.path import isfile, join

default_postgres_db_name = "postgres"

def read_file_as_string(local_file_name):
    data = None
    with open(local_file_name, 'r') as myfile:
        data = myfile.read()
    if not data:
        print("The file {0} is empty. ".format(local_file_name))
    return data

def execute_queries_from_map(conn, file_query_map):
    cursor = conn.cursor()
    if(len(file_query_map)>0):
        print("Installed: \n")
        for file_path,query in file_query_map.items():
            cursor.execute(query)
            conn.commit()
            print("\t{0}".format(file_path))         
    return

def database_exists(conn, db_name):
    if db_name:
        cursor = conn.cursor()
        query = "SELECT 1 FROM pg_database WHERE datname=%s"
        cursor.execute(query,(db_name,))
        row = cursor.fetchone()
        if row:
            return int(row[0]) == 1
    return False

def create_database(conn, db_name):
    if db_name:
        cursor = conn.cursor()
        conn.autocommit = True
        query = "CREATE DATABASE {0};"
        print("\nAttempting to create database '{0}'...This may take up to 30 seconds".format(db_name))
        cursor.execute(query.format(db_name))
        print("Successfully created database named '{0}'".format(db_name))
    else:
        print("No database created due to empty parameter")
    return

def remove_database(conn, db_name):
    if db_name:
        cursor = conn.cursor()
        conn.autocommit = True
        query = "DROP DATABASE {0};"
        print("\nAttempting to drop database '{0}'...This may take up to 30 seconds".format(db_name))
        cursor.execute(query.format(db_name))
        print("Successfully dropped database named '{0}'".format(db_name))
    else:
        print("No database dropped due to empty parameter")
    return

def install_extensions(conn, list_of_extensions):
    if (len(list_of_extensions) > 0):
        cursor = conn.cursor()
        conn.autocommit = True
        for ext in list_of_extensions:     
            query = "CREATE EXTENSION {0};"
            cursor.execute(query.format(ext))
            print("Installed extension named '{0}'".format(ext))
    else:
        print("No extensions to install")
    return

def get_connection():
    return __new_postgres_connection(os.environ['DB_HOST'],os.environ['DB_NAME'],os.environ['DB_USER'],os.environ['DB_PASS'])

def __new_postgres_connection(host_name,db_name,db_user,db_pass):
    return pg8000.connect(db_user, host=host_name, unix_sock=None, port=5432, database=db_name, password=db_pass, ssl=True, timeout=None, application_name=None)

def get_file_query_map(sub_dir_name):
    dirname = os.path.dirname(__file__)
    full_sub_dir_path = os.path.join(dirname, sub_dir_name)
    sub_dir_scripts = [join(full_sub_dir_path, f) for f in listdir(full_sub_dir_path) if isfile(join(full_sub_dir_path, f))]
    file_query_map = {f:read_file_as_string(f) for f in sub_dir_scripts}
    return file_query_map

def get_default_connection():
    return __new_postgres_connection(os.environ['DB_HOST'],default_postgres_db_name,os.environ['DB_USER'],os.environ['DB_PASS'])

def get_connection_for_db(db_name):
    return __new_postgres_connection(os.environ['DB_HOST'],db_name,os.environ['DB_USER'],os.environ['DB_PASS'])

def execute_files_in_dir_list(conn,list_of_sub_dirs):
    for sub_dir in list_of_sub_dirs:
        print("\n****\tReading files in '{0}' directory\t****\n".format(sub_dir))
        file_query_map = get_file_query_map(sub_dir)
        file_query_map = collections.OrderedDict(sorted(file_query_map.items()))
        if '' in file_query_map.values():
            print("One of the files is empty. Please fix")
            return
        execute_queries_from_map(conn,file_query_map)

def main(db_name, overwrite_db):
    try:
        if(os.getenv("DB_HOST") is None or os.getenv("DB_USER") is None or os.getenv("DB_PASS") is None):
            print("Please set environment variables for DB_HOST, DB_USER, DB_PASS")
            return
        
        if (database_exists(get_default_connection(), db_name) and overwrite_db):
            remove_database(get_default_connection(),db_name)
        elif (database_exists(get_default_connection(), db_name) and not overwrite_db):    
            print("Database {0} already exists. Please see --help for overwrite option.".format(db_name))
            return

        #Set up the database
        create_database(get_default_connection(),db_name)

        #Install extensions
        install_extensions(get_connection_for_db(db_name),['citext'])

        #Connect to the new database and install resources
        conn = get_connection_for_db(db_name) 
        sub_dirs = ["tables","functions","triggers","data"]
        execute_files_in_dir_list(conn,sub_dirs)

        print("Done!")
    except Exception as e: 
        print(e)
        #traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('database_name', type=str,
                    help='The name of the database to create and install resources on')

    parser.add_argument('-o','--overwrite', action='store_true',
                    help='Will drop and restore a database if it already exists')

    args = parser.parse_args()
    database_name = args.database_name
    main(args.database_name,args.overwrite)           
