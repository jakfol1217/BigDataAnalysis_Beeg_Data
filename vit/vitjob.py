# Run with:
# spark-submit --name vit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 vitjob.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import PIL
import requests
from transformers import AutoImageProcessor, MobileViTV2Model
import torch
import json

spark = SparkSession.builder.appName('vit').getOrCreate()

image_processor = AutoImageProcessor.from_pretrained("apple/mobilevitv2-1.0-imagenet1k-256")
model = MobileViTV2Model.from_pretrained("apple/mobilevitv2-1.0-imagenet1k-256")

@udf
def process(url):
    print("[UDF] Processing", url)
    if not url.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return ""
    try:
        image = PIL.Image.open(
            requests.get(url, stream=True).raw
        )
        inputs = image_processor(image, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        embeddings = outputs.pooler_output.tolist()[0]
        return json.dumps(embeddings) 
    except Exception:
        import traceback
        print(traceback.format_exc())
        return ""

schema = StructType([
    StructField("global_id", StringType()),
    StructField("author", StringType()),
    StructField("created_time", StringType()),
    StructField("desc", StringType()),
    StructField("score", IntegerType()),
    StructField("url", StringType()),
    StructField("source", StringType())
])

raw_kafka = (
  spark 
  .readStream 
  .format("kafka") 
  .option("kafka.bootstrap.servers", "nifi:9092") 
  .option("subscribe", "nifi2vit") 
  .load()
)

parsed_message = raw_kafka.select(
  from_json(col("value").cast("string"), schema).alias("message")
)

embedded = parsed_message.select(
  col("message.global_id").alias("global_id"),
  process(col("message.url")).alias("embeddings")
)

kafka_message = embedded.select(
  to_json(struct(col("global_id"), col("embeddings"))).alias("value")
)

vit2analytics_ssc = (
    kafka_message
    .writeStream 
    .format("kafka") 
    .option("kafka.bootstrap.servers", "nifi:9092") 
    .option("checkpointLocation", "/tmp/vit/checkpoint/analytics")
    .option("topic", "vit2analytics")
    .start()
)

vit2cluster_ssc = (
    kafka_message
    .writeStream  
    .format("kafka") 
    .option("kafka.bootstrap.servers", "nifi:9092") 
    .option("checkpointLocation", "/tmp/vit/checkpoint/cluster")
    .option("topic", "vit2cluster")
    .start()
)

vit2analytics_ssc.awaitTermination()
vit2cluster_ssc.awaitTermination()
