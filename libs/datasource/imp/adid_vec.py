import logging
logger = logging.getLogger(__name__)
from pyspark.sql.dataframe import DataFrame
from conf import hadoop as hadoop_conf
from libs.utilis.dict_utils import get_simple_str
import logging
logger = logging.getLogger(__name__)
from libs.datasource.datasource import DataSource
from libs.utilis.spark_utils import read_csv
from libs.processing.udf.wrapper_udf import split_to_list_udf,list_dict_index_udf,list_dict_has_key_udf,list_avg_udf,list_sum_udf
from pyspark.sql.types import *
from libs.env.hdfs import hdfs
class AdidVecDataSource(DataSource):


    def __init__(self, name,spark=None,parallel=False,**kwargs):
        super().__init__(name)
        self.model = None
        self._args = kwargs
        self._spark = spark


    def get_dataframe(self):
        output_path = self.get_output_filepath(**self._args)
        print(f"read dataframe from:{output_path}")
        ret_df:DataFrame = self._spark.read.parquet(output_path)
        ret_df.show(10)
        return ret_df

    @staticmethod
    def get_type():
        return 'Bid_AdId_Imp_Sequence_Vec'



    @staticmethod
    def download_image(adid):
        pass

    def get_output_filepath(self,**kwargs):
        output_file = f"{self.get_type()}{get_simple_str(**kwargs)}"
        output_path = f"{hadoop_conf.HDFS_FEATURE_ROOT}/{str(self._name).format(**kwargs)}/{output_file}"
        return output_path



    def _produce_data(self,output_path):
        vector_size = 16
        user_file = "hdfs:///user/model/extend_data/suning_gid_list.csv"
        #user_file = "hdfs:///user/model/extend_data/user_20190318.txt"
        user_df = read_csv(user_file, spark=self._spark, has_header=False,
                           delimiter='\t',
                           #schema_names=['Id_Zid', 'imp', 'clk', 'imp_adid', 'clk_adid']
                            schema_names = ['Id_Zid',  'imp_adid']
                           )

        print(f"read user from:{user_file}")

        word_vec_file = "hdfs:///user/model/extend_data/suning_gid_emb.csv"
        # word_vec_file = "hdfs:///user/model/extend_data/ad_vec_1.txt"
        word_vec_df = read_csv(word_vec_file, spark=self._spark, has_header=False,
                               delimiter='\t',
                               schema_names=['adid', 'adid_vec'])
        print(f"read word_vecv from:{word_vec_file}")
        word_vec_df.show(10,truncate=False)
        apply_udf = split_to_list_udf(" ", DoubleType()).get_udf()
        word_vec_df = word_vec_df.withColumn("adid_arr", apply_udf("adid_vec"))
        word_vec_list = word_vec_df.toPandas().to_dict('records')

        word_vec_dict = {}

        for row in word_vec_list:
            word_vec_dict[row['adid']] = row['adid_arr']

        apply_udf = list_dict_index_udf(word_vec_dict, [0.0 for i in range(vector_size)],
                                        output_type=ArrayType(DoubleType())).get_udf()
        user_df = user_df.withColumn("adid_vec_list", apply_udf('imp_adid'))
        # user_df = user_df.withColumn("adid_clk_vec_list", apply_udf('clk_adid'))
        apply_udf = list_avg_udf(vector_size).get_udf()
        user_df = user_df.withColumn("adid_vec_avg", apply_udf('adid_vec_list'))
        # user_df = user_df.withColumn("adid_clk_vec_avg", apply_udf('adid_clk_vec_list'))
        apply_udf = list_sum_udf(vector_size).get_udf()
        user_df = user_df.withColumn("adid_vec_sum", apply_udf('adid_vec_list'))
        # user_df = user_df.withColumn("adid_clk_vec_sum", apply_udf('adid_clk_vec_list'))
        df = user_df.select(
            # ["Id_Zid", "adid_vec_avg","adid_vec_sum","adid_clk_vec_avg","adid_clk_vec_sum"]
            ["Id_Zid", "adid_vec_avg", "adid_vec_sum"]
        )
        df.write.parquet(path=output_path, mode='overwrite')
        return  df

    def produce_data(self,overwrite=False,df_handler=None,write_df=True)->DataFrame:
        df = None
        output_path = self.get_output_filepath(**self._args)
        if not hdfs.exists(output_path):
            logger.info("file [{path}] is not exist! we process data from clickhouse."
                        .format(path=output_path))
            df = self._produce_data(output_path)

        else:
            if overwrite:
                logger.info("file [{path}] is  exist! we overwrite process data from clickhouse."
                            .format(path=output_path))
                df = self._produce_data(output_path)

        return df