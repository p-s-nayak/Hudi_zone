try:
    import os
    import sys
    import uuid

    import pyspark
    from pyspark import SparkConf, SparkContext
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, asc, desc
    from awsglue.utils import getResolvedOptions
    from awsglue.dynamicframe import DynamicFrame
    from awsglue.context import GlueContext

    from faker import Faker

    print("All modules are loaded .....")

except Exception as e:
    print("Some modules are missing {} ".format(e))


# ----------------------------------------------------------------------------------------
#                 Settings
# -----------------------------------------------------------------------------------------

database_name1 = "hudidatalakedb"
table_name = "hudidatalake_table"
base_s3_path = "s3a://ps-apache-hudi-dev"
final_base_path = "{base_s3_path}/{table_name}".format(
    base_s3_path=base_s3_path, table_name=table_name
)

# ----------------------------------------------------------------------------------------------------
global faker
faker = Faker()


class DataGenerator(object):

    @staticmethod
    def get_data():
        return [
            (
                x,
                faker.name(),
                faker.random_element(elements=('IT', 'HR', 'Sales', 'Marketing')),
                faker.random_element(elements=('CA', 'NY', 'TX', 'FL', 'IL', 'RJ')),
                faker.random_int(min=10000, max=150000),
                faker.random_int(min=18, max=60),
                faker.random_int(min=0, max=100000),
                faker.unix_time()
            ) for x in range(5)
        ]


def create_spark_session():
    spark = SparkSession \
        .builder \
        .config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer') \
        .getOrCreate()
    return spark


spark = create_spark_session()
sc = spark.sparkContext
glueContext = GlueContext(sc)

"""
CHOOSE ONE 
"hoodie.datasource.write.storage.type": "MERGE_ON_READ",
"hoodie.datasource.write.storage.type": "COPY_ON_WRITE",
"""


hudi_options = {
    'hoodie.table.name': table_name,
    "hoodie.datasource.write.storage.type": "COPY_ON_WRITE",
    'hoodie.datasource.write.recordkey.field': 'emp_id',
    'hoodie.datasource.write.table.name': table_name,
    'hoodie.datasource.write.operation': 'upsert',
    'hoodie.datasource.write.precombine.field': 'ts',

    'hoodie.datasource.hive_sync.enable': 'true',
    "hoodie.datasource.hive_sync.mode":"hms",
    'hoodie.datasource.hive_sync.sync_as_datasource': 'false',
    'hoodie.datasource.hive_sync.database': database_name1,
    'hoodie.datasource.hive_sync.table': table_name,
    'hoodie.datasource.hive_sync.use_jdbc': 'false',
    'hoodie.datasource.hive_sync.partition_extractor_class': 'org.apache.hudi.hive.MultiPartKeysValueExtractor',
    'hoodie.datasource.write.hive_style_partitioning': 'true',

}


# ====================================================
"""Create Spark Data Frame """
# ====================================================
data = DataGenerator.get_data()

columns = ["emp_id", "employee_name", "department", "state", "salary", "age", "bonus", "ts"]
df = spark.createDataFrame(data=data, schema=columns)
df.write.format("hudi").options(**hudi_options).mode("overwrite").save(final_base_path)


# ====================================================
"""APPEND """
# ====================================================

impleDataUpd = [
    (6, "This is APPEND", "Sales", "RJ", 81000, 30, 23000, 827307999),
    (7, "This is APPEND", "Engineering", "RJ", 79000, 53, 15000, 1627694678),
]

columns = ["emp_id", "employee_name", "department", "state", "salary", "age", "bonus", "ts"]
usr_up_df = spark.createDataFrame(data=impleDataUpd, schema=columns)
usr_up_df.write.format("hudi").options(**hudi_options).mode("append").save(final_base_path)


# ====================================================
"""UPDATE """
# ====================================================
impleDataUpd = [
    (3, "this is update on data lake", "Sales", "RJ", 81000, 30, 23000, 827307999),
]
columns = ["emp_id", "employee_name", "department", "state", "salary", "age", "bonus", "ts"]
usr_up_df = spark.createDataFrame(data=impleDataUpd, schema=columns)
usr_up_df.write.format("hudi").options(**hudi_options).mode("append").save(final_base_path)

# # ====================================================

# ====================================================
"""HARD DELETE """
# ====================================================


print("\n")
hard_delete_df = spark.sql("SELECT * FROM hudidb.hudi_table where emp_id='4' ")
print(hard_delete_df.show())
print("\n")
hudi_options['hoodie.datasource.write.operation'] = 'delete'
hard_delete_df.write.format("hudi").options(**hudi_options).mode("append").save(final_base_path)





# ====================================================
"""CLUSTERING  """
# ====================================================
hudi_options['hoodie.clustering.plan.strategy.sort.columns'] = 'state'
hudi_options['hoodie.clustering.plan.strategy.max.bytes.per.group'] = '107374182400'
hudi_options['hoodie.clustering.plan.strategy.max.num.groups'] = '1'


hudi_options['hoodie.cleaner.policy'] = 'KEEP_LATEST_FILE_VERSIONS'


cluster_df = spark.sql("SELECT * FROM hudidb.hudi_table ")
cluster_df.write.format("hudi").options(**hudi_options).mode("append").save(final_base_path)




