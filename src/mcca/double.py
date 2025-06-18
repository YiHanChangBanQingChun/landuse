import os
import rasterio
from rasterio.enums import Resampling

class TIFConverter:
    def __init__(self, input_dir, output_dir):
        """
        初始化转换器
        :param input_dir: 输入文件夹路径，包含待转换的 .tif 文件
        :param output_dir: 输出文件夹路径，用于保存转换后的文件
        """
        self.input_dir = input_dir
        self.output_dir = output_dir

        # 创建输出文件夹（如果不存在）
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def convert_to_double(self):
        """
        将文件夹中的所有 .tif 文件转换为 double 类型
        """
        for file_name in os.listdir(self.input_dir):
            if file_name.endswith(".tif"):
                input_path = os.path.join(self.input_dir, file_name)
                output_path = os.path.join(self.output_dir, file_name)

                self._process_file(input_path, output_path)

    def _process_file(self, input_path, output_path):
        """
        处理单个 .tif 文件，将其转换为 double 类型
        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        """
        with rasterio.open(input_path) as src:
            # 读取元数据
            profile = src.profile
            profile.update(dtype=rasterio.float64)  # 更新数据类型为 double (float64)

            # 读取数据
            data = src.read(1)  # 读取第一波段数据
            nodata = src.nodata  # 获取 nodata 值

            # 写入新的文件
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(data, 1)  # 写入第一波段数据
                dst.nodata = nodata  # 保留 nodata 值

if __name__ == "__main__":
    input_dir = r"F:\landuse\data\double\landuse"  # 输入文件夹路径
    output_dir = r"F:\landuse\data\double\converlu"  # 输出文件夹路径

    converter = TIFConverter(input_dir, output_dir)
    converter.convert_to_double()